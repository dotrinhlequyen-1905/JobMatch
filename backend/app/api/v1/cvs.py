from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session

from ...core.database import get_db
from ...core.security import current_user, is_candidate
from ...models import User
from ...schemas.cvs import CVUpdate
from ...services import cvs as cvs_service

router = APIRouter(prefix="/cvs", tags=["cvs"])


@router.get("")
def my_cvs(user: User = Depends(is_candidate), db: Session = Depends(get_db)):
    return cvs_service.my_cvs(user=user, db=db)


@router.post("")
async def upload_cv(
    file: UploadFile | None = File(None),
    text: str | None = Form(None),
    title: str | None = Form(None),
    user: User = Depends(is_candidate),
    db: Session = Depends(get_db),
):
    return await cvs_service.upload_cv(file=file, text=text, title=title, user=user, db=db)


@router.get("/{cv_id}")
def get_cv(cv_id: int, user: User = Depends(is_candidate), db: Session = Depends(get_db)):
    return cvs_service.get_cv(cv_id=cv_id, user=user, db=db)


@router.put("/{cv_id}")
def update_cv(cv_id: int, body: CVUpdate, user: User = Depends(is_candidate), db: Session = Depends(get_db)):
    return cvs_service.update_cv(cv_id=cv_id, body=body, user=user, db=db)


@router.delete("/{cv_id}")
def delete_cv(cv_id: int, user: User = Depends(is_candidate), db: Session = Depends(get_db)):
    return cvs_service.delete_cv(cv_id=cv_id, user=user, db=db)


@router.get("/{cv_id}/file")
def download_cv(cv_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    return cvs_service.download_cv(cv_id=cv_id, user=user, db=db)
