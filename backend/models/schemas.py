"""
Pydantic 数据模型
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


# ========== 行业管理 ==========

class IndustryCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="行业名称")
    description: str = Field(default="", description="行业描述")


class IndustryUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=100, description="行业名称")
    description: Optional[str] = Field(default=None, description="行业描述")
    chunk_size: Optional[int] = Field(default=None, ge=50, le=2000, description="切片大小（字符数）")
    chunk_overlap: Optional[int] = Field(default=None, ge=0, le=500, description="切片重叠大小（字符数）")


class IndustryResponse(BaseModel):
    id: str
    name: str
    slug: str
    description: str
    doc_count: int
    chunk_count: int
    chunk_size: int
    chunk_overlap: int
    created_at: str
    updated_at: str


# ========== 知识管理 ==========

class KnowledgeTextInsert(BaseModel):
    title: str = Field(default="", description="文档标题")
    content: str = Field(..., min_length=1, description="文本内容")
    tags: list[str] = Field(default_factory=list, description="标签列表")


class KnowledgeTextResponse(BaseModel):
    doc_id: str
    chunk_count: int
    message: str = "知识录入成功"


class KnowledgeDocument(BaseModel):
    id: str
    title: str
    source: str
    chunk_count: int
    tags: list[str]
    created_at: str


class KnowledgeListResponse(BaseModel):
    items: list[KnowledgeDocument]
    total: int
    page: int
    page_size: int


# ========== 对话管理 ==========

class ChatMessage(BaseModel):
    role: str = Field(..., description="user / assistant")
    content: str


class ChatRequest(BaseModel):
    query: str = Field(..., min_length=1, description="用户问题")
    history: list[ChatMessage] = Field(default_factory=list, description="对话历史")
    industry: Optional[str] = Field(default=None, description="手动指定行业 slug（可选）")
    session_id: Optional[str] = Field(default=None, description="会话 ID")


class RouteRequest(BaseModel):
    query: str = Field(..., min_length=1, description="用户问题")


class RouteResponse(BaseModel):
    industry: str
    slug: str
    confidence: str


class ChatSession(BaseModel):
    id: str
    title: str
    industry: Optional[str]
    industry_name: Optional[str]
    message_count: int
    created_at: str
    updated_at: str


# ========== 系统配置 ==========

class SettingsUpdate(BaseModel):
    llm_model: Optional[str] = Field(default=None, description="LLM 模型")
    embedding_model: Optional[str] = Field(default=None, description="Embedding 模型")
    api_key: Optional[str] = Field(default=None, description="DashScope API Key")


class SettingsResponse(BaseModel):
    llm_model: str
    embedding_model: str
    api_key_configured: bool


class ModelInfo(BaseModel):
    id: str
    name: str
    description: str
    dimension: Optional[int] = None


class ModelsResponse(BaseModel):
    llm_models: list[ModelInfo]
    embedding_models: list[ModelInfo]


# ========== 通用响应 ==========

class ApiResponse(BaseModel):
    code: int = 0
    data: dict | list | None = None
    message: str = "success"