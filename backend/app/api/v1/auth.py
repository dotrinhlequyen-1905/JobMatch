from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ...core.database import get_db
from ...core.security import current_user
from ...models import User
from ...schemas.auth import ForgotPasswordIn, LoginIn, RefreshIn, RegisterIn, ResetPasswordIn, TokenIn
from ...services import auth as auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register")
def register(body: RegisterIn, db: Session = Depends(get_db)):
    return auth_service.register(body=body, db=db)


@router.post("/login")
def login(body: LoginIn, db: Session = Depends(get_db)):
    return auth_service.login(body=body, db=db)


@router.post("/refresh")
def refresh(body: RefreshIn, db: Session = Depends(get_db)):
    return auth_service.refresh(body=body, db=db)


@router.post("/logout")
def logout(body: RefreshIn, db: Session = Depends(get_db)):
    return auth_service.logout(body=body, db=db)


@router.post("/forgot-password")
def forgot_password(body: ForgotPasswordIn, db: Session = Depends(get_db)):
    return auth_service.forgot_password(body=body, db=db)


@router.post("/reset-password")
def reset_password(body: ResetPasswordIn, db: Session = Depends(get_db)):
    return auth_service.reset_password(body=body, db=db)


@router.post("/verify-email")
def verify_email(body: TokenIn, db: Session = Depends(get_db)):
    return auth_service.verify_email(body=body, db=db)


@router.post("/resend-verification")
def resend_verification(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return auth_service.resend_verification(user=user, db=db)
