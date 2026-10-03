from src.receipt_sender import DonationReceipt, InfraiClient, ReceiptSender


def test_positive_donation_renders_pdf_before_sending_receipt() -> None:
    calls: list[tuple[str, str, dict[str, object], str]] = []

    def transport(path: str, method: str, payload: dict[str, object], key: str) -> dict[str, object]:
        calls.append((path, method, payload, key))
        return {"message_id": "msg_42"} if path == "/v1/email/send" else {}

    receipt = DonationReceipt("donor@example.org", "Mina", "don_42", 2500, "Clinic Fund")
    result = ReceiptSender(InfraiClient(api_key="test-key"), transport).send_donation_receipt(receipt)

    assert result.message_id == "msg_42"
    assert [call[0] for call in calls] == ["/v1/pdf/generate", "/v1/email/send"]
    assert calls[0][2]["store"] is False
    assert calls[1][2]["to"] == "donor@example.org"
    assert calls[0][3] == calls[1][3] == "donation-don_42"
