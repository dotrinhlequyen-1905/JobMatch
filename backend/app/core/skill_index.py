"""Đồng bộ danh mục kỹ năng chuẩn hóa (skills, cv_skills, job_skills) từ cột JSON `skills` của CV/Job.

Cột JSON vẫn là nguồn cho matching; các bảng nối phục vụ truy vấn/thống kê theo ERD (bảng 4.9–4.11).
Đồng bộ chạy trong cùng flush nên luôn nhất quán với transaction ghi CV/Job.
"""

from sqlalchemy import delete, insert, inspect, select
from sqlalchemy.dialects import postgresql, sqlite

from ..models import CV, CVSkill, Job, JobSkill, Skill

LINKS = {CV: (CVSkill, CVSkill.cv_id, "cv_id"), Job: (JobSkill, JobSkill.job_id, "job_id")}


def _insert_ignore(connection, table, rows):
    if not rows:
        return
    dialect = connection.dialect.name
    if dialect == "postgresql":
        stmt = postgresql.insert(table).on_conflict_do_nothing()
    elif dialect == "sqlite":
        stmt = sqlite.insert(table).on_conflict_do_nothing()
    else:
        stmt = insert(table)
    connection.execute(stmt, rows)


def sync_entity(connection, entity):
    link, fk_column, fk_name = LINKS[type(entity)]
    names = sorted({str(s).strip()[:100] for s in (entity.skills or []) if str(s).strip()})
    connection.execute(delete(link).where(fk_column == entity.id))
    if not names:
        return
    _insert_ignore(connection, Skill.__table__, [{"name": n} for n in names])
    ids = connection.execute(select(Skill.id).where(Skill.name.in_(names))).scalars().all()
    _insert_ignore(connection, link.__table__, [{fk_name: entity.id, "skill_id": i} for i in ids])


def after_flush(session, _context):
    changed = [
        obj
        for obj in (*session.new, *session.dirty)
        if type(obj) in LINKS
        and (obj in session.new or inspect(obj).attrs.skills.history.has_changes())
        and obj.id is not None
    ]
    if changed:
        connection = session.connection()
        for obj in changed:
            sync_entity(connection, obj)
