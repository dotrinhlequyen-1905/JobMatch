from fastapi import APIRouter

from ...services import metadata as metadata_service

router = APIRouter(prefix="/metadata", tags=["metadata"])


@router.get("")
def meta():
    return metadata_service.meta()
