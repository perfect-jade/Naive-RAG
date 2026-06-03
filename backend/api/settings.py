"""
系统配置 API 接口
"""
from fastapi import APIRouter, HTTPException

from backend.config import (
    get_config, set_config, get_llm_model, get_embedding_model,
    VALID_LLM_MODELS, VALID_EMBEDDING_MODELS, EMBEDDING_DIMENSIONS,
    DEFAULT_LLM_MODEL, DEFAULT_EMBEDDING_MODEL,
)
from backend.models.schemas import SettingsUpdate

router = APIRouter(prefix="/api/v1", tags=["settings"])


@router.get("/health")
def health_check():
    """健康检查"""
    return {"status": "ok", "code": 0}


@router.get("/settings")
def get_settings():
    """获取当前系统配置"""
    llm_model = get_config("llm_model") or DEFAULT_LLM_MODEL
    embedding_model = get_config("embedding_model") or DEFAULT_EMBEDDING_MODEL
    api_key = get_config("api_key") or ""
    return {
        "code": 0,
        "data": {
            "llm_model": llm_model,
            "embedding_model": embedding_model,
            "api_key_configured": bool(api_key),
        },
        "message": "success",
    }


@router.put("/settings")
def update_settings(body: SettingsUpdate):
    """更新系统配置"""
    if not any([body.llm_model, body.embedding_model, body.api_key]):
        raise HTTPException(status_code=422, detail={"code": 1, "message": "请求体不能为空"})

    embedding_changed = False

    if body.llm_model is not None:
        if body.llm_model not in VALID_LLM_MODELS:
            raise HTTPException(status_code=400, detail={
                "code": 1,
                "message": f"无效的 LLM 模型: {body.llm_model}，可选: {', '.join(VALID_LLM_MODELS)}"
            })
        set_config("llm_model", body.llm_model)

    if body.embedding_model is not None:
        if body.embedding_model not in VALID_EMBEDDING_MODELS:
            raise HTTPException(status_code=400, detail={
                "code": 1,
                "message": f"无效的 Embedding 模型: {body.embedding_model}，可选: {', '.join(VALID_EMBEDDING_MODELS)}"
            })
        old_model = get_config("embedding_model") or DEFAULT_EMBEDDING_MODEL
        if body.embedding_model != old_model:
            embedding_changed = True
        set_config("embedding_model", body.embedding_model)

    if body.api_key is not None:
        set_config("api_key", body.api_key)

    response = {"message": "配置已更新", "embedding_changed": embedding_changed}
    if embedding_changed:
        response["warning"] = (
            "切换 Embedding 模型后，已有的知识库向量将无法使用，"
            "建议重新录入知识或备份后清空重来"
        )

    return {"code": 0, "data": response, "message": "success"}


@router.get("/settings/models")
def get_available_models():
    """获取可用模型列表"""
    return {
        "code": 0,
        "data": {
            "llm_models": [
                {"id": "qwen-turbo", "name": "qwen-turbo", "description": "速度快，适合简单任务"},
                {"id": "qwen-plus", "name": "qwen-plus", "description": "能力均衡，适合大多数场景"},
                {"id": "qwen-max", "name": "qwen-max", "description": "能力最强，适合复杂推理"},
                {"id": "qwen-long", "name": "qwen-long", "description": "超长上下文，适合长文档处理"},
            ],
            "embedding_models": [
                {"id": "text-embedding-v1", "name": "text-embedding-v1", "description": "基础版本", "dimension": EMBEDDING_DIMENSIONS["text-embedding-v1"]},
                {"id": "text-embedding-v2", "name": "text-embedding-v2", "description": "推荐版本，效果更好", "dimension": EMBEDDING_DIMENSIONS["text-embedding-v2"]},
                {"id": "text-embedding-v3", "name": "text-embedding-v3", "description": "最新版本，维度更小、效率更高", "dimension": EMBEDDING_DIMENSIONS["text-embedding-v3"]},
            ],
        },
        "message": "success",
    }