from fastapi import APIRouter
from app.api.v2.endpoints import tympani_bulk, hrv_bulk

api_router = APIRouter()

api_router.include_router(tympani_bulk.router, prefix="/tympani", tags=["tympani"])
api_router.include_router(hrv_bulk.router, prefix="/hrv", tags=["hrv"])
