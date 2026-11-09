from pydantic import BaseModel


class CompanyIn(BaseModel):
    name: str
    description: str | None = None
    location: str | None = None
    website: str | None = None
    logo_url: str | None = None
