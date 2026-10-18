#!/usr/bin/env python3
"""Synthetic fixture: list unpaid invoices in CSV source order."""

import argparse
import csv
import sys


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv_path", help="CSV with invoice_id,status,amount_cents")
    args = parser.parse_args()

    writer = csv.writer(sys.stdout, lineterminator="\n")
    writer.writerow(("invoice_id", "amount_cents"))
    with open(args.csv_path, newline="", encoding="utf-8") as source:
        for row in csv.DictReader(source):
            if row["status"] == "unpaid":
                # The existing behavior keeps money in exact integer cents.
                writer.writerow((row["invoice_id"], int(row["amount_cents"])))


if __name__ == "__main__":
    main()
