"""
import_contacts.py
-----------------
CLI script to import contacts from a CSV or Excel file into MongoDB.

Usage:
    python scripts/import_contacts.py --file contacts.csv
    python scripts/import_contacts.py --file contacts.xlsx --type excel
"""

import argparse
import sys
import os

# Allow imports from the project root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.contact_service import import_from_csv, import_from_excel
from utils.logger import get_logger

logger = get_logger("import_contacts")


def main() -> None:
    """Parse CLI arguments and run the contact import."""
    parser = argparse.ArgumentParser(
        description="Import contacts from CSV or Excel into MongoDB."
    )
    parser.add_argument(
        "--file",
        required=True,
        help="Path to the CSV or Excel file to import.",
    )
    parser.add_argument(
        "--type",
        choices=["csv", "excel"],
        default="csv",
        help="File type: 'csv' (default) or 'excel'.",
    )
    args = parser.parse_args()

    if not os.path.isfile(args.file):
        logger.error("File not found: '%s'", args.file)
        sys.exit(1)

    logger.info("Importing contacts from '%s' (type=%s) …", args.file, args.type)

    try:
        if args.type == "csv":
            result = import_from_csv(args.file)
        else:
            result = import_from_excel(args.file)

        print(
            f"\n✅ Import complete:\n"
            f"   Imported : {result['imported']}\n"
            f"   Skipped  : {result['skipped']}\n"
        )

    except Exception as exc:
        logger.error("Import failed: %s", exc)
        sys.exit(1)


if __name__ == "__main__":
    main()
