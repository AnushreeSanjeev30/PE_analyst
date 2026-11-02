"""Question-answering endpoint over ingested deal documents."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from pe_analyst.auth.dependencies import get_current_user
from pe_analyst.auth.models import UserPublic
from pe_analyst.core.config import Settings, get_settings
from pe_analyst.llm.factory import build_llm_service

from .answering import RAGService, build_rag_service
from .schemas import RAGAnswerSchema, RAGQueryRequest

router = APIRouter(prefix="/rag", tags=["rag"])


def get_rag_service(settings: Settings = Depends(get_settings)) -> RAGService:  # noqa: B008
    return build_rag_service(settings, build_llm_service(settings))


@router.post(
    "/query",
    response_model=RAGAnswerSchema,
    summary="Ask a question grounded in previously ingested deal documents",
)
def query(
    request: RAGQueryRequest,
    rag_service: RAGService = Depends(get_rag_service),  # noqa: B008
    current_user: UserPublic = Depends(get_current_user),  # noqa: B008
) -> RAGAnswerSchema:
    result = rag_service.answer(request.question, document_id=request.document_id)
    return RAGAnswerSchema.from_result(result)


__all__ = ["router"]
