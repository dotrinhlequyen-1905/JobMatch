from sqlalchemy import func, select

from ..models import Company, Job, Report, User

TARGETS = {"JOB": Job, "COMPANY": Company, "USER": User}


def get_target(db, target_type, target_id):
    return db.get(TARGETS[target_type], target_id)


def find_open(db, reporter, body):
    return db.scalar(
        select(Report.id).where(
            Report.reporter_id == reporter.id,
            Report.target_type == body.target_type,
            Report.target_id == body.target_id,
            Report.status == "OPEN",
        )
    )


def add(db, report):
    return db.add(report)


def list_for_reporter(db, user):
    return db.scalars(select(Report).where(Report.reporter_id == user.id).order_by(Report.id.desc())).all()


def reports(status):
    stmt = select(Report)
    return stmt.where(Report.status == status) if status else stmt


def count(db, stmt):
    return db.scalar(select(func.count()).select_from(stmt.subquery()))


def list_page(db, page, size, stmt):
    return db.scalars(stmt.order_by(Report.id.desc()).offset((page - 1) * size).limit(size)).all()


def lock(db, report_id):
    return db.get(Report, report_id, with_for_update=True)


def owner_of(db, report):
    target = get_target(db, report.target_type, report.target_id)
    if target is None:
        return None
    if report.target_type == "USER":
        return target
    company = target if report.target_type == "COMPANY" else target.company
    return company.owner
