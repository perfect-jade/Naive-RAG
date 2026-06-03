"""
知识管理 API 接口
"""
import os
import shutil
from pathlib import Path
from fastapi import APIRouter, HTTPException, UploadFile, File, Form

from backend.models.schemas import KnowledgeTextInsert
from backend.services import industry_service, knowledge_service, file_parser
from backend.config import MAX_FILE_SIZE_MB

router = APIRouter(prefix="/api/v1/industries", tags=["knowledge"])


@router.post("/{slug}/knowledge/text")
def insert_text_knowledge(slug: str, body: KnowledgeTextInsert):
    """文本录入"""
    try:
        result = knowledge_service.insert_text_knowledge(
            slug, body.content, body.title, body.tags
        )
        return {"code": 0, "data": result, "message": "success"}
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail={"code": 1, "message": str(e)})
    except ValueError as e:
        raise HTTPException(status_code=422, detail={"code": 1, "message": str(e)})


@router.post("/{slug}/knowledge/upload")
async def upload_files(slug: str, files: list[UploadFile] = File(...)):
    """上传文件"""
    if not industry_service.get_industry(slug):
        raise HTTPException(status_code=404, detail={"code": 1, "message": f"行业 '{slug}' 不存在"})

    if not files:
        raise HTTPException(status_code=422, detail={"code": 1, "message": "请上传至少一个文件"})

    max_size = MAX_FILE_SIZE_MB * 1024 * 1024
    industry_dir = industry_service._get_industry_dir(slug)
    raw_docs_dir = industry_dir / "raw_docs"
    raw_docs_dir.mkdir(parents=True, exist_ok=True)

    results = []
    for file in files:
        file_result = {
            "filename": file.filename,
            "status": "success",
            "chunk_count": 0,
            "stages": [],
        }

        try:
            ext = Path(file.filename).suffix.lower()
            if ext not in file_parser.SUPPORTED_EXTENSIONS:
                file_result["status"] = "error"
                file_result["error"] = f"不支持的文件类型: {ext}"
                results.append(file_result)
                continue

            # 阶段1: 读取文件
            file_result["stages"].append({"stage": "read", "status": "success"})
            content = await file.read()
            if len(content) > max_size:
                file_result["status"] = "error"
                file_result["error"] = f"文件大小超过限制 ({MAX_FILE_SIZE_MB}MB)"
                results.append(file_result)
                continue

            # 阶段2: 保存文件
            file_result["stages"].append({"stage": "save", "status": "success"})
            temp_path = raw_docs_dir / file.filename
            with open(temp_path, "wb") as f:
                f.write(content)

            # 阶段3: 解析文件
            file_result["stages"].append({"stage": "parse", "status": "processing"})
            text = file_parser.parse_file(temp_path)
            if not text or not text.strip():
                file_result["status"] = "error"
                file_result["error"] = "文件解析失败，内容为空"
                results.append(file_result)
                continue
            file_result["stages"].append({"stage": "parse", "status": "success"})
            title = file_parser.get_file_title(temp_path)

            # 阶段4: 分块和入库
            file_result["stages"].append({"stage": "chunk", "status": "processing"})
            result = knowledge_service.insert_text_knowledge(
                slug, text, title, []
            )
            file_result["stages"].append({"stage": "chunk", "status": "success"})
            file_result["chunk_count"] = result["chunk_count"]
            file_result["doc_id"] = result["doc_id"]

        except Exception as e:
            file_result["status"] = "error"
            file_result["error"] = str(e)

        results.append(file_result)

    return {"code": 0, "data": {"results": results}, "message": "success"}


@router.get("/{slug}/knowledge")
def list_knowledge(slug: str, page: int = 1, page_size: int = 10):
    """获取知识列表"""
    if not industry_service.get_industry(slug):
        raise HTTPException(status_code=404, detail={"code": 1, "message": f"行业 '{slug}' 不存在"})

    result = industry_service.list_documents(slug, page, page_size)
    return {"code": 0, "data": result, "message": "success"}


@router.delete("/{slug}/knowledge/{doc_id}")
def delete_knowledge(slug: str, doc_id: str):
    """删除知识文档"""
    try:
        ok = knowledge_service.remove_knowledge(slug, doc_id)
        if not ok:
            raise HTTPException(status_code=404, detail={"code": 1, "message": f"文档 '{doc_id}' 不存在"})
        return {"code": 0, "data": None, "message": "success"}
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail={"code": 1, "message": str(e)})


@router.get("/{slug}/knowledge/{doc_id}/chunks")
def get_document_chunks(slug: str, doc_id: str):
    """获取文档的所有切片"""
    if not industry_service.get_industry(slug):
        raise HTTPException(status_code=404, detail={"code": 1, "message": f"行业 '{slug}' 不存在"})
    
    doc = industry_service.get_document(slug, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail={"code": 1, "message": f"文档 '{doc_id}' 不存在"})
    
    chunks = industry_service.get_document_chunks(slug, doc_id)
    return {"code": 0, "data": chunks, "message": "success"}


@router.delete("/{slug}/knowledge/{doc_id}/chunks/{chunk_id}")
def delete_chunk(slug: str, doc_id: str, chunk_id: str):
    """删除单个切片"""
    if not industry_service.get_industry(slug):
        raise HTTPException(status_code=404, detail={"code": 1, "message": f"行业 '{slug}' 不存在"})
    
    doc = industry_service.get_document(slug, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail={"code": 1, "message": f"文档 '{doc_id}' 不存在"})
    
    try:
        knowledge_service.remove_chunk(slug, doc_id, chunk_id)
        return {"code": 0, "data": None, "message": "success"}
    except ValueError as e:
        raise HTTPException(status_code=422, detail={"code": 1, "message": str(e)})