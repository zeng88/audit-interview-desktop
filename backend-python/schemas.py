from typing import Any, Literal

from pydantic import BaseModel, Field


class ProjectCreate(BaseModel):
    project_name: str
    company_name: str = ""
    industry: str = ""
    audit_objective: str = ""
    audit_period: str = ""
    focus_areas: str = ""


class ProjectUpdate(ProjectCreate):
    pass


class ModelConfigIn(BaseModel):
    config_name: str
    config_type: Literal["chat", "embedding"]
    provider: str = "openai-compatible"
    base_url: str = ""
    api_key: str = ""
    model: str
    temperature: float = 0.2
    max_tokens: int = 4096
    embedding_dimension: int | None = None
    embedding_batch_size: int = 16
    timeout_seconds: int = 120
    is_default: int = 0


class LocalQuestionTemplate(BaseModel):
    interview_role: str
    question_template: str
    keywords: list[str] = Field(default_factory=list)


class LocalTemplateSettingsIn(BaseModel):
    default_modules: list[str] = Field(default_factory=list)
    question_templates: list[LocalQuestionTemplate] = Field(default_factory=list)


class ChunkRequest(BaseModel):
    chunk_size: int = Field(default=800, ge=100, le=3000)
    overlap: int = Field(default=120, ge=0, le=1000)


class BuildVectorRequest(BaseModel):
    embedding_model_config_id: int
    batch_size: int = Field(default=16, ge=1, le=128)


class SearchRequest(BaseModel):
    query: str
    embedding_model_config_id: int | None = None
    top_k: int = Field(default=10, ge=1, le=50)


class GenerateChecklistRequest(BaseModel):
    chat_model_config_id: int | None = None
    embedding_model_config_id: int | None = None
    question_count: int = Field(default=20, ge=1, le=100)
    modules: list[str] = Field(default_factory=list)


class ExportRequest(BaseModel):
    format: Literal["xlsx", "docx", "json"]


class ChecklistUpdate(BaseModel):
    module: str | None = None
    interview_role: str | None = None
    interview_question: str | None = None
    expected_answer: str | None = None
    follow_up_question: str | None = None
    risk_hint: str | None = None


class ApiResult(BaseModel):
    ok: bool = True
    data: Any | None = None
    message: str = ""
