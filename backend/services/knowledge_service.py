"""
知识业务逻辑 - 分块、入库
"""
import uuid
import logging
import sqlite3
from pathlib import Path
from typing import Union

from langchain_text_splitters import RecursiveCharacterTextSplitter

from backend.config import CHUNK_SIZE, CHUNK_OVERLAP
from backend.core.embedding import get_embeddings
from backend.core.faiss_engine import FAISSEngine
from backend.core.bm25_engine import BM25Engine
from backend.services.industry_service import (
    add_document, add_chunks, list_documents, get_document,
    delete_document, get_industry, _get_industry_dir, get_chunk_config,
)

_log = logging.getLogger(__name__)


def split_text(text: str, chunk_size: int = CHUNK_SIZE, chunk_overlap: int = CHUNK_OVERLAP) -> list[str]:
    """文本分块"""
    if not text or not text.strip():
        return []

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", "。", "！", "？", "，", " ", ""],
    )
    return splitter.split_text(text)


def _get_engines(slug: str):
    """获取行业的检索引擎"""
    industry_dir = _get_industry_dir(slug)
    faiss = FAISSEngine(industry_dir / "faiss_index")
    bm25 = BM25Engine(industry_dir / "bm25_index")
    return faiss, bm25


def insert_text_knowledge(slug: str, content: str, title: str = "",
                          tags: list[str] | None = None) -> dict:
    """录入文本知识"""
    if not get_industry(slug):
        raise FileNotFoundError(f"行业 '{slug}' 不存在")

    if not content or not content.strip():
        raise ValueError("内容不能为空")

    tags = tags or []
    doc_id = uuid.uuid4().hex[:12]
    
    # 获取行业级分片配置
    chunk_config = get_chunk_config(slug)
    chunks = split_text(content, chunk_config["chunk_size"], chunk_config["chunk_overlap"])

    if not chunks:
        raise ValueError("文本内容无法分块")

    faiss, bm25 = _get_engines(slug)

    chunk_records = []
    chunk_ids = []
    bm25_chunks = []

    for i, chunk_text in enumerate(chunks):
        chunk_id = f"{doc_id}_chunk_{i}"
        chunk_ids.append(chunk_id)
        chunk_records.append({
            "id": chunk_id,
            "doc_id": doc_id,
            "content": chunk_text,
            "chunk_index": i,
        })
        bm25_chunks.append({
            "chunk_id": chunk_id,
            "doc_id": doc_id,
            "content": chunk_text,
        })

    # 生成 Embedding 并写入 FAISS
    embeddings = get_embeddings([c["content"] for c in chunk_records])
    faiss.add(embeddings, chunk_ids)

    # 写入 BM25
    bm25.add(bm25_chunks)

    # 写入数据库
    add_document(slug, doc_id, title, "text", len(chunks), tags)
    add_chunks(slug, chunk_records)

    return {"doc_id": doc_id, "chunk_count": len(chunks), "message": "知识录入成功"}


def remove_knowledge(slug: str, doc_id: str) -> bool:
    """删除知识文档"""
    if not get_industry(slug):
        raise FileNotFoundError(f"行业 '{slug}' 不存在")

    doc = get_document(slug, doc_id)
    if not doc:
        raise FileNotFoundError(f"文档 '{doc_id}' 不存在")

    faiss, bm25 = _get_engines(slug)
    chunk_ids = [f"{doc_id}_chunk_{i}" for i in range(doc["chunk_count"] + 10)]
    faiss.remove_by_ids(chunk_ids)
    bm25.remove_by_doc_ids([doc_id])

    return delete_document(slug, doc_id)


def remove_chunk(slug: str, doc_id: str, chunk_id: str) -> bool:
    """删除单个切片"""
    if not get_industry(slug):
        raise FileNotFoundError(f"行业 '{slug}' 不存在")

    doc = get_document(slug, doc_id)
    if not doc:
        raise FileNotFoundError(f"文档 '{doc_id}' 不存在")

    # 验证 chunk_id 是否属于该文档
    if not chunk_id.startswith(f"{doc_id}_chunk_"):
        raise ValueError(f"切片 '{chunk_id}' 不属于文档 '{doc_id}'")

    faiss, bm25 = _get_engines(slug)
    faiss.remove_by_ids([chunk_id])
    bm25.remove_by_ids([chunk_id])

    from backend.services.industry_service import _get_db
    conn = _get_db(slug)
    conn.execute("DELETE FROM chunks WHERE id = ?", (chunk_id,))
    conn.execute("UPDATE documents SET chunk_count = chunk_count - 1 WHERE id = ?", (doc_id,))
    conn.commit()
    conn.close()

    _update_meta_counts(slug)
    return True


def _update_meta_counts(slug: str):
    """更新行业元数据中的文档和 chunk 计数"""
    from backend.services.industry_service import get_industry, _get_meta_path, _get_db
    import json

    industry = get_industry(slug)
    if not industry:
        return

    conn = _get_db(slug)
    doc_count = conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
    chunk_count = conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
    conn.close()

    industry["doc_count"] = doc_count
    industry["chunk_count"] = chunk_count
    
    from datetime import datetime
    industry["updated_at"] = datetime.now().isoformat()

    with open(_get_meta_path(slug), "w", encoding="utf-8") as f:
        json.dump(industry, f, ensure_ascii=False)