from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ...core.database import get_db
from ...core.security import current_user
from ...models import User
from ...services import notifications as notifications_service

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("")
def list_notifications(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return notifications_service.list_notifications(user=user, db=db)


@router.post("/read-all")
def read_all(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return notifications_service.read_all(user=user, db=db)
