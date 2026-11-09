"""Bổ sung theo đặc tả: phiên/khôi phục mật khẩu/xác minh email, hồ sơ ứng viên, lượt xem tin,
nhắc lịch phỏng vấn, báo cáo vi phạm và bảng kỹ năng chuẩn hóa (skills, cv_skills, job_skills)."""

import json

from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def _backfill_skills(connection):
    skill_ids: dict[str, int] = {}
    skills = sa.table("skills", sa.column("id", sa.Integer), sa.column("name", sa.String))

    def skill_id(name):
        if name not in skill_ids:
            connection.execute(skills.insert().values(name=name))
            skill_ids[name] = connection.execute(sa.select(skills.c.id).where(skills.c.name == name)).scalar_one()
        return skill_ids[name]

    for table, link, fk in (("cvs", "cv_skills", "cv_id"), ("jobs", "job_skills", "job_id")):
        for row_id, raw in connection.execute(sa.text(f"SELECT id, skills FROM {table}")).all():
            values = json.loads(raw) if isinstance(raw, str) else (raw or [])
            names = sorted({str(v).strip()[:100] for v in values if str(v).strip()})
            for name in names:
                connection.execute(
                    sa.text(f"INSERT INTO {link} ({fk}, skill_id) VALUES (:id, :skill)"),
                    {"id": row_id, "skill": skill_id(name)},
                )


def upgrade():
    connection = op.get_bind()
    with op.batch_alter_table("users") as batch:
        batch.add_column(sa.Column("email_verified_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("avatar_path", sa.String(300), nullable=True))
    # Tài khoản tạo trước khi có chức năng xác minh được coi là đã xác minh để không bị khóa khi bật bắt buộc.
    op.execute("UPDATE users SET email_verified_at = created_at")
    with op.batch_alter_table("jobs") as batch:
        batch.add_column(sa.Column("view_count", sa.Integer(), server_default="0", nullable=False))
    with op.batch_alter_table("interview_slots") as batch:
        batch.add_column(sa.Column("reminder_sent_at", sa.DateTime(timezone=True), nullable=True))

    op.create_table(
        "auth_tokens",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("purpose", sa.String(20), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_auth_tokens_user_id", "auth_tokens", ["user_id"])
    op.create_table(
        "candidate_profiles",
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), primary_key=True),
        sa.Column("headline", sa.String(300)),
        sa.Column("summary", sa.Text()),
        sa.Column("location", sa.String(100)),
        sa.Column("desired_role", sa.String(200)),
        sa.Column("expected_salary", sa.Integer()),
        sa.Column("is_public", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "reports",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("reporter_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("target_type", sa.String(20), nullable=False),
        sa.Column("target_id", sa.Integer(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("status", sa.String(20), server_default="OPEN", nullable=False),
        sa.Column("admin_note", sa.Text()),
        sa.Column("handled_by", sa.Integer(), sa.ForeignKey("users.id")),
        sa.Column("handled_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("target_type IN ('JOB','COMPANY','USER')", name="ck_reports_target_type"),
        sa.CheckConstraint("status IN ('OPEN','RESOLVED','DISMISSED')", name="ck_reports_status"),
    )
    op.create_index("ix_reports_reporter_id", "reports", ["reporter_id"])
    op.create_index("ix_reports_status", "reports", ["status"])
    op.create_table(
        "skills",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False, unique=True),
    )
    op.create_table(
        "cv_skills",
        sa.Column("cv_id", sa.Integer(), sa.ForeignKey("cvs.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("skill_id", sa.Integer(), sa.ForeignKey("skills.id"), primary_key=True),
    )
    op.create_index("ix_cv_skills_skill_id", "cv_skills", ["skill_id"])
    op.create_table(
        "job_skills",
        sa.Column("job_id", sa.Integer(), sa.ForeignKey("jobs.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("skill_id", sa.Integer(), sa.ForeignKey("skills.id"), primary_key=True),
    )
    op.create_index("ix_job_skills_skill_id", "job_skills", ["skill_id"])
    _backfill_skills(connection)


def downgrade():
    for table in ("job_skills", "cv_skills", "skills", "reports", "candidate_profiles", "auth_tokens"):
        op.drop_table(table)
    with op.batch_alter_table("interview_slots") as batch:
        batch.drop_column("reminder_sent_at")
    with op.batch_alter_table("jobs") as batch:
        batch.drop_column("view_count")
    with op.batch_alter_table("users") as batch:
        batch.drop_column("avatar_path")
        batch.drop_column("email_verified_at")
