from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.models import User, UserStatus
from app.schemas import (
    PhoneVerifyRequest, PasswordSetupRequest, LoginRequest,
    TokenResponse, StatusResponse
)
from app.core.phone import normalize_phone
from app.core.security import verify_password, hash_password, create_access_token
from app.services.otp import OtpService
from app.services.audit import log_audit_event
from app.core.permissions import get_current_user

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/phone/verify", response_model=TokenResponse)
def verify_phone(req: PhoneVerifyRequest, response: Response, db: Session = Depends(get_db)):
    phone = normalize_phone(req.phone)
    user = db.query(User).filter(User.phone == phone).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found for this phone number.")

    valid = OtpService.verify_code(db, phone, req.otp_code)
    if not valid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired OTP code.")

    user.phone_verified_at = datetime.now(timezone.utc)
    user.status = UserStatus.ACTIVE
    db.commit()

    log_audit_event(
        db=db,
        action="user.phone_verified",
        target_type="user",
        target_id=str(user.id),
        actor_user_id=user.id
    )

    access_token = create_access_token(data={"sub": str(user.id), "role": user.role.value})

    # Set secure HttpOnly session cookie
    response.set_cookie(
        key="topline_token",
        value=access_token,
        httponly=True,
        samesite="lax",
        secure=settings.IS_PRODUCTION,
        max_age=7200
    )

    full_name = user.profile.full_name if user.profile else None

    return TokenResponse(
        access_token=access_token,
        user_id=user.id,
        role=user.role,
        phone=user.phone,
        full_name=full_name
    )

@router.post("/password", response_model=StatusResponse)
def set_password(
    req: PasswordSetupRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    current_user.password_hash = hash_password(req.password)
    db.commit()

    log_audit_event(
        db=db,
        action="user.password_updated",
        target_type="user",
        target_id=str(current_user.id),
        actor_user_id=current_user.id
    )

    return StatusResponse(success=True, message="Password updated successfully.")

@router.post("/login", response_model=TokenResponse)
def login(req: LoginRequest, response: Response, db: Session = Depends(get_db)):
    phone = normalize_phone(req.phone)
    user = db.query(User).filter(User.phone == phone).first()

    if not user or not user.password_hash:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid phone number or password.")

    if not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid phone number or password.")

    if user.status == UserStatus.SUSPENDED:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This account has been suspended.")

    access_token = create_access_token(data={"sub": str(user.id), "role": user.role.value})

    response.set_cookie(
        key="topline_token",
        value=access_token,
        httponly=True,
        samesite="lax",
        secure=settings.IS_PRODUCTION,
        max_age=7200
    )

    log_audit_event(
        db=db,
        action="user.logged_in",
        target_type="user",
        target_id=str(user.id),
        actor_user_id=user.id
    )

    full_name = user.profile.full_name if user.profile else None

    return TokenResponse(
        access_token=access_token,
        user_id=user.id,
        role=user.role,
        phone=user.phone,
        full_name=full_name
    )

@router.post("/logout", response_model=StatusResponse)
def logout(response: Response, current_user: User = Depends(get_current_user)):
    response.delete_cookie(key="topline_token")
    return StatusResponse(success=True, message="Successfully logged out.")

