import re

from fastapi import HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from ..config import settings
from ..models import Company, User
from ..repositories import companies as queries
from ..schemas.companies import CompanyIn
from ..services.common import company_out, job_out
from .users import store_image

LOGO_URL_PREFIX = "/api/v1/companies/logos/"
LOGO_FILE = re.compile(r"[0-9a-f]{32}\.(png|jpe?g|webp)")


def _company(user: User):
    if not user.company:
        raise HTTPException(400, "Tài khoản chưa có hồ sơ công ty")
    return user.company


def get_company(*, user: User):
    return company_out(_company(user), resolve_logo=False)


def create_company(*, body: CompanyIn, user: User, db: Session):
    if user.company:
        raise HTTPException(409, "Tài khoản đã có hồ sơ công ty; hãy cập nhật hồ sơ hiện tại")
    company = Company(owner=user, status="PENDING", **body.model_dump())
    queries.add(db, company)
    db.commit()
    return company_out(company, resolve_logo=False)


def update_company(*, body: CompanyIn, user: User, db: Session):
    c = _company(user)
    for k, v in body.model_dump().items():
        setattr(c, k, v)
    if c.status == "REJECTED":
        c.status = "PENDING"
    db.commit()
    return company_out(c, resolve_logo=False)


async def upload_logo(*, file: UploadFile, user: User, db: Session):
    c = _company(user)
    name = await store_image(file, "logos")
    old = c.logo_url
    c.logo_url = LOGO_URL_PREFIX + name.rsplit("/", 1)[-1]
    db.commit()
    if old and old.startswith(LOGO_URL_PREFIX):
        (settings.upload_dir / "logos" / old.removeprefix(LOGO_URL_PREFIX)).unlink(missing_ok=True)
    return company_out(c, resolve_logo=False)


def logo(*, filename: str):
    path = settings.upload_dir / "logos" / filename
    if not LOGO_FILE.fullmatch(filename) or not path.is_file():
        raise HTTPException(404, "Không tìm thấy logo")
    return FileResponse(path)


def companies(*, q: str | None = None, page: int = 1, size: int = 20, db: Session):
    stmt = queries.approved()
    if q:
        stmt = queries.filter_name(q, stmt)
    total = queries.count(db, stmt)
    counts = dict(queries.open_job_counts(db))
    rows = queries.list_page(db, page, size, stmt)
    return {"total": total, "items": [{**company_out(c), "open_jobs": counts.get(c.id, 0)} for c in rows]}


def company_detail(*, company_id: int, db: Session):
    c = queries.get(db, company_id)
    if not c or c.status != "APPROVED":
        raise HTTPException(404, "Không tìm thấy công ty")
    jobs = queries.list_open_jobs(db, c)
    return {**company_out(c), "jobs": [job_out(j, full=False) for j in jobs]}
