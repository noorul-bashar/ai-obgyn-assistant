import logging

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


class NotFoundError(Exception):
    def __init__(self, message: str):
        self.message = message


class RetrievalError(Exception):
    """Raised when the vector store / RAG retrieval step fails."""

    def __init__(self, message: str):
        self.message = message


class LLMGenerationError(Exception):
    """Raised when the LLM provider fails or returns an unusable response."""

    def __init__(self, message: str):
        self.message = message


from sqlalchemy.exc import SQLAlchemyError


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(NotFoundError)
    async def not_found_handler(request: Request, exc: NotFoundError):
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"detail": exc.message})

    @app.exception_handler(RetrievalError)
    async def retrieval_error_handler(request: Request, exc: RetrievalError):
        logger.error("Retrieval error: %s", exc.message)
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"detail": "Knowledge base is temporarily unavailable.", "error": exc.message},
        )

    @app.exception_handler(LLMGenerationError)
    async def llm_error_handler(request: Request, exc: LLMGenerationError):
        logger.error("LLM generation error: %s", exc.message)
        detail_msg = f"LLM generation failed: {exc.message}" if exc.message else (
            "The assistant could not generate a response right now. "
            "Please contact your care provider directly if this is urgent."
        )
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"detail": detail_msg},
        )

    @app.exception_handler(SQLAlchemyError)
    async def db_error_handler(request: Request, exc: SQLAlchemyError):
        logger.error("Database error: %s", exc)
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"detail": "Database connection error. Ensure PostgreSQL is running locally at localhost:5432 or check DATABASE_URL in .env."},
        )
