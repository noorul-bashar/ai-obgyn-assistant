from fastapi import APIRouter

from app.api.v1.endpoints import chat, documents, health, patients

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(patients.router, prefix="/patients", tags=["patients"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(documents.router, prefix="/documents", tags=["documents"])
