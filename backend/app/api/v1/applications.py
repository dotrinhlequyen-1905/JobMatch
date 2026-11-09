from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ...core.database import get_db
from ...core.security import is_candidate, is_hr
from ...models import User
from ...schemas.applications import ApplyIn, TransitionIn
from ...services import applications as applications_service
from ...services import interviews as interviews_service

router = APIRouter(prefix="/applications", tags=["applications"])


@router.post("")
def apply(body: ApplyIn, user: User = Depends(is_candidate), db: Session = Depends(get_db)):
    return applications_service.apply(body=body, user=user, db=db)


@router.get("")
def my_applications(user: User = Depends(is_candidate), db: Session = Depends(get_db)):
    return applications_service.my_applications(user=user, db=db)


@router.post("/{app_id}/withdraw")
def withdraw(app_id: int, user: User = Depends(is_candidate), db: Session = Depends(get_db)):
    return applications_service.withdraw(app_id=app_id, user=user, db=db)


@router.get("/{app_id}/slots")
def available_slots(app_id: int, user: User = Depends(is_candidate), db: Session = Depends(get_db)):
    return interviews_service.available_slots(app_id=app_id, user=user, db=db)


@router.get("/jobs/{job_id}")
def job_applications(
    job_id: int, status: str | None = None, user: User = Depends(is_hr), db: Session = Depends(get_db)
):
    return applications_service.job_applications(job_id=job_id, status=status, user=user, db=db)


@router.get("/{app_id}/manage")
def application_detail(app_id: int, user: User = Depends(is_hr), db: Session = Depends(get_db)):
    return applications_service.application_detail(app_id=app_id, user=user, db=db)


@router.patch("/{app_id}/status")
def transition(app_id: int, body: TransitionIn, user: User = Depends(is_hr), db: Session = Depends(get_db)):
    return applications_service.transition(app_id=app_id, body=body, user=user, db=db)
