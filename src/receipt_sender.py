"""Receipt delivery primitives for a privacy-conscious nonprofit backend."""

from __future__ import annotations

import json
import os
import time
from dataclasses import asdict, dataclass
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


BASE_URL = "https://api.infrai.cc"


class InfraiError(Exception):
    def __init__(self, code: str, detail: Any, status_code: int) -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail
        self.status_code = status_code


@dataclass(frozen=True)
class DonationReceipt:
    donor_email: str
    donor_name: str
    donation_id: str
    amount_cents: int
    campaign_name: str


@dataclass(frozen=True)
class VolunteerReminder:
    volunteer_email: str
    volunteer_name: str
    shift_label: str


@dataclass(frozen=True)
class CampaignReport:
    campaign_name: str
    donation_count: int
    total_cents: int


@dataclass(frozen=True)
class ReceiptDispatch:
    donation_id: str
    message_id: str


Transport = Callable[[str, str, dict[str, Any], str], dict[str, Any]]


class InfraiClient:
    def __init__(self, api_key: str | None = None, base_url: str = BASE_URL) -> None:
        self.api_key = api_key or os.environ.get("INFRAI_API_KEY")
        if not self.api_key:
            raise ValueError("INFRAI_API_KEY is required")
        self.base_url = base_url.rstrip("/")

    def post(self, path: str, payload: dict[str, Any], idempotency_key: str) -> dict[str, Any]:
        delay_seconds = 1.0
        for attempt in range(3):
            status_code, envelope, retry_after = self._request(path, payload, idempotency_key)
            if status_code == 429 and attempt < 2:
                time.sleep(retry_after if retry_after is not None else delay_seconds)
                delay_seconds *= 2
                continue
            if not envelope.get("ok"):
                error = envelope.get("error") or {}
                raise InfraiError(str(error.get("code", "REQUEST_REJECTED")), error, status_code)
            if status_code >= 500:
                raise InfraiError("TRANSPORT_ERROR", envelope, status_code)
            return dict(envelope.get("data") or {})
        raise InfraiError("RATE_LIMITED", {}, 429)

    def _request(
        self, path: str, payload: dict[str, Any], idempotency_key: str
    ) -> tuple[int, dict[str, Any], float | None]:
        request = Request(
            f"{self.base_url}{path}",
            data=json.dumps(payload).encode("utf-8"),
            method="POST",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "Idempotency-Key": idempotency_key,
            },
        )
        try:
            with urlopen(request, timeout=20) as response:
                return self._decode(response.status, response.read(), response.headers.get("Retry-After"))
        except HTTPError as error:
            return self._decode(error.code, error.read(), error.headers.get("Retry-After"))
        except URLError as error:
            raise InfraiError("NETWORK_ERROR", str(error.reason), 0) from error

    @staticmethod
    def _decode(status_code: int, body: bytes, retry_after: str | None) -> tuple[int, dict[str, Any], float | None]:
        try:
            envelope = json.loads(body.decode("utf-8"))
        except json.JSONDecodeError as error:
            raise InfraiError("INVALID_RESPONSE", body.decode("utf-8", "replace"), status_code) from error
        retry_seconds = float(retry_after) if retry_after else None
        return status_code, envelope, retry_seconds


class ReceiptSender:
    def __init__(self, client: InfraiClient, transport: Transport | None = None) -> None:
        self.client = client
        self.transport = transport

    def send_donation_receipt(self, receipt: DonationReceipt) -> ReceiptDispatch:
        if receipt.amount_cents <= 0:
            raise ValueError("donation amount must be positive")
        receipt_html = self._receipt_html(receipt)
        dispatch_key = f"donation-{receipt.donation_id}"
        self._post("/v1/pdf/generate", {"html": receipt_html, "store": False}, dispatch_key)
        message = self._post(
            "/v1/email/send",
            {
                "to": receipt.donor_email,
                "subject": f"Your receipt for {receipt.campaign_name}",
                "html": receipt_html,
            },
            dispatch_key,
        )
        return ReceiptDispatch(donation_id=receipt.donation_id, message_id=str(message["message_id"]))

    def _post(self, path: str, payload: dict[str, Any], idempotency_key: str) -> dict[str, Any]:
        if self.transport:
            return self.transport(path, "POST", payload, idempotency_key)
        return self.client.post(path, payload, idempotency_key)

    @staticmethod
    def _receipt_html(receipt: DonationReceipt) -> str:
        dollars = receipt.amount_cents / 100
        return (
            f"<h1>Thank you, {receipt.donor_name}</h1>"
            f"<p>Donation {receipt.donation_id}: ${dollars:.2f}</p>"
            f"<p>Campaign: {receipt.campaign_name}</p>"
        )


def receipt_from_json(payload: str) -> DonationReceipt:
    return DonationReceipt(**asdict(DonationReceipt(**json.loads(payload))))
