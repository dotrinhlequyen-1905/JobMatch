from pydantic import BaseModel


class ApplyIn(BaseModel):
    job_id: int
    cv_id: int | None = None
    cover_letter: str | None = None


class TransitionIn(BaseModel):
    to: str
    note: str | None = None
