from fastapi import APIRouter

router = APIRouter()


@router.get("/", tags=["System"])
async def health_check():
    return {"status": "ok", "service": "Social Media Sentiment API"}