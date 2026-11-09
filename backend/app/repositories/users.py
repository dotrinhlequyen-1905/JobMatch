from ..models import CandidateProfile, User


def get_user(db, user_id):
    return db.get(User, user_id)


def get_profile(db, user):
    return db.get(CandidateProfile, user.id)


def add_profile(db, profile):
    return db.add(profile)
