from fastapi import APIRouter

from .v1 import (
    admin,
    applications,
    auth,
    companies,
    cvs,
    health,
    interviews,
    jobs,
    matching,
    metadata,
    notifications,
    payments,
    reports,
    users,
    webhooks,
)

api_router = APIRouter()
api_router.include_router(admin.router)
api_router.include_router(applications.router)
api_router.include_router(auth.router)
api_router.include_router(companies.router)
api_router.include_router(cvs.router)
api_router.include_router(interviews.router)
api_router.include_router(jobs.router)
api_router.include_router(matching.router)
api_router.include_router(metadata.router)
api_router.include_router(notifications.router)
api_router.include_router(payments.router)
api_router.include_router(reports.router)
api_router.include_router(users.router)
api_router.include_router(webhooks.router)
api_router.include_router(health.router)
