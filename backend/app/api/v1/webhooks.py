from fastapi import APIRouter, Depends, Header, Request
from sqlalchemy.orm import Session

from ...core.database import get_db
from ...services import payment_api as payments_service

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/sepay")
async def sepay_webhook(request: Request, authorization: str | None = Header(None), db: Session = Depends(get_db)):
    return await payments_service.sepay_webhook(request=request, authorization=authorization, db=db)
