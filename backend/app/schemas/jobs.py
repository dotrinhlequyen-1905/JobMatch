from typing import Literal

from pydantic import BaseModel, Field, model_validator


class JobIn(BaseModel):
    title: str = Field(min_length=3)
    description: str = Field(min_length=30)
    skills: list[str] | None = None
    min_years: int | None = Field(default=None, ge=0)
    seniority: str | None = None
    role: str | None = None
    city: str | None = None
    salary_min: int | None = Field(default=None, ge=0)
    salary_max: int | None = Field(default=None, ge=0)
    expires_in_days: int = 30
    submit: bool = True

    @model_validator(mode="after")
    def _salary_range(self):
        if self.salary_min is not None and self.salary_max is not None and self.salary_min > self.salary_max:
            raise ValueError("Lương tối thiểu không được lớn hơn lương tối đa")
        return self


class InviteIn(BaseModel):
    candidate_id: int
    message: str | None = None


class JobStatusIn(BaseModel):
    # CLOSED: đóng tin; PENDING: gửi duyệt bản nháp hoặc mở lại tin đã đóng (cần duyệt lại).
    status: Literal["CLOSED", "PENDING"]
    expires_in_days: int | None = Field(default=None, ge=1, le=90)
