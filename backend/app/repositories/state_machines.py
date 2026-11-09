from sqlalchemy import update

from ..models import Application, ApplicationHistory, Notification


def compare_and_set(db, app, frm, to):
    return db.execute(
        update(Application)
        .where(Application.id == app.id, Application.status == frm)
        .values(status=to)
        .execution_options(synchronize_session=False)
    )


def append_history(db, actor_id, app, frm, note, to):
    return db.add(
        ApplicationHistory(application_id=app.id, from_status=frm, to_status=to, actor_id=actor_id, note=note)
    )


def append_notification(db, APP_STATUS_VI, app, to):
    return db.add(
        Notification(
            user_id=app.candidate_id,
            type="APPLICATION",
            title=f"Đơn ứng tuyển của bạn: {APP_STATUS_VI[to]}",
            link="/candidate/applications",
        )
    )
