from ..repositories import expiry as queries


def close_expired_jobs(db):
    result = queries.close_expired_jobs(db)
    db.commit()
    return result.rowcount
