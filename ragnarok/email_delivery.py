"""Resend delivery for approved ODIN alert drafts only."""
from __future__ import annotations

import httpx

from .config import Settings


class EmailDeliveryError(ValueError):
    pass


def send_approved_alert(settings: Settings, draft: dict) -> str:
    if draft.get("status") != "APPROVED" or not draft.get("recipient"):
        raise EmailDeliveryError("The alert must be approved with a recipient before sending")
    if not settings.resend_api_key:
        raise EmailDeliveryError("RESEND_API_KEY is not configured")
    if not settings.resend_from_email:
        raise EmailDeliveryError("Set RESEND_FROM_EMAIL to an address on a verified Resend domain")
    try:
        response = httpx.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {settings.resend_api_key}",
                "Content-Type": "application/json",
                "Idempotency-Key": f"odin-alert-{draft['id']}",
            },
            json={
                "from": settings.resend_from_email,
                "to": [draft["recipient"]],
                "subject": draft["subject"],
                "text": draft["body"],
            },
            timeout=20,
        )
    except httpx.HTTPError as exc:
        raise EmailDeliveryError(f"Resend connection failed: {type(exc).__name__}") from exc
    if response.status_code >= 400:
        raise EmailDeliveryError(f"Resend rejected the alert (HTTP {response.status_code})")
    try:
        provider_id = response.json()["id"]
    except (ValueError, KeyError, TypeError) as exc:
        raise EmailDeliveryError("Resend returned no email ID") from exc
    if not isinstance(provider_id, str) or not provider_id:
        raise EmailDeliveryError("Resend returned an invalid email ID")
    return provider_id
