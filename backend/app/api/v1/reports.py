from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ...core.database import get_db
from ...core.security import current_user
from ...models import User
from ...schemas.reports import ReportIn
from ...services import reports as reports_service

router = APIRouter(prefix="/reports", tags=["reports"])


@router.post("")
def create(body: ReportIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    return reports_service.create(body=body, user=user, db=db)


@router.get("/mine")
def mine(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return reports_service.mine(user=user, db=db)
