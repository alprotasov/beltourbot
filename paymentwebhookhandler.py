import hmac
import hashlib
import datetime
import json
from enum import Enum

from fastapi import APIRouter, Request, HTTPException, Depends
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from db.session import get_db
from models.payment import Payment as PaymentModel
from models.subscription import Subscription as SubscriptionModel
from config import settings
from logger import logger

router = APIRouter(prefix="/webhooks", tags=["payment"])

class CurrencyEnum(str, Enum):
    USD = "USD"
    EUR = "EUR"
    BYN = "BYN"

class PaymentWebhookPayload(BaseModel):
    payment_id: str = Field(..., alias="payment_id")
    user_id: int = Field(..., alias="user_id")
    amount: float
    currency: CurrencyEnum
    status: str
    period_days: int = Field(default=settings.SUBSCRIPTION_PERIOD_DAYS)

    class Config:
        allow_population_by_field_name = True

def verify_signature(raw_body: bytes, signature: str) -> bool:
    secret = settings.PAYMENT_WEBHOOK_SECRET.encode()
    computed = hmac.new(secret, raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(computed, signature)

@router.post("/payment")
async def handle_payment_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    raw_body = await request.body()
    signature = request.headers.get("X-Payment-Signature", "")
    if not signature or not verify_signature(raw_body, signature):
        logger.warning("Invalid payment webhook signature")
        raise HTTPException(status_code=400, detail="Invalid signature")
    try:
        payload_data = json.loads(raw_body)
        payload = PaymentWebhookPayload(**payload_data)
    except (json.JSONDecodeError, ValidationError):
        logger.warning("Invalid payment webhook payload")
        raise HTTPException(status_code=400, detail="Invalid payload")
    if payload.status.lower() != "success":
        logger.info("Ignoring non-success payment: %s", payload.status)
        return {"status": "ignored"}
    try:
        await update_subscription(db, payload)
    except Exception:
        logger.error("Failed to process payment webhook")
        raise HTTPException(status_code=500, detail="Internal server error")
    return {"status": "success"}

async def update_subscription(db: AsyncSession, payload: PaymentWebhookPayload):
    try:
        async with db.begin():
            existing_payment = await db.get(PaymentModel, payload.payment_id)
            if existing_payment:
                logger.info("Payment %s already processed", payload.payment_id)
                return
            payment = PaymentModel(
                id=payload.payment_id,
                user_id=payload.user_id,
                amount=payload.amount,
                currency=payload.currency.value,
                status=payload.status,
                raw_payload=payload.dict(by_alias=True)
            )
            db.add(payment)
            stmt = select(SubscriptionModel).where(SubscriptionModel.user_id == payload.user_id).with_for_update()
            result = await db.execute(stmt)
            subscription = result.scalar_one_or_none()
            now = datetime.datetime.utcnow()
            start = subscription.expires_at if subscription and subscription.expires_at and subscription.expires_at > now else now
            expires_at = start + datetime.timedelta(days=payload.period_days)
            if subscription:
                subscription.expires_at = expires_at
                subscription.status = "active"
            else:
                new_subscription = SubscriptionModel(
                    user_id=payload.user_id,
                    expires_at=expires_at,
                    status="active"
                )
                db.add(new_subscription)
    except Exception:
        logger.error("Error updating subscription")
        raise