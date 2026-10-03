"""Run one nonprofit donation receipt workflow."""

from __future__ import annotations

import argparse
import json

from src.receipt_sender import InfraiClient, ReceiptSender, receipt_from_json


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("receipt_json", help="DonationReceipt JSON")
    args = parser.parse_args()
    receipt = receipt_from_json(args.receipt_json)
    result = ReceiptSender(InfraiClient()).send_donation_receipt(receipt)
    print(json.dumps({"donation_id": result.donation_id, "message_id": result.message_id}))


if __name__ == "__main__":
    main()
