"""
行业管理 API 接口
"""
from fastapi import APIRouter, HTTPException
from backend.models.schemas import IndustryCreate, IndustryUpdate, IndustryResponse
from backend.services import industry_service as service

router = APIRouter(prefix="/api/v1/industries", tags=["industry"])


@router.post("", status_code=201)
def create_industry(body: IndustryCreate):
    """创建行业"""
    try:
        result = service.create_industry(body.name, body.description)
        return {"code": 0, "data": result, "message": "success"}
    except ValueError as e:
        raise HTTPException(status_code=409, detail={"code": 1, "message": str(e)})


@router.get("")
def list_industries():
    """获取行业列表"""
    items = service.list_industries()
    return {"code": 0, "data": items, "message": "success"}


@router.get("/{slug}")
def get_industry_detail(slug: str):
    """获取行业详情"""
    item = service.get_industry(slug)
    if not item:
        raise HTTPException(status_code=404, detail={"code": 1, "message": f"行业 '{slug}' 不存在"})
    return {"code": 0, "data": item, "message": "success"}


@router.put("/{slug}")
def update_industry(slug: str, body: IndustryUpdate):
    """更新行业信息"""
    try:
        result = service.update_industry(
            slug,
            name=body.name,
            description=body.description,
            chunk_size=body.chunk_size,
            chunk_overlap=body.chunk_overlap,
        )
        if not result:
            raise HTTPException(status_code=404, detail={"code": 1, "message": f"行业 '{slug}' 不存在"})
        return {"code": 0, "data": result, "message": "success"}
    except ValueError as e:
        raise HTTPException(status_code=409, detail={"code": 1, "message": str(e)})


@router.get("/{slug}/chunk-config")
def get_chunk_config(slug: str):
    """获取行业的分片配置"""
    config = service.get_chunk_config(slug)
    return {"code": 0, "data": config, "message": "success"}


@router.delete("/{slug}")
def delete_industry(slug: str):
    """删除行业"""
    ok = service.delete_industry(slug)
    if not ok:
        raise HTTPException(status_code=404, detail={"code": 1, "message": f"行业 '{slug}' 不存在"})
    return {"code": 0, "data": None, "message": "success"}