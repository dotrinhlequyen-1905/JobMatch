from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ...core.database import get_db
from ...core.security import is_candidate, require_roles
from ...models import User
from ...services import matching as matching_service

router = APIRouter(prefix="/matching", tags=["matching"])


@router.get("/gap")
def gap(
    cv_id: int, job_id: int, user: User = Depends(require_roles("CANDIDATE", "HR")), db: Session = Depends(get_db)
):
    return matching_service.gap(cv_id=cv_id, job_id=job_id, user=user, db=db)


@router.get("/cv-evaluation")
def cv_evaluation(
    cv_id: int, job_id: int | None = None, user: User = Depends(is_candidate), db: Session = Depends(get_db)
):
    return matching_service.cv_evaluation(cv_id=cv_id, job_id=job_id, user=user, db=db)


@router.get("/jobs")
def recommendations(cv_id: int | None = None, user: User = Depends(is_candidate), db: Session = Depends(get_db)):
    return matching_service.recommendations(cv_id=cv_id, user=user, db=db)


@router.get("/jobs/{job_id}/match")
def match_one(job_id: int, cv_id: int | None = None, user: User = Depends(is_candidate), db: Session = Depends(get_db)):
    return matching_service.match_one(job_id=job_id, cv_id=cv_id, user=user, db=db)
