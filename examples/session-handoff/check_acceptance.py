#!/usr/bin/env python3
"""Independent acceptance for the fictional invoice CLI handoff exercise."""

import csv
import io
import subprocess
import sys
import tempfile
from pathlib import Path


def run(cli: Path, data: Path, *options: str) -> list[list[str]]:
    result = subprocess.run(
        [sys.executable, str(cli), str(data), *options],
        capture_output=True,
        text=True,
    )
    if result.returncode:
        raise AssertionError(
            f"CLI exited {result.returncode} for {options}: {result.stderr.strip()}"
        )
    return list(csv.reader(io.StringIO(result.stdout)))


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: python3 check_acceptance.py /path/to/unpaid.py")
    cli = Path(sys.argv[1]).resolve()
    if not cli.is_file():
        raise SystemExit(f"missing CLI: {cli}")

    with tempfile.TemporaryDirectory() as directory:
        data = Path(directory) / "cases.csv"
        with data.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.writer(stream)
            writer.writerows(
                [
                    ("invoice_id", "status", "amount_cents"),
                    ("A", "unpaid", "249"),
                    ("B", "unpaid", "250"),
                    ("C", "paid", "9007199254740993"),
                    ("D", "unpaid", "9007199254740992"),
                    ("E", "unpaid", "9007199254740993"),
                ]
            )

        header = ["invoice_id", "amount_cents"]
        assert run(cli, data) == [
            header, ["A", "249"], ["B", "250"],
            ["D", "9007199254740992"], ["E", "9007199254740993"],
        ], "existing default behavior changed"
        assert run(cli, data, "--min-cents", "250") == [
            header, ["B", "250"], ["D", "9007199254740992"],
            ["E", "9007199254740993"],
        ], "inclusive minimum, unpaid filter, or source order is wrong"
        assert run(cli, data, "--min-cents", "9007199254740993") == [
            header, ["E", "9007199254740993"],
        ], "large integer cents lost precision or threshold is wrong"
        invalid = subprocess.run(
            [sys.executable, str(cli), str(data), "--min-cents", "-1"],
            capture_output=True,
            text=True,
        )
        assert invalid.returncode != 0, "negative minimum must be rejected"
    print("PASS: default behavior, inclusive minimum, unpaid filter, order, exact cents, invalid minimum")


if __name__ == "__main__":
    main()
