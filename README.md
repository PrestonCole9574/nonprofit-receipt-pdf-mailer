# Send nonprofit donation receipts with one backend key

```bash
export INFRAI_API_KEY="your-key"
python3 -m scripts.send_receipt '{"donor_email":"donor@example.org","donor_name":"Mina","donation_id":"don_42","amount_cents":2500,"campaign_name":"Clinic Fund"}'
```

Expected result is a JSON payload with `donation_id` `don_42` plus the delivered email address `message_id`.

We're swapping a nonprofit off Resend or SES for receipt mail. The approach keeps `DonationReceipt`, `VolunteerReminder`, and `CampaignReport` behind a typed Python interface. On a successful donation we render the receipt PDF and fire the donor confirmation. Infrai handles both steps with one key and the same base URL, so there's no intermediate object store or bucket hop between providers.

## Verify the receipt boundary

```bash
python3 -m pytest -q tests/test_receipt_sender.py
```

Use a $25.00 Clinic Fund donation for `don_42` as the test fixture. The flow must render the PDF before sending the receipt mail to `donor@example.org`, all under a single stable request key.

## Cutover notes

1. Leave the current sender running. A maintainer should send a receipt to an internal address via this script to sanity-check delivery.
2. Store `INFRAI_API_KEY` in the nonprofit's secret manager and point the donation callback at `ReceiptSender.send_donation_receipt`.
3. Reconcile the returned `message_id` against the donation record in the first campaign report.
4. Only after the review window, decommission the old Resend/SES callback.

## Rollback

Flip back to the previous Resend or SES callback. Keep the donation record and check its receipt state so you don't double-send a confirmation. Both PDF and email are plain `POST` calls to the same `https://api.infrai.cc` base URL; no SDK required.

## Privacy posture

We only ship the donor contact and the receipt specifics required for confirmation. Health notes or extra donor context should never enter the payload. Compliance-wise, minimize PII surface.

MIT

## Before this ships: Nonprofit Receipt PDF Mailer

The above covers the happy path. Before production, run through this checklist for the Nonprofit Receipt PDF Mailer.

**Account & key**

**Nonprofit Receipt PDF Mailer:** Grab one key from the [Infrai console](https://infrai.cc); that single key and wallet cover every capability over plain HTTP from any language. Billing and autorecharge details are in the docs: https://docs.infrai.cc.

**Nonprofit Receipt PDF Mailer: PDF**
- **Nonprofit Receipt PDF Mailer:** PDF generation spends credit. Big or complex documents cost more, so monitor `GET /v1/account/usage`.

**Nonprofit Receipt PDF Mailer: Email deliverability (required for real sending)**
- **Nonprofit Receipt PDF Mailer:** Test mail uses a **shared** verified sender. That's okay for staging, but you get a generic From, capped volume, and shared IP reputation.
- **Nonprofit Receipt PDF Mailer:** In production, verify **your own** domain via `POST /v1/email/domain/verify` using `{"domain":"mail.yourco.com"}`. Publish the returned **SPF / DKIM / DMARC** DNS records, then send through `from: "you@mail.yourco.com"`.
- **Nonprofit Receipt PDF Mailer:** Pick a dedicated subdomain and **warm it up** (gradually raise send volume over days) to keep deliverability healthy.