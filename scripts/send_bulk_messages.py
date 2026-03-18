"""
send_bulk_messages.py
---------------------
CLI script to send a bulk broadcast message from the command line.

Usage:
    # Send to all contacts
    python scripts/send_bulk_messages.py --message "Hello everyone!"

    # Send to a specific segment tag
    python scripts/send_bulk_messages.py --message "Promo for VIPs!" --tag vip

    # Send to specific phone numbers
    python scripts/send_bulk_messages.py --message "Hi!" --phones 911234567890,919876543210

    # Dry run (preview recipients without sending)
    python scripts/send_bulk_messages.py --message "Test" --dry-run
"""

import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.broadcast_service import broadcast_text, _resolve_recipients
from utils.logger import get_logger

logger = get_logger("send_bulk_messages")


def main() -> None:
    """Parse CLI arguments and execute a bulk message broadcast."""
    parser = argparse.ArgumentParser(
        description="Send a bulk WhatsApp broadcast message."
    )
    parser.add_argument("--message", required=True, help="Message text to send.")
    parser.add_argument(
        "--tag",
        default=None,
        help="Target contacts with this segment tag.",
    )
    parser.add_argument(
        "--phones",
        default=None,
        help="Comma-separated list of phone numbers to message.",
    )
    parser.add_argument(
        "--name",
        default="CLI Broadcast",
        help="Campaign display name (for logging).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview recipient list without sending any messages.",
    )
    args = parser.parse_args()

    phones = (
        [p.strip() for p in args.phones.split(",") if p.strip()]
        if args.phones
        else None
    )

    # Resolve recipients for preview
    recipients = _resolve_recipients(phones, args.tag)

    if not recipients:
        print("⚠️  No recipients found. Check your contacts database.")
        sys.exit(0)

    print(f"\n📋 Broadcast Preview\n{'─' * 40}")
    print(f"   Message   : {args.message[:80]}{'…' if len(args.message) > 80 else ''}")
    print(f"   Campaign  : {args.name}")
    print(f"   Recipients: {len(recipients)}")
    if args.tag:
        print(f"   Tag filter: {args.tag}")

    if args.dry_run:
        print("\n🔍 Dry run — no messages sent.")
        print("   Recipients:")
        for phone in recipients[:20]:
            print(f"     • {phone}")
        if len(recipients) > 20:
            print(f"     … and {len(recipients) - 20} more.")
        return

    confirm = input(f"\n⚠️  Send to {len(recipients)} contact(s)? [y/N]: ").strip().lower()
    if confirm != "y":
        print("Aborted.")
        sys.exit(0)

    print("\n🚀 Sending …")
    result = broadcast_text(
        message=args.message,
        phones=phones,
        tag=args.tag,
        campaign_name=args.name,
    )

    print(
        f"\n✅ Broadcast complete:\n"
        f"   Sent   : {result['sent_count']}\n"
        f"   Failed : {result['failed_count']}\n"
    )


if __name__ == "__main__":
    main()
