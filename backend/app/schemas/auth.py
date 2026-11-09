from pydantic import BaseModel, EmailStr, Field


class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    full_name: str = Field(min_length=2)
    phone: str | None = None
    role: str = Field(pattern="^(CANDIDATE|HR)$")
    company_name: str | None = None


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class RefreshIn(BaseModel):
    refresh_token: str = Field(min_length=10)


class ForgotPasswordIn(BaseModel):
    email: EmailStr


class ResetPasswordIn(BaseModel):
    token: str = Field(min_length=10)
    password: str = Field(min_length=6)


class TokenIn(BaseModel):
    token: str = Field(min_length=10)


class ProfileIn(BaseModel):
    full_name: str | None = None
    phone: str | None = None
    password: str | None = Field(default=None, min_length=6)
    current_password: str | None = None


class CandidateProfileIn(BaseModel):
    headline: str | None = Field(default=None, max_length=300)
    summary: str | None = Field(default=None, max_length=5000)
    location: str | None = Field(default=None, max_length=100)
    desired_role: str | None = Field(default=None, max_length=200)
    expected_salary: int | None = Field(default=None, ge=0)
    is_public: bool = True
