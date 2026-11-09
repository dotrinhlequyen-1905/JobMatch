from sqlalchemy import select


def get(db, entity_id, model):
    return db.get(model, entity_id)


def pending(db, model):
    return db.execute(select(model.id, model.embedding_revision).where(model.processing_status == "PENDING").limit(200))
