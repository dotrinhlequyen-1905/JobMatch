from pydantic import BaseModel


class CVUpdate(BaseModel):
    title: str | None = None
    skills: list[str] | None = None
    years: int | None = None
    role: str | None = None
    is_default: bool | None = None
