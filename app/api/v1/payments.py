import hmac
from datetime import datetime, timezone
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import (
    User, Payment, Entitlement, PaymentWebhookEvent,
    PaymentStatus, EntitlementType
)
from app.schemas import PaymentInitiateRequest, PaymentOut, MockPaymentConfirmRequest
from app.core.config import settings
from app.core.permissions import get_current_user
from app.core.phone import normalize_phone
from app.integrations.mpesa import get_payment_provider
from app.services.audit import log_audit_event

router = APIRouter(prefix="/payments", tags=["Payments"])

@router.post("", response_model=PaymentOut, status_code=status.HTTP_201_CREATED)
def initiate_payment(
    req: PaymentInitiateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Determine phone to charge: either requested or user's registered phone
    charge_phone = normalize_phone(req.phone_number) if req.phone_number else current_user.phone

    # Check if worker already has active entitlement
    existing_ent = (
        db.query(Entitlement)
        .filter(
            Entitlement.user_id == current_user.id,
            Entitlement.entitlement_type == EntitlementType.PLATFORM_ACCESS,
            Entitlement.revoked_at.is_(None)
        )
        .first()
    )
    if existing_ent:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Your platform access is already active."
        )

    # Server strictly controls amount: KSh 1,000 = 100,000 minor units
    amount_minor = settings.PLATFORM_ACCESS_FEE_MINOR
    currency = settings.PLATFORM_ACCESS_CURRENCY

    payment = Payment(
        user_id=current_user.id,
        purpose="platform_access",
        amount_minor=amount_minor,
        currency=currency,
        provider="mpesa" if settings.MPESA_ENVIRONMENT != "mock" else "mock",
        phone_number=charge_phone,
        status=PaymentStatus.INITIATED
    )
    db.add(payment)
    db.flush()

    try:
        provider = get_payment_provider()
        provider_resp = provider.initiate_stk_push(
            phone_number=charge_phone,
            amount_minor=amount_minor,
            account_reference=f"TL-{str(payment.id)[:8]}",
            transaction_desc="TopLine Access Fee"
        )
        payment.merchant_request_id = provider_resp.get("merchant_request_id")
        payment.checkout_request_id = provider_resp.get("checkout_request_id")
        payment.status = PaymentStatus.AWAITING_CONFIRMATION
        db.commit()
    except Exception as e:
        payment.status = PaymentStatus.FAILED
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Payment provider error: {str(e)}"
        )

    log_audit_event(
        db=db,
        action="payment.initiated",
        target_type="payment",
        target_id=str(payment.id),
        actor_user_id=current_user.id,
        metadata_json={
            "amount_minor": amount_minor,
            "currency": currency,
            "phone": charge_phone
        }
    )

    return payment

@router.get("/{payment_id}", response_model=PaymentOut)
def get_payment_status(
    payment_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if not payment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment record not found.")

    # Workers can only view their own payments
    if payment.user_id != current_user.id and current_user.role.value != "administrator":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

    return payment

@router.post("/mock/confirm", response_model=PaymentOut)
def mock_confirm_payment(
    req: MockPaymentConfirmRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    For development and testing environments:
    Safely confirms a pending payment without exposing real financial simulation in production.
    """
    if settings.APP_ENV == "production":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Mock payment endpoint disabled in production.")

    payment = db.query(Payment).filter(Payment.id == req.payment_id).first()
    if not payment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment record not found.")

    if payment.user_id != current_user.id and current_user.role.value != "administrator":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

    receipt = req.mpesa_receipt_number or f"MOCK_MPE_{str(payment.id)[:8]}"

    # Process idempotently
    if payment.status != PaymentStatus.CONFIRMED:
        payment.status = PaymentStatus.CONFIRMED
        payment.confirmed_at = datetime.now(timezone.utc)
        payment.provider_reference = receipt

        # Grant platform entitlement idempotently
        existing_ent = db.query(Entitlement).filter(Entitlement.source_payment_id == payment.id).first()
        if not existing_ent:
            ent = Entitlement(
                user_id=payment.user_id,
                entitlement_type=EntitlementType.PLATFORM_ACCESS,
                source_payment_id=payment.id,
                granted_at=datetime.now(timezone.utc),
                expires_at=None
            )
            db.add(ent)

        db.commit()

        log_audit_event(
            db=db,
            action="payment.confirmed",
            target_type="payment",
            target_id=str(payment.id),
            actor_user_id=current_user.id,
            metadata_json={"receipt": receipt}
        )

    return payment

@router.post("/mpesa/callback")
async def mpesa_callback(request: Request, token: str = "", db: Session = Depends(get_db)):
    """
    Idempotent M-Pesa Daraja callback handler.
    Validates amount, currency, phone, and receipt, and prevents duplicate processing.
    """
    # Safaricom does not sign callbacks. Without this shared-secret check anyone who knows a
    # checkout_request_id (workers can see their own) could forge a "paid" callback.
    if settings.MPESA_CALLBACK_TOKEN and not hmac.compare_digest(token, settings.MPESA_CALLBACK_TOKEN):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden.")

    body = await request.json()
    stk_callback = body.get("Body", {}).get("stkCallback", {})

    merchant_request_id = stk_callback.get("MerchantRequestID")
    checkout_request_id = stk_callback.get("CheckoutRequestID")
    result_code = stk_callback.get("ResultCode")
    result_desc = stk_callback.get("ResultDesc")

    dedup_key = f"daraja:{checkout_request_id}"

    # Check webhook deduplication
    existing_event = db.query(PaymentWebhookEvent).filter(PaymentWebhookEvent.event_reference == dedup_key).first()
    if existing_event:
        return {"ResultCode": 0, "ResultDesc": "Callback already processed"}

    webhook_event = PaymentWebhookEvent(
        provider="mpesa",
        event_reference=dedup_key,
        raw_payload=body,
        processing_status="processing"
    )
    db.add(webhook_event)
    db.flush()

    payment = db.query(Payment).filter(Payment.checkout_request_id == checkout_request_id).first()
    if payment:
        webhook_event.payment_id = payment.id

        if result_code == 0:
            # Payment successful from M-Pesa
            items = stk_callback.get("CallbackMetadata", {}).get("Item", [])
            meta = {item.get("Name"): item.get("Value") for item in items if "Name" in item}

            receipt = meta.get("MpesaReceiptNumber")
            amount = meta.get("Amount")
            phone = meta.get("PhoneNumber")

            # Validate amount matches expected KSh 1,000 (1,000 KES = 100,000 minor units)
            expected_amount = settings.PLATFORM_ACCESS_FEE_MINOR // 100
            if amount is not None and int(amount) == expected_amount:
                payment.status = PaymentStatus.CONFIRMED
                payment.confirmed_at = datetime.now(timezone.utc)
                payment.provider_reference = receipt

                # Grant entitlement idempotently
                existing_ent = db.query(Entitlement).filter(Entitlement.source_payment_id == payment.id).first()
                if not existing_ent:
                    ent = Entitlement(
                        user_id=payment.user_id,
                        entitlement_type=EntitlementType.PLATFORM_ACCESS,
                        source_payment_id=payment.id,
                        granted_at=datetime.now(timezone.utc),
                        expires_at=None
                    )
                    db.add(ent)
            else:
                payment.status = PaymentStatus.FAILED

        else:
            payment.status = PaymentStatus.FAILED

    webhook_event.processing_status = "completed"
    webhook_event.processed_at = datetime.now(timezone.utc)
    db.commit()

    return {"ResultCode": 0, "ResultDesc": "Accepted"}

