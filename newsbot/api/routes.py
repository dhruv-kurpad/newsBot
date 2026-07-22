"""HTTP route handlers."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from newsbot.config import get_settings
from newsbot.llm.summarizer import StructuredSummary
from newsbot.pipeline.digest import answer_question, run_daily_digest
from newsbot.vectorstore.store import VectorStore

router = APIRouter()


class StoreSummaryRequest(BaseModel):
    title: str = ""
    summary: str
    key_points: list[str] = Field(default_factory=list)
    important_facts: list[str] = Field(default_factory=list)
    why_it_matters: str = ""
    follow_up_questions: list[str] = Field(default_factory=list)
    links: list[str] = Field(default_factory=list)
    message_id: str = ""


class AskRequest(BaseModel):
    question: str


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/store-summary")
def store_summary(payload: StoreSummaryRequest) -> dict[str, Any]:
    settings = get_settings()
    summary = StructuredSummary(
        title=payload.title,
        summary=payload.summary,
        key_points=payload.key_points,
        important_facts=payload.important_facts,
        why_it_matters=payload.why_it_matters,
        follow_up_questions=payload.follow_up_questions,
        links=payload.links,
        message_id=payload.message_id,
    )
    store = VectorStore(settings.vector_store_path)
    doc_id = store.store_summary(summary)
    return {"id": doc_id, "status": "stored"}


@router.post("/daily-digest")
def daily_digest() -> dict[str, Any]:
    return run_daily_digest()


@router.post("/ask")
def ask(payload: AskRequest) -> dict[str, Any]:
    if not payload.question.strip():
        raise HTTPException(status_code=400, detail="question is required")
    result = answer_question(payload.question)
    return {"answer": result}
