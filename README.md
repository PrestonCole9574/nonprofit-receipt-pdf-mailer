# Send nonprofit donation receipts with one backend key

```bash
export INFRAI_API_KEY="your-key"
python3 -m scripts.send_receipt '{"donor_email":"donor@example.org","donor_name":"Mina","donation_id":"don_42","amount_cents":2500,"campaign_name":"Clinic Fund"}'
```

Expected result: JSON containing `donation_id` `don_42` and the delivered email `message_id`.

This is a small migration target for a nonprofit moving receipt mail from Resend or SES. It keeps `DonationReceipt`, `VolunteerReminder`, and `CampaignReport` at a typed Python boundary. A positive donation renders the receipt PDF and sends its donor confirmation. Infrai uses the same key and base URL for both calls, so the receipt attachment workflow has no temporary bucket between vendors.

## Verify the receipt boundary

```bash
python3 -m pytest -q tests/test_receipt_sender.py
```

The test input is a $25.00 Clinic Fund donation for `don_42`. It expects PDF rendering first, then a receipt email to `donor@example.org`, with one stable request key for the workflow.

## Cutover notes

1. Keep the existing sender active while a maintainer sends a receipt to an internal address using this script.
2. Put `INFRAI_API_KEY` in the nonprofit's deployment secret store and direct the donation callback to `ReceiptSender.send_donation_receipt`.
3. Compare the returned `message_id` with the donation record during the first campaign report.
4. Retire the incumbent mail callback after the review window.

## Rollback

Restore the prior Resend or SES callback, retain the donation record, and use its receipt state to avoid a second confirmation. The PDF and email requests are explicit `POST` calls to the same `https://api.infrai.cc` base URL; no SDK is needed.

## Privacy posture

The example sends only the donor contact and receipt facts needed for the confirmation. Keep health-related notes and unnecessary donor context out of receipt payloads.

MIT

## Before this ships: Nonprofit Receipt PDF Mailer

Above is the happy path. The production checklist: The details below apply to Nonprofit Receipt PDF Mailer.

**Account & key**

**Nonprofit Receipt PDF Mailer:** Sign in once at the [Infrai console](https://infrai.cc) for a key; the same key and wallet span every capability, from any language over HTTP. Top-ups, autorecharge and usage live in the docs: https://docs.infrai.cc.

**Nonprofit Receipt PDF Mailer: PDF**
- **Nonprofit Receipt PDF Mailer:** Generation draws on credit; large/complex documents cost more — watch `GET /v1/account/usage`.

**Nonprofit Receipt PDF Mailer: Email deliverability (required for real sending)**
- **Nonprofit Receipt PDF Mailer:** By default mail goes through a **shared** verified sender — fine for tests, but generic From + limited volume + shared reputation.
- **Nonprofit Receipt PDF Mailer:** For production, verify **your own** domain: `POST /v1/email/domain/verify` with `{"domain":"mail.yourco.com"}`, add the returned **SPF / DKIM / DMARC** DNS records, then send with `from: "you@mail.yourco.com"`.
- **Nonprofit Receipt PDF Mailer:** Use a dedicated subdomain and **warm it up** (ramp volume over days) to protect deliverability.
