"""Mô hình dữ liệu (SQLAlchemy 2)."""

from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .core.database import Base
from .core.vector import Embedding


def utcnow():
    return datetime.now(timezone.utc)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class User(TimestampMixin, Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(30))
    role: Mapped[str] = mapped_column(String(20), index=True)
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE")
    premium_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    email_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    avatar_path: Mapped[str | None] = mapped_column(String(300))
    company: Mapped["Company | None"] = relationship(back_populates="owner", uselist=False)
    profile: Mapped["CandidateProfile | None"] = relationship(back_populates="user", uselist=False)


class AuthToken(TimestampMixin, Base):
    """Token một lần/có hạn: REFRESH (phiên), RESET (đặt lại mật khẩu), VERIFY (xác minh email). Chỉ lưu SHA-256."""

    __tablename__ = "auth_tokens"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    purpose: Mapped[str] = mapped_column(String(20))
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    user: Mapped[User] = relationship()


class CandidateProfile(TimestampMixin, Base):
    __tablename__ = "candidate_profiles"
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    headline: Mapped[str | None] = mapped_column(String(300))
    summary: Mapped[str | None] = mapped_column(Text)
    location: Mapped[str | None] = mapped_column(String(100))
    desired_role: Mapped[str | None] = mapped_column(String(200))
    expected_salary: Mapped[int | None] = mapped_column(Integer)
    is_public: Mapped[bool] = mapped_column(Boolean, default=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    user: Mapped[User] = relationship(back_populates="profile")


class Company(TimestampMixin, Base):
    __tablename__ = "companies"
    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True)
    name: Mapped[str] = mapped_column(String(255), index=True)
    description: Mapped[str | None] = mapped_column(Text)
    location: Mapped[str | None] = mapped_column(String(255))
    website: Mapped[str | None] = mapped_column(String(255))
    logo_url: Mapped[str | None] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(20), default="PENDING")
    owner: Mapped[User] = relationship(back_populates="company")
    jobs: Mapped[list["Job"]] = relationship(back_populates="company")


class Job(TimestampMixin, Base):
    __tablename__ = "jobs"
    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    title: Mapped[str] = mapped_column(String(300))
    description: Mapped[str] = mapped_column(Text)
    role: Mapped[str] = mapped_column(String(40), index=True)
    seniority: Mapped[str] = mapped_column(String(20))
    min_years: Mapped[int] = mapped_column(Integer, default=0)
    skills: Mapped[list] = mapped_column(JSON, default=list)
    salary_min: Mapped[int | None] = mapped_column(Integer)
    salary_max: Mapped[int | None] = mapped_column(Integer)
    city: Mapped[str | None] = mapped_column(String(100), index=True)
    status: Mapped[str] = mapped_column(String(20), default="PENDING", index=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    embedding: Mapped[bytes | None] = mapped_column(Embedding())
    processing_status: Mapped[str] = mapped_column(String(20), default="PENDING")
    embedding_revision: Mapped[int] = mapped_column(Integer, default=0)
    embedding_model: Mapped[str] = mapped_column(String(300), default="")
    view_count: Mapped[int] = mapped_column(Integer, default=0)
    company: Mapped[Company] = relationship(back_populates="jobs")


class CV(TimestampMixin, Base):
    __tablename__ = "cvs"
    id: Mapped[int] = mapped_column(primary_key=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(300))
    file_path: Mapped[str | None] = mapped_column(String(500))
    file_type: Mapped[str | None] = mapped_column(String(10))
    raw_text: Mapped[str] = mapped_column(Text)
    parsed: Mapped[dict] = mapped_column(JSON, default=dict)
    skills: Mapped[list] = mapped_column(JSON, default=list)
    years: Mapped[int] = mapped_column(Integer, default=0)
    seniority: Mapped[str] = mapped_column(String(20), default="junior")
    role: Mapped[str] = mapped_column(String(40), default="software_engineer")
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    embedding: Mapped[bytes | None] = mapped_column(Embedding())
    processing_status: Mapped[str] = mapped_column(String(20), default="PENDING")
    embedding_revision: Mapped[int] = mapped_column(Integer, default=0)
    embedding_model: Mapped[str] = mapped_column(String(300), default="")
    candidate: Mapped[User] = relationship()


class Application(TimestampMixin, Base):
    __tablename__ = "applications"
    __table_args__ = (
        Index(
            "uq_application_active",
            "job_id",
            "candidate_id",
            unique=True,
            postgresql_where=text("status NOT IN ('REJECTED','WITHDRAWN')"),
            sqlite_where=text("status NOT IN ('REJECTED','WITHDRAWN')"),
        ),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id"), index=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    cv_id: Mapped[int] = mapped_column(ForeignKey("cvs.id"))
    status: Mapped[str] = mapped_column(String(30), default="NEW", index=True)
    match_score: Mapped[float | None] = mapped_column(Float)
    cover_letter: Mapped[str | None] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    job: Mapped[Job] = relationship()
    candidate: Mapped[User] = relationship()
    cv: Mapped[CV] = relationship()
    history: Mapped[list["ApplicationHistory"]] = relationship(order_by="ApplicationHistory.id")


class ApplicationHistory(TimestampMixin, Base):
    __tablename__ = "application_history"
    id: Mapped[int] = mapped_column(primary_key=True)
    application_id: Mapped[int] = mapped_column(ForeignKey("applications.id"), index=True)
    from_status: Mapped[str | None] = mapped_column(String(30))
    to_status: Mapped[str] = mapped_column(String(30))
    actor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    note: Mapped[str | None] = mapped_column(Text)


class InterviewSlot(TimestampMixin, Base):
    __tablename__ = "interview_slots"
    __table_args__ = (
        Index(
            "uq_slot_application_active",
            "application_id",
            unique=True,
            postgresql_where=text("status IN ('HELD','BOOKED')"),
            sqlite_where=text("status IN ('HELD','BOOKED')"),
        ),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id"), index=True)
    hr_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    location: Mapped[str | None] = mapped_column(String(300))
    status: Mapped[str] = mapped_column(String(20), default="OPEN", index=True)
    held_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    held_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    application_id: Mapped[int | None] = mapped_column(ForeignKey("applications.id"))
    result: Mapped[str | None] = mapped_column(String(20))
    feedback: Mapped[str | None] = mapped_column(Text)
    reminder_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Package(Base):
    __tablename__ = "packages"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(40), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    target: Mapped[str] = mapped_column(String(20))
    price: Mapped[int] = mapped_column(Integer)
    duration_days: Mapped[int] = mapped_column(Integer)
    quota_jobs: Mapped[int] = mapped_column(Integer, default=0)
    description: Mapped[str | None] = mapped_column(Text)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class Order(TimestampMixin, Base):
    __tablename__ = "orders"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    package_id: Mapped[int] = mapped_column(ForeignKey("packages.id"))
    amount: Mapped[int] = mapped_column(Integer)
    order_code: Mapped[str | None] = mapped_column(String(40), unique=True)
    status: Mapped[str] = mapped_column(String(30), default="PENDING", index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    user: Mapped[User] = relationship()
    package: Mapped[Package] = relationship()


class PaymentTransaction(Base):
    __tablename__ = "payment_transactions"
    id: Mapped[int] = mapped_column(primary_key=True)
    sepay_tx_id: Mapped[str] = mapped_column(String(64), unique=True)
    order_id: Mapped[int | None] = mapped_column(ForeignKey("orders.id"), index=True)
    amount: Mapped[int] = mapped_column(Integer)
    content: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20))
    raw_payload: Mapped[dict] = mapped_column(JSON)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Refund(TimestampMixin, Base):
    __tablename__ = "refunds"
    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), unique=True)
    reason: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="REQUESTED")
    admin_note: Mapped[str | None] = mapped_column(Text)
    processed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    order: Mapped[Order] = relationship()


class Subscription(TimestampMixin, Base):
    __tablename__ = "subscriptions"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    package_id: Mapped[int] = mapped_column(ForeignKey("packages.id"))
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), unique=True)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    remaining_quota: Mapped[int] = mapped_column(Integer, default=0)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    package: Mapped[Package] = relationship()


class Notification(TimestampMixin, Base):
    __tablename__ = "notifications"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    type: Mapped[str] = mapped_column(String(40))
    title: Mapped[str] = mapped_column(String(300))
    link: Mapped[str | None] = mapped_column(String(300))
    read: Mapped[bool] = mapped_column(Boolean, default=False)


class Report(TimestampMixin, Base):
    """Báo cáo vi phạm do người dùng gửi; quản trị viên xử lý (FR-8.5)."""

    __tablename__ = "reports"
    id: Mapped[int] = mapped_column(primary_key=True)
    reporter_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    target_type: Mapped[str] = mapped_column(String(20))
    target_id: Mapped[int] = mapped_column(Integer)
    reason: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="OPEN", index=True)
    admin_note: Mapped[str | None] = mapped_column(Text)
    handled_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    handled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reporter: Mapped[User] = relationship(foreign_keys=[reporter_id])


class Skill(Base):
    """Danh mục kỹ năng chuẩn hóa; cv_skills/job_skills đồng bộ từ cột JSON skills."""

    __tablename__ = "skills"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)


class CVSkill(Base):
    __tablename__ = "cv_skills"
    cv_id: Mapped[int] = mapped_column(ForeignKey("cvs.id", ondelete="CASCADE"), primary_key=True)
    skill_id: Mapped[int] = mapped_column(ForeignKey("skills.id"), primary_key=True, index=True)


class JobSkill(Base):
    __tablename__ = "job_skills"
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), primary_key=True)
    skill_id: Mapped[int] = mapped_column(ForeignKey("skills.id"), primary_key=True, index=True)


class AuditLog(TimestampMixin, Base):
    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(primary_key=True)
    actor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(60), index=True)
    entity: Mapped[str] = mapped_column(String(40))
    entity_id: Mapped[int | None] = mapped_column(Integer)
    data: Mapped[dict | None] = mapped_column(JSON)
