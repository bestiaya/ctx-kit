#!/usr/bin/env python3
"""Read-only Codex usage audit. Python 3.9+, standard library only.

Explicit rollout paths or context-kit usage snapshots; never scans an account.
Response records are authoritative. token_count is a legacy fallback/cross-check.
"""
import argparse
import hashlib
import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from zoneinfo import ZoneInfo

VERSION = 1
DEFAULT_PROFILE = {
    'id': 'codex-astra-fixed-v1', 'models': ['gpt-6-astra'],
    'weights': {'uncached_input': '1', 'cached_input': '0.1', 'output': '5'},
}
COUNTERS = ('input_tokens', 'cached_input_tokens', 'cache_write_input_tokens',
            'output_tokens', 'reasoning_output_tokens', 'total_tokens')


def instant(value, tz='UTC'):
    result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if result.tzinfo is None:
        result = result.replace(tzinfo=ZoneInfo(tz))
    return result.astimezone(timezone.utc)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def check_profile(profile):
    if not isinstance(profile, dict) or not isinstance(profile.get('id'), str) or not profile['id']:
        raise ValueError('profile requires a nonempty id')
    models = profile.get('models')
    if not isinstance(models, list) or not models or not all(isinstance(m, str) and m for m in models):
        raise ValueError('profile requires a nonempty list of exact model names')
    if not isinstance(profile.get('weights'), dict):
        raise ValueError('profile weights must be an object')
    weights = {}
    for key in ('uncached_input', 'cached_input', 'output'):
        try:
            value = Decimal(str(profile.get('weights', {})[key]))
        except (KeyError, InvalidOperation):
            raise ValueError('missing or invalid profile weight: ' + key)
        if not value.is_finite() or value < 0:
            raise ValueError('weights must be finite and nonnegative')
        weights[key] = str(value)
    return {'id': profile['id'], 'models': sorted(set(models)), 'weights': weights}


def usage_values(value):
    if not isinstance(value, dict):
        raise ValueError('usage is not an object')
    result = {k: value.get(k) for k in COUNTERS}
    for key, number in result.items():
        if number is not None and (type(number) is not int or number < 0):
            raise ValueError(key + ' must be a nonnegative integer or absent')
    if result['input_tokens'] is None or result['output_tokens'] is None:
        raise ValueError('input_tokens and output_tokens are required')
    i, o = result['input_tokens'], result['output_tokens']
    if result['cached_input_tokens'] is not None and result['cached_input_tokens'] > i:
        raise ValueError('cached input exceeds input')
    if result['cache_write_input_tokens'] is not None and result['cache_write_input_tokens'] > i:
        raise ValueError('cache writes exceed input')
    if result['cached_input_tokens'] is not None and result['cache_write_input_tokens'] is not None:
        if result['cached_input_tokens'] + result['cache_write_input_tokens'] > i:
            raise ValueError('cache read plus writes exceed input')
    if result['reasoning_output_tokens'] is not None and result['reasoning_output_tokens'] > o:
        raise ValueError('reasoning output exceeds output')
    if result['total_tokens'] is not None and result['total_tokens'] != i + o:
        raise ValueError('total_tokens differs from input + output')
    result['total_tokens'] = i + o
    result['uncached_input_tokens'] = None if result['cached_input_tokens'] is None else i - result['cached_input_tokens']
    return result


def read_events(path, issues):
    path = Path(path).expanduser().resolve()
    with path.open('rb') as handle:
        size = os.fstat(handle.fileno()).st_size
        raw = handle.read(size)
    manifest = {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
    if path.suffix == '.json':
        data = json.loads(raw)
        if not isinstance(data, dict) or not isinstance(data.get('request_records'), list):
            raise ValueError(str(path) + ': not a context-kit usage snapshot')
        events = [(0, {'type': 'session_meta', 'payload': data.get('session_meta', {})})]
        for row in data['request_records']:
            line = row['source_line']
            events.extend([
                (line, {'type': 'turn_context', 'payload': row.get('context', {})}),
                (line, {'type': 'event_msg', 'payload': {'type': 'thread_settings_applied', 'thread_settings': row.get('settings', {})}}),
                (line, {'type': 'token_usage_record', 'timestamp': row['timestamp'], 'payload': row['record']}),
            ])
        for row in data.get('token_count_events', []):
            events.append((row['source_line'], {'type': 'event_msg', 'timestamp': row['timestamp'],
                                              'payload': {'type': 'token_count', 'info': row['info']}}))
        for row in data.get('compaction_markers', []):
            events.append((row['source_line'], {'type': 'compacted', 'timestamp': row['timestamp'], 'payload': {}}))
        manifest['original_path'] = data.get('source')
        manifest['original_sha256'] = data.get('source_prefix_sha256')
        return sorted(events, key=lambda pair: pair[0]), manifest
    events = []
    lines = raw.splitlines()
    for line, body in enumerate(lines, 1):
        if not body.strip():
            continue
        try:
            event = json.loads(body)
            if not isinstance(event, dict):
                raise ValueError('not an object')
        except (ValueError, UnicodeDecodeError):
            issues.append({'code': 'invalid_json_line', 'path': str(path), 'line': line,
                           'detail': 'truncated tail' if line == len(lines) and not raw.endswith(b'\n') else 'malformed JSON'})
            continue
        events.append((line, event))
    return events, manifest


def parse_file(path, source_mode, issues):
    events, manifest = read_events(path, issues)
    responses, notices, compactions = [], [], []
    meta, context, settings = {}, {}, {}
    for line, event in events:
        kind, p = event.get('type'), event.get('payload') or {}
        if not isinstance(p, dict):
            issues.append({'code': 'invalid_payload', 'path': manifest['path'], 'line': line})
            continue
        if kind == 'session_meta':
            meta = p
        elif kind == 'turn_context':
            context = p
        elif kind == 'event_msg' and p.get('type') == 'thread_settings_applied':
            settings = p.get('thread_settings') or {}
        elif kind == 'compacted':
            compactions.append(line)
        if kind == 'token_usage_record' or (kind == 'event_msg' and p.get('type') == 'token_count' and isinstance(p.get('info'), dict)):
            row = {
                'path': manifest['path'], 'source_line': line, 'timestamp': event.get('timestamp'),
                'session_id': p.get('thread_id') or meta.get('id') or Path(path).stem,
                'turn_id': p.get('turn_id') or context.get('turn_id'),
                'model': context.get('model') or settings.get('model'),
                'effort': context.get('effort') or settings.get('reasoning_effort'),
                'service_tier': settings.get('service_tier'),
                'provider': settings.get('model_provider_id') or 'openai', 'payload': p,
            }
            (responses if kind == 'token_usage_record' else notices).append(row)
    mode = 'responses' if source_mode == 'auto' and responses else ('token-count' if source_mode == 'auto' else source_mode)
    manifest.update(session_id=meta.get('id'), source_mode=mode,
                    response_records=len(responses), token_count_events=len(notices), compaction_lines=compactions)
    selected = []
    if mode == 'responses':
        if not responses:
            issues.append({'code': 'missing_response_records', 'path': manifest['path'], 'line': None,
                           'detail': 'requested response source unavailable; use auto or token-count for legacy logs'})
        matched = defaultdict(list)
        cursor = 0
        for notice in notices:
            while cursor < len(responses) and responses[cursor]['source_line'] < notice['source_line']:
                cursor += 1
            prior = responses[cursor - 1] if cursor else None
            if prior and prior['payload'].get('usage') == notice['payload']['info'].get('last_token_usage'):
                matched[prior['source_line']].append(notice['source_line'])
            else:
                # A positive delta not represented by authoritative records may signal a mixed-format gap.
                issues.append({'code': 'unmatched_token_count', 'path': manifest['path'], 'line': notice['source_line'],
                               'detail': 'not added to response totals; inspect compaction/mixed-format coverage'})
        manifest['repeated_token_count_notifications'] = {str(k): v for k, v in matched.items() if len(v) > 1}
        manifest['responses_without_token_count_match'] = [r['source_line'] for r in responses if r['source_line'] not in matched]
        for row in responses:
            p = row.pop('payload')
            row.update(response_id=p.get('response_id'), usage=p.get('usage'), basis='response',
                       thread_token_usage=p.get('thread_token_usage'))
            selected.append(row)
    else:
        # Notifications lack response IDs; cumulative changes are the only reliable deduplication key.
        previous, epoch = None, 0
        for row in notices:
            info = row.pop('payload')['info']
            total, last = info.get('total_token_usage'), info.get('last_token_usage')
            if not isinstance(total, dict):
                issues.append({'code': 'legacy_missing_cumulative', 'path': manifest['path'], 'line': row['source_line'],
                               'detail': 'cannot distinguish repeated notifications; not counted'})
                continue
            try:
                usage_values(total)
            except ValueError as exc:
                issues.append({'code': 'invalid_cumulative', 'path': manifest['path'], 'line': row['source_line'], 'detail': str(exc)})
                continue
            keys = [k for k in COUNTERS if total.get(k) is not None]
            signature = {k: total[k] for k in keys}
            if previous is not None and signature == previous:
                continue
            reset = previous is not None and any(k not in previous or total[k] < previous[k] for k in keys)
            if previous is None or reset:
                if reset:
                    epoch += 1
                    issues.append({'code': 'legacy_counter_reset', 'path': manifest['path'], 'line': row['source_line'],
                                   'detail': 'starts a new segment using last usage; prior unseen amounts are not invented'})
                current = last if isinstance(last, dict) else (total if previous is None else None)
                if current is None:
                    issues.append({'code': 'legacy_unresolved_reset', 'path': manifest['path'], 'line': row['source_line']})
                    previous = signature
                    continue
                if previous is None and isinstance(last, dict) and any(total.get(k) != last.get(k) for k in keys):
                    issues.append({'code': 'legacy_carried_baseline', 'path': manifest['path'], 'line': row['source_line'],
                                   'detail': 'counts first last usage only, not unseen earlier cumulative history'})
            else:
                current = {k: total[k] - previous[k] for k in keys}
            row.update(response_id=None, usage=current, basis='cumulative_delta',
                       legacy_key=f"{row['session_id']}:{epoch}:{digest(signature)}")
            selected.append(row)
            previous = signature
        manifest['legacy_notice'] = 'Cumulative deltas, not verified individual response identities; counts may combine multiple calls.'
    return selected, manifest


def summarize(rows):
    metrics = list(COUNTERS) + ['uncached_input_tokens']
    result = {'records': len(rows), 'response_records': sum(r['basis'] == 'response' for r in rows),
              'legacy_delta_records': sum(r['basis'] != 'response' for r in rows)}
    for key in metrics:
        values = [r['usage'].get(key) for r in rows]
        result[key] = None if any(v is None for v in values) else sum(values)
    eligible = [r for r in rows if r['weighted_tokens'] is not None]
    subtotal = sum((Decimal(r['weighted_tokens']) for r in eligible), Decimal(0))
    result['weighted_tokens'] = str(subtotal) if len(eligible) == len(rows) else None
    result['weighted_covered_records'] = len(eligible)
    result['weighted_covered_tokens'] = str(subtotal)
    i, r = result['input_tokens'], result['cached_input_tokens']
    result['cache_hit_rate'] = r / i if i and r is not None else None
    return result


def audit_paths(paths, source_mode='auto', since=None, until=None, models=None,
                profile=None, include_records=False):
    if source_mode not in ('auto', 'responses', 'token-count'):
        raise ValueError('invalid source mode')
    profile = check_profile(profile or DEFAULT_PROFILE)
    since = instant(since) if isinstance(since, str) else since
    until = instant(until) if isinstance(until, str) else until
    if since and until and since >= until:
        raise ValueError('since must precede until; interval is [since, until)')
    issues, manifests, parsed = [], [], []
    for path in paths:
        records, manifest = parse_file(path, source_mode, issues)
        parsed.extend(records)
        manifests.append(manifest)
    unique, conflicts, duplicate_count, validated = {}, set(), 0, []
    for row in parsed:
        try:
            row['usage'] = usage_values(row['usage'])
            row['_time'] = instant(row['timestamp'])
            if row['basis'] == 'response' and (not isinstance(row.get('response_id'), str) or not row['response_id']):
                raise ValueError('authoritative response lacks response_id')
            for field in ('session_id', 'provider', 'model', 'effort', 'service_tier'):
                if row[field] is not None and not isinstance(row[field], str):
                    raise ValueError(field + ' must be a string or absent')
        except (ValueError, TypeError, AttributeError) as exc:
            issues.append({'code': 'invalid_record', 'path': row['path'], 'line': row['source_line'], 'detail': str(exc)})
            continue
        key = (row['provider'], row['response_id'] if row['basis'] == 'response' else row['legacy_key'])
        validated.append(row)
        if key in unique:
            original = unique[key]
            if row['usage'] != original['usage'] or row['model'] != original['model']:
                conflicts.add(key)
                issues.append({'code': 'response_conflict', 'path': row['path'], 'line': row['source_line'],
                               'detail': 'conflicting same-ID records excluded, not silently replaced'})
            else:
                duplicate_count += 1
                original['duplicate_sources'].append({'path': row['path'], 'line': row['source_line']})
            continue
        row['duplicate_sources'] = []
        unique[key] = row
    complete = [row for key, row in unique.items() if key not in conflicts]
    # Check unfiltered per-file totals when complete authoritative records are present.
    for manifest in manifests:
        # Check each physical file independently before cross-file deduplication.
        own_map = {(r['provider'], r['response_id']): r for r in validated
                   if r['path'] == manifest['path'] and r['basis'] == 'response'
                   and (r['provider'], r['response_id']) not in conflicts}
        own = list(own_map.values())
        totals = [r for r in own if isinstance(r.get('thread_token_usage'), dict)]
        if totals:
            last = max(totals, key=lambda r: r['source_line'])['thread_token_usage']
            differences = {}
            for k in COUNTERS:
                vals = [r['usage'][k] for r in own]
                if last.get(k) is not None and all(v is not None for v in vals) and sum(vals) != last[k]:
                    differences[k] = {'sum': sum(vals), 'reported': last[k]}
            manifest['cumulative_check'] = {'status': 'mismatch' if differences else 'matched', 'differences': differences}
            if differences:
                issues.append({'code': 'cumulative_mismatch', 'path': manifest['path'], 'line': None,
                               'detail': 'response totals differ from reported thread totals; may be a sliced or mixed-format log'})
    rows = []
    weights = {k: Decimal(v) for k, v in profile['weights'].items()}
    for row in sorted(complete, key=lambda r: (r['_time'], r['path'], r['source_line'])):
        t = row.pop('_time')
        if (since and t < since) or (until and t >= until) or (models and row['model'] not in models):
            continue
        u = row['usage']
        row['weighted_tokens'] = None
        if row['model'] in profile['models'] and u['cached_input_tokens'] is not None:
            row['weighted_tokens'] = str(u['uncached_input_tokens'] * weights['uncached_input']
                                         + u['cached_input_tokens'] * weights['cached_input']
                                         + u['output_tokens'] * weights['output'])
        row.pop('thread_token_usage', None)
        rows.append(row)
    groups = defaultdict(list)
    sessions = defaultdict(list)
    for row in rows:
        groups[(row['model'], row['effort'], row['service_tier'])].append(row)
        sessions[row['session_id']].append(row)
    invalid_codes = {'invalid_json_line', 'invalid_payload', 'invalid_record', 'response_conflict',
                     'legacy_missing_cumulative', 'invalid_cumulative', 'legacy_unresolved_reset',
                     'legacy_carried_baseline', 'missing_response_records', 'cumulative_mismatch'}
    status = 'partial' if any(i['code'] in invalid_codes for i in issues) else 'ok'
    result = {
        'schema_version': VERSION, 'status': status,
        'profile': {**profile, 'sha256': digest(profile), 'unit': 'weighted_tokens', 'money_conversion': False},
        'filters': {'since': since.isoformat() if since else None, 'until_exclusive': until.isoformat() if until else None,
                    'models': sorted(models) if models else []},
        'source_files': manifests, 'duplicate_response_records': duplicate_count,
        'issues': issues, 'summary': summarize(rows),
        'by_session': [{'session_id': key, **summarize(vals)} for key, vals in sorted(sessions.items())],
        'by_model': [{'model': key[0], 'effort': key[1], 'service_tier': key[2], **summarize(vals)}
                     for key, vals in sorted(groups.items(), key=lambda pair: str(pair[0]))],
    }
    if include_records:
        result['records'] = rows
    return result


def render(report):
    lines = [f"Codex token audit: {report['status']} | profile={report['profile']['id']}",
             '| model / effort | records | input | cache read | uncached | output | raw total | weighted |',
             '|---|---:|---:|---:|---:|---:|---:|---:|']
    for row in report['by_model']:
        fields = ['records', 'input_tokens', 'cached_input_tokens', 'uncached_input_tokens',
                  'output_tokens', 'total_tokens', 'weighted_tokens']
        lines.append('| ' + str(row['model']) + ' / ' + str(row['effort']) + ' | '
                     + ' | '.join('unknown' if row[k] is None else str(row[k]) for k in fields) + ' |')
    lines.append('Weighted totals are reported only for exact models in the selected profile; no currency/credit conversion.')
    lines.append(f"Issues: {len(report['issues'])}; duplicate response records removed: {report['duplicate_response_records']}")
    for issue in report['issues'][:20]:
        lines.append(f"  {issue['code']}: {issue.get('path')}:{issue.get('line')}")
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('paths', nargs='+', help='Explicit rollout JSONL or context-kit usage snapshot JSON files')
    parser.add_argument('--source', choices=('auto', 'responses', 'token-count'), default='auto')
    parser.add_argument('--model', action='append', help='Exact model filter; repeatable')
    parser.add_argument('--since', help='Inclusive ISO timestamp/date')
    parser.add_argument('--until', help='Exclusive ISO timestamp/date')
    parser.add_argument('--timezone', default='Asia/Taipei', help='Zone for dates/timestamps without an offset')
    parser.add_argument('--profile', type=Path, help='JSON fixed weights and exact supported model names')
    parser.add_argument('--json', action='store_true', help='JSON output, including issues and source fingerprints')
    parser.add_argument('--records', action='store_true', help='Include per-response records in JSON')
    args = parser.parse_args()
    try:
        profile = json.loads(args.profile.read_text()) if args.profile else None
        report = audit_paths(args.paths, args.source,
                             instant(args.since, args.timezone) if args.since else None,
                             instant(args.until, args.timezone) if args.until else None,
                             args.model, profile, args.records)
        print(json.dumps(report, ensure_ascii=False, indent=2) if args.json else render(report))
        return 2 if report['status'] == 'partial' else 0
    except (OSError, ValueError, KeyError) as exc:
        parser.error(str(exc))


if __name__ == '__main__':
    sys.exit(main())
