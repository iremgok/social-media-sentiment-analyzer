from fastapi import APIRouter, Request

router = APIRouter()


@router.get("/", tags=["System"])
async def health_check(request: Request):
    ml_models = getattr(request.app.state, "ml_models", {})
    return {
        "status": "healthy",
        "service": "Social Media Sentiment API",
        "models_loaded": bool(ml_models)
    }