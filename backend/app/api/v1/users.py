from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from ...core.database import get_db
from ...core.security import current_user, is_candidate
from ...models import User
from ...schemas.auth import CandidateProfileIn, ProfileIn
from ...services import users as users_service

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me")
def me(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return users_service.me(user=user, db=db)


@router.put("/me")
def update_me(body: ProfileIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    return users_service.update_me(body=body, user=user, db=db)


@router.post("/me/avatar")
async def upload_avatar(file: UploadFile = File(...), user: User = Depends(current_user), db: Session = Depends(get_db)):
    return await users_service.upload_avatar(file=file, user=user, db=db)


@router.get("/me/profile")
def my_profile(user: User = Depends(is_candidate), db: Session = Depends(get_db)):
    return users_service.my_profile(user=user, db=db)


@router.put("/me/profile")
def update_profile(body: CandidateProfileIn, user: User = Depends(is_candidate), db: Session = Depends(get_db)):
    return users_service.update_profile(body=body, user=user, db=db)


@router.get("/{user_id}/avatar")
def avatar(user_id: int, db: Session = Depends(get_db)):
    return users_service.avatar(user_id=user_id, db=db)
