from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from ...core.database import get_db
from ...core.security import is_hr
from ...models import User
from ...schemas.companies import CompanyIn
from ...services import companies as companies_service

router = APIRouter(prefix="/companies", tags=["companies"])


@router.post("")
def create_company(body: CompanyIn, user: User = Depends(is_hr), db: Session = Depends(get_db)):
    return companies_service.create_company(body=body, user=user, db=db)


@router.get("")
def companies(q: str | None = None, page: int = 1, size: int = 20, db: Session = Depends(get_db)):
    return companies_service.companies(q=q, page=page, size=size, db=db)


@router.get("/me")
def get_company(user: User = Depends(is_hr)):
    return companies_service.get_company(user=user)


@router.put("/me")
def update_company(body: CompanyIn, user: User = Depends(is_hr), db: Session = Depends(get_db)):
    return companies_service.update_company(body=body, user=user, db=db)


@router.post("/me/logo")
async def upload_logo(file: UploadFile = File(...), user: User = Depends(is_hr), db: Session = Depends(get_db)):
    return await companies_service.upload_logo(file=file, user=user, db=db)


@router.get("/logos/{filename}")
def logo(filename: str):
    return companies_service.logo(filename=filename)


@router.get("/{company_id}")
def company_detail(company_id: int, db: Session = Depends(get_db)):
    return companies_service.company_detail(company_id=company_id, db=db)
