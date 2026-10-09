from fastapi import APIRouter

from app.utils.responses import success_response

router = APIRouter(tags=["Health"])


@router.get("/health")
def health() -> dict:
    return success_response("OK", {"status": "healthy"})
