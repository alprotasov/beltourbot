import base64
import binascii
import hashlib
import hmac
import json
import logging
import time
from typing import Any, Dict, Optional
from urllib.parse import urlencode, urlparse, parse_qs
from app.core.config import settings

logger = logging.getLogger(__name__)

SECRET_KEY = getattr(settings, "deep_link_secret", getattr(settings, "SECRET_KEY", None))
if not SECRET_KEY:
    raise RuntimeError("Deep link secret is not configured")

BASE_URL = getattr(settings, "deep_link_base_url", f"https://t.me/{settings.bot_username}")

TTL = getattr(settings, "deep_link_url_expiry", None)
if TTL is not None:
    try:
        TTL = int(TTL)
        if TTL <= 0:
            raise ValueError("must be positive")
    except Exception as e:
        raise RuntimeError(f"Invalid deep_link_url_expiry configuration: {e}")

def generate_deeplink(payload: Dict[str, Any]) -> str:
    data = dict(payload)
    if TTL is not None:
        data["_ts"] = int(time.time())
    json_bytes = json.dumps(data, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    data_b64 = base64.urlsafe_b64encode(json_bytes).rstrip(b"=").decode("ascii")
    sig = hmac.new(SECRET_KEY.encode("utf-8"), json_bytes, hashlib.sha256).digest()
    sig_b64 = base64.urlsafe_b64encode(sig).rstrip(b"=").decode("ascii")
    token = f"{data_b64}.{sig_b64}"
    return f"{BASE_URL}?{urlencode({'start': token})}"

def parse_deeplink(link: str) -> Optional[Dict[str, Any]]:
    token = link
    if link.startswith(("http://", "https://")):
        parsed = urlparse(link)
        qs = parse_qs(parsed.query)
        values = qs.get("start") or qs.get("startgroup") or []
        if not values:
            logger.warning("No deep link token found in query string")
            return None
        token = values[0]
    parts = token.split(".")
    if len(parts) != 2:
        logger.warning("Deep link token has invalid format")
        return None
    data_b64, sig_b64 = parts
    try:
        pad = "=" * (-len(data_b64) % 4)
        json_bytes = base64.urlsafe_b64decode(data_b64 + pad)
    except (binascii.Error, ValueError) as e:
        logger.warning("Invalid base64 data in deep link: %s", e)
        return None
    try:
        data_obj = json.loads(json_bytes.decode("utf-8"))
    except json.JSONDecodeError as e:
        logger.warning("Invalid JSON in deep link: %s", e)
        return None
    if not isinstance(data_obj, dict):
        logger.warning("Decoded deep link data is not a dict: %r", data_obj)
        return None
    expected_sig = hmac.new(SECRET_KEY.encode("utf-8"), json_bytes, hashlib.sha256).digest()
    try:
        pad2 = "=" * (-len(sig_b64) % 4)
        sig_bytes = base64.urlsafe_b64decode(sig_b64 + pad2)
    except (binascii.Error, ValueError) as e:
        logger.warning("Invalid signature base64 in deep link: %s", e)
        return None
    if not hmac.compare_digest(expected_sig, sig_bytes):
        logger.warning("Signature mismatch in deep link")
        return None
    if TTL is not None:
        ts = data_obj.get("_ts")
        if not isinstance(ts, int):
            logger.warning("Timestamp missing or invalid in deep link")
            return None
        if time.time() - ts > TTL:
            logger.warning("Deep link has expired")
            return None
        data_obj.pop("_ts", None)
    return data_obj