"""Admin Configuration API — prompt templates + alert thresholds."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

import app.config_store as store

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


# --- Thresholds ---

class Thresholds(BaseModel):
    failure_rate_warning:           float = Field(ge=0, le=1)
    failure_rate_critical:          float = Field(ge=0, le=1)
    processing_time_warning_s:      int   = Field(ge=0)
    processing_time_critical_s:     int   = Field(ge=0)
    min_transaction_volume_per_day: int   = Field(ge=0)


@router.get("/thresholds", response_model=Thresholds)
async def get_thresholds() -> Thresholds:
    return Thresholds(**store.get_thresholds())


@router.put("/thresholds", response_model=Thresholds)
async def update_thresholds(body: Thresholds) -> Thresholds:
    updated = store.update_thresholds(body.model_dump())
    return Thresholds(**updated)


# --- Prompt templates ---

class PromptTemplate(BaseModel):
    id: str
    name: str
    description: str
    template: str
    updated_at: str


class CreateTemplateRequest(BaseModel):
    name: str        = Field(min_length=1, max_length=100)
    description: str = Field(default="")
    template: str    = Field(min_length=1)


class UpdateTemplateRequest(BaseModel):
    name: str | None        = Field(default=None, max_length=100)
    description: str | None = None
    template: str | None    = None


@router.get("/prompts", response_model=list[PromptTemplate])
async def list_prompts() -> list[PromptTemplate]:
    return [PromptTemplate(**t) for t in store.list_templates()]


@router.post("/prompts", response_model=PromptTemplate, status_code=201)
async def create_prompt(body: CreateTemplateRequest) -> PromptTemplate:
    tpl = store.create_template(body.name, body.description, body.template)
    return PromptTemplate(**tpl)


@router.put("/prompts/{template_id}", response_model=PromptTemplate)
async def update_prompt(template_id: str, body: UpdateTemplateRequest) -> PromptTemplate:
    tpl = store.update_template(template_id, **body.model_dump(exclude_none=True))
    if tpl is None:
        raise HTTPException(status_code=404, detail="Template not found")
    return PromptTemplate(**tpl)


@router.delete("/prompts/{template_id}", status_code=204)
async def delete_prompt(template_id: str) -> None:
    if not store.delete_template(template_id):
        raise HTTPException(status_code=404, detail="Template not found")
