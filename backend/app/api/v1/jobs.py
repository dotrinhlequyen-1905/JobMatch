from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ...core.database import get_db
from ...core.security import is_hr, optional_user
from ...models import User
from ...schemas.interviews import SlotsIn
from ...schemas.jobs import InviteIn, JobIn, JobStatusIn
from ...services import interviews as interviews_service
from ...services import jobs as jobs_service
from ...services import matching as matching_service

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("")
def search_jobs(
    q: str | None = None,
    role: str | None = None,
    city: str | None = None,
    seniority: str | None = None,
    skill: str | None = None,
    company_id: int | None = None,
    cities: list[str] | None = Query(None),
    salary_range: Literal["under_10", "10_15", "15_25", "over_25"] | None = None,
    experience: list[Literal["none", "under_1", "1_3", "3_5", "over_5"]] | None = Query(None),
    sort: Literal["newest", "oldest", "salary_desc"] = "newest",
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    return jobs_service.search_jobs(
        q=q,
        role=role,
        city=city,
        seniority=seniority,
        skill=skill,
        company_id=company_id,
        cities=cities,
        salary_range=salary_range,
        experience=experience,
        sort=sort,
        page=page,
        size=size,
        db=db,
    )


@router.get("/quota")
def quota(user: User = Depends(is_hr), db: Session = Depends(get_db)):
    return jobs_service.quota(user=user, db=db)


@router.get("/owned")
def my_jobs(user: User = Depends(is_hr), db: Session = Depends(get_db)):
    return jobs_service.my_jobs(user=user, db=db)


@router.post("")
def create_job(body: JobIn, user: User = Depends(is_hr), db: Session = Depends(get_db)):
    return jobs_service.create_job(body=body, user=user, db=db)


@router.get("/stats")
def stats(user: User = Depends(is_hr), db: Session = Depends(get_db)):
    return jobs_service.stats(user=user, db=db)


@router.get("/{job_id}")
def job_detail(job_id: int, db: Session = Depends(get_db), user=Depends(optional_user)):
    return jobs_service.job_detail(job_id=job_id, db=db, user=user)


@router.get("/{job_id}/manage")
def get_job(job_id: int, user: User = Depends(is_hr), db: Session = Depends(get_db)):
    return jobs_service.get_job(job_id=job_id, user=user, db=db)


@router.put("/{job_id}")
def update_job(job_id: int, body: JobIn, user: User = Depends(is_hr), db: Session = Depends(get_db)):
    return jobs_service.update_job(job_id=job_id, body=body, user=user, db=db)


@router.patch("/{job_id}/status")
def change_status(job_id: int, body: JobStatusIn, user: User = Depends(is_hr), db: Session = Depends(get_db)):
    return jobs_service.change_status(job_id=job_id, body=body, user=user, db=db)


@router.get("/{job_id}/candidates")
def recommended_candidates(job_id: int, limit: int = 30, user: User = Depends(is_hr), db: Session = Depends(get_db)):
    return matching_service.recommended_candidates(job_id=job_id, limit=limit, user=user, db=db)


@router.post("/{job_id}/invite")
def invite_candidate(job_id: int, body: InviteIn, user: User = Depends(is_hr), db: Session = Depends(get_db)):
    return jobs_service.invite_candidate(job_id=job_id, body=body, user=user, db=db)


@router.get("/{job_id}/interview-slots")
def job_slots(job_id: int, user: User = Depends(is_hr), db: Session = Depends(get_db)):
    return interviews_service.job_slots(job_id=job_id, user=user, db=db)


@router.post("/{job_id}/interview-slots")
def add_slots(job_id: int, body: SlotsIn, user: User = Depends(is_hr), db: Session = Depends(get_db)):
    return interviews_service.add_slots(job_id=job_id, body=body, user=user, db=db)
