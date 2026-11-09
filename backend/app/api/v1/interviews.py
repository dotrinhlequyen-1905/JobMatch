from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ...core.database import get_db
from ...core.security import is_candidate, is_hr, require_roles
from ...models import User
from ...schemas.interviews import CancelIn, HoldIn, ResultIn
from ...services import interviews as interviews_service

router = APIRouter(prefix="/interview-slots", tags=["interviews"])


@router.post("/{slot_id}/hold")
def hold(slot_id: int, body: HoldIn, user: User = Depends(is_candidate), db: Session = Depends(get_db)):
    return interviews_service.hold(slot_id=slot_id, body=body, user=user, db=db)


@router.post("/{slot_id}/book")
def confirm(slot_id: int, user: User = Depends(is_candidate), db: Session = Depends(get_db)):
    return interviews_service.confirm(slot_id=slot_id, user=user, db=db)


@router.post("/{slot_id}/cancel")
def cancel(
    slot_id: int, body: CancelIn, user: User = Depends(require_roles("HR", "CANDIDATE")), db: Session = Depends(get_db)
):
    return interviews_service.cancel(slot_id=slot_id, body=body, user=user, db=db)


@router.post("/{slot_id}/result")
def result(slot_id: int, body: ResultIn, user: User = Depends(is_hr), db: Session = Depends(get_db)):
    return interviews_service.result(slot_id=slot_id, body=body, user=user, db=db)
