from sqlalchemy import Text, cast, func, or_, select, update
from sqlalchemy.orm import joinedload

from ..core.clock import now
from ..core.filters import job_is_open
from ..models import CV, Application, Company, InterviewSlot, Job, Notification, User


def get(db, job_id):
    return db.get(Job, job_id)


def count_posts_for_quota(db, company):
    return count_posts(db, company)


def list_owned(db, c):
    return db.scalars(select(Job).where(Job.company_id == c.id).order_by(Job.created_at.desc())).all()


def application_counts(db, c):
    return db.execute(
        select(Application.job_id, func.count(), func.avg(Application.match_score))
        .join(Job)
        .where(Job.company_id == c.id)
        .group_by(Application.job_id)
    ).all()


def count_posts(db, c):
    """Số tin đã dùng lượt đăng (bản nháp chưa gửi duyệt không tính)."""
    return db.scalar(select(func.count()).select_from(Job).where(Job.company_id == c.id, Job.status != "DRAFT"))


def increment_views(db, job):
    return db.execute(update(Job).where(Job.id == job.id).values(view_count=Job.view_count + 1))


def add(db, job):
    return db.add(job)


def find_candidate(db, body):
    return db.get(User, body.candidate_id)


def has_application(db, cand, job):
    return db.scalar(select(Application.id).where(Application.job_id == job.id, Application.candidate_id == cand.id))


def find_invitation(db, cand, link):
    return db.scalar(
        select(Notification.id).where(
            Notification.user_id == cand.id, Notification.type == "INVITE", Notification.link == link
        )
    )


def add_invitation(db, cand, job, link, note):
    return db.add(
        Notification(
            user_id=cand.id, type="INVITE", link=link, title=f"{job.company.name} mời bạn ứng tuyển '{job.title}'{note}"
        )
    )


def application_status_counts(db, c):
    return db.execute(
        select(Application.status, func.count()).join(Job).where(Job.company_id == c.id).group_by(Application.status)
    ).all()


def job_status_counts(db, c):
    return db.execute(select(Job.status, func.count()).where(Job.company_id == c.id).group_by(Job.status)).all()


def upcoming_slots(db, user):
    return db.scalars(
        select(InterviewSlot)
        .where(InterviewSlot.hr_id == user.id, InterviewSlot.status == "BOOKED", InterviewSlot.start_at > now())
        .order_by(InterviewSlot.start_at)
        .limit(10)
    ).all()


def applications_for_slots(db, upcoming):
    return db.scalars(
        select(Application).where(Application.id.in_([s.application_id for s in upcoming if s.application_id]))
    )


def cv_pool_count(db):
    return db.scalar(select(func.count()).select_from(CV))


def open_jobs():
    return select(Job).join(Company).where(job_is_open())


def filter_keyword(like, stmt):
    return stmt.where(
        or_(
            Job.title.ilike(like),
            Company.name.ilike(like),
            Job.description.ilike(like),
            cast(Job.skills, Text).ilike(like),
        )
    )


def filter_role(role, stmt):
    return stmt.where(Job.role == role)


def filter_city(city, stmt):
    return filter_cities([city], stmt)


def filter_cities(cities, stmt):
    selected = {city.strip() for city in cities if city.strip()}
    if "Remote" in selected:
        selected.update(("Làm việc từ xa", "Làm từ xa"))
    return stmt.where(Job.city.in_(sorted(selected))) if selected else stmt


def filter_salary_range(salary_range, stmt):
    # UI buckets are [lower, upper); a salary interval may overlap several buckets.
    lower, upper = {
        "under_10": (None, 10_000_000),
        "10_15": (10_000_000, 15_000_000),
        "15_25": (15_000_000, 25_000_000),
        "over_25": (25_000_000, None),
    }[salary_range]
    stmt = stmt.where(or_(Job.salary_min.is_not(None), Job.salary_max.is_not(None)))
    # A missing endpoint leaves that side open; wholly undisclosed salaries never match.
    if lower is not None:
        stmt = stmt.where(or_(Job.salary_max.is_(None), Job.salary_max >= lower))
    if upper is not None:
        stmt = stmt.where(or_(Job.salary_min.is_(None), Job.salary_min < upper))
    return stmt


def filter_experience(experience, stmt):
    # min_years is integral, so both "none" and "under_1" select zero years.
    buckets = {
        "none": Job.min_years == 0,
        "under_1": Job.min_years < 1,
        "1_3": (Job.min_years >= 1) & (Job.min_years < 3),
        "3_5": (Job.min_years >= 3) & (Job.min_years < 5),
        "over_5": Job.min_years >= 5,
    }
    return stmt.where(or_(*(buckets[value] for value in experience)))


def filter_seniority(seniority, stmt):
    return stmt.where(Job.seniority == seniority)


def filter_company(company_id, stmt):
    return stmt.where(Job.company_id == company_id)


def filter_skill(skill, stmt):
    return stmt.where(cast(Job.skills, Text).ilike(f'%"{skill}"%'))


def count(db, stmt):
    return db.scalar(select(func.count()).select_from(stmt.subquery()))


def list_page(db, page, size, stmt, *, sort="newest"):
    ordering = {
        "newest": (Job.created_at.desc(), Job.id.desc()),
        "oldest": (Job.created_at.asc(), Job.id.asc()),
        "salary_desc": (
            func.coalesce(Job.salary_max, Job.salary_min).desc().nulls_last(),
            Job.created_at.desc(),
            Job.id.desc(),
        ),
    }[sort]
    return db.scalars(
        stmt.options(joinedload(Job.company)).order_by(*ordering).offset((page - 1) * size).limit(size)
    ).all()


def get_public(db, job_id):
    return db.get(Job, job_id)
