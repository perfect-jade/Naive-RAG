"""
行业业务逻辑
"""
import json
import uuid
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

from backend.config import INDUSTRIES_DIR, CHUNK_SIZE, CHUNK_OVERLAP


def _get_industry_dir(slug: str) -> Path:
    return INDUSTRIES_DIR / slug


def _get_meta_path(slug: str) -> Path:
    return _get_industry_dir(slug) / "meta.json"


def _get_metadata_db_path(slug: str) -> Path:
    return _get_industry_dir(slug) / "metadata.db"


def _init_metadata_db(slug: str):
    db_path = _get_metadata_db_path(slug)
    conn = sqlite3.connect(str(db_path))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id TEXT PRIMARY KEY,
            title TEXT DEFAULT '',
            source TEXT DEFAULT 'text',
            chunk_count INTEGER DEFAULT 0,
            tags TEXT DEFAULT '[]',
            created_at TEXT DEFAULT ''
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS chunks (
            id TEXT PRIMARY KEY,
            doc_id TEXT,
            content TEXT,
            chunk_index INTEGER,
            created_at TEXT DEFAULT '',
            FOREIGN KEY (doc_id) REFERENCES documents(id)
        )
    """)
    conn.commit()
    conn.close()


def _slugify(name: str) -> str:
    """中文名转拼音 slug"""
    import re
    import unicodedata

    slug = name.strip()
    slug = unicodedata.normalize('NFKD', slug)
    slug = slug.encode('ascii', 'ignore').decode('ascii')

    # 如果全是中文字符，使用拼音方案
    if not slug:
        import hashlib
        slug = hashlib.md5(name.encode()).hexdigest()[:8]

    slug = re.sub(r'[^\w\s-]', '', slug.lower())
    slug = re.sub(r'[\s]+', '_', slug)
    slug = slug.strip('_')
    return slug if slug else f"industry_{uuid.uuid4().hex[:8]}"


def create_industry(name: str, description: str = "") -> dict:
    """创建行业"""
    slug = _slugify(name)
    industry_dir = _get_industry_dir(slug)

    if industry_dir.exists():
        raise ValueError(f"行业 '{name}' 已存在")

    industry_dir.mkdir(parents=True, exist_ok=True)
    (industry_dir / "faiss_index").mkdir(exist_ok=True)
    (industry_dir / "bm25_index").mkdir(exist_ok=True)
    (industry_dir / "raw_docs").mkdir(exist_ok=True)

    _init_metadata_db(slug)

    meta = {
        "id": uuid.uuid4().hex[:12],
        "name": name,
        "slug": slug,
        "description": description,
        "doc_count": 0,
        "chunk_count": 0,
        "chunk_size": CHUNK_SIZE,
        "chunk_overlap": CHUNK_OVERLAP,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    }

    with open(_get_meta_path(slug), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False)

    return meta


def list_industries() -> list[dict]:
    """获取所有行业列表"""
    industries = []
    if not INDUSTRIES_DIR.exists():
        return industries

    for d in sorted(INDUSTRIES_DIR.iterdir(), key=lambda x: x.name):
        if not d.is_dir():
            continue
        meta_path = d / "meta.json"
        if meta_path.exists():
            with open(meta_path, "r", encoding="utf-8") as f:
                industries.append(json.load(f))

    return sorted(industries, key=lambda x: x.get("created_at", ""), reverse=True)


def get_industry(slug: str) -> Optional[dict]:
    """获取行业详情"""
    meta_path = _get_meta_path(slug)
    if not meta_path.exists():
        return None
    with open(meta_path, "r", encoding="utf-8") as f:
        return json.load(f)


def update_industry(slug: str, name: Optional[str] = None, description: Optional[str] = None,
                    chunk_size: Optional[int] = None, chunk_overlap: Optional[int] = None) -> Optional[dict]:
    """更新行业信息"""
    industry = get_industry(slug)
    if not industry:
        return None

    new_slug = slug
    if name is not None:
        new_slug = _slugify(name)
        if new_slug != slug:
            old_dir = _get_industry_dir(slug)
            new_dir = _get_industry_dir(new_slug)
            if new_dir.exists():
                raise ValueError(f"行业名称 '{name}' 对应的 slug 已存在")
            old_dir.rename(new_dir)

    if description is not None:
        industry["description"] = description
    if name is not None:
        industry["name"] = name
        industry["slug"] = new_slug
    if chunk_size is not None:
        industry["chunk_size"] = chunk_size
    if chunk_overlap is not None:
        industry["chunk_overlap"] = chunk_overlap

    industry["updated_at"] = datetime.now().isoformat()

    with open(_get_meta_path(new_slug), "w", encoding="utf-8") as f:
        json.dump(industry, f, ensure_ascii=False)

    return industry


def get_chunk_config(slug: str) -> dict:
    """获取行业的分片配置"""
    industry = get_industry(slug)
    if not industry:
        return {"chunk_size": CHUNK_SIZE, "chunk_overlap": CHUNK_OVERLAP}
    
    return {
        "chunk_size": industry.get("chunk_size", CHUNK_SIZE),
        "chunk_overlap": industry.get("chunk_overlap", CHUNK_OVERLAP),
    }


def delete_industry(slug: str) -> bool:
    """删除行业"""
    industry = get_industry(slug)
    if not industry:
        return False

    industry_dir = _get_industry_dir(slug)
    if industry_dir.exists():
        shutil.rmtree(industry_dir, ignore_errors=True)

    return True


def _get_db(slug: str) -> sqlite3.Connection:
    return sqlite3.connect(str(_get_metadata_db_path(slug)))


def add_document(slug: str, doc_id: str, title: str, source: str,
                 chunk_count: int, tags: list[str]) -> dict:
    """添加文档记录"""
    conn = _get_db(slug)
    now = datetime.now().isoformat()
    conn.execute(
        "INSERT INTO documents (id, title, source, chunk_count, tags, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (doc_id, title, source, chunk_count, json.dumps(tags, ensure_ascii=False), now)
    )
    conn.commit()
    conn.close()

    _update_meta_counts(slug)
    return {"id": doc_id, "title": title, "chunk_count": chunk_count, "created_at": now}


def add_chunks(slug: str, chunks: list[dict]):
    """批量添加 chunk 记录"""
    conn = _get_db(slug)
    now = datetime.now().isoformat()
    for chunk in chunks:
        conn.execute(
            "INSERT INTO chunks (id, doc_id, content, chunk_index, created_at) VALUES (?, ?, ?, ?, ?)",
            (chunk["id"], chunk["doc_id"], chunk["content"], chunk["chunk_index"], now)
        )
    conn.commit()
    conn.close()


def list_documents(slug: str, page: int = 1, page_size: int = 10) -> dict:
    """分页获取文档列表"""
    conn = _get_db(slug)
    offset = (page - 1) * page_size
    total = conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
    rows = conn.execute(
        "SELECT id, title, source, chunk_count, tags, created_at FROM documents ORDER BY created_at DESC LIMIT ? OFFSET ?",
        (page_size, offset)
    ).fetchall()
    conn.close()

    items = []
    for row in rows:
        try:
            tags = json.loads(row[4])
        except (json.JSONDecodeError, TypeError):
            tags = []
        items.append({
            "id": row[0], "title": row[1], "source": row[2],
            "chunk_count": row[3], "tags": tags, "created_at": row[5]
        })

    return {"items": items, "total": total, "page": page, "page_size": page_size}


def get_document(slug: str, doc_id: str) -> Optional[dict]:
    """获取文档详情"""
    conn = _get_db(slug)
    row = conn.execute(
        "SELECT id, title, source, chunk_count, tags, created_at FROM documents WHERE id = ?",
        (doc_id,)
    ).fetchone()
    conn.close()

    if not row:
        return None
    try:
        tags = json.loads(row[4])
    except (json.JSONDecodeError, TypeError):
        tags = []
    return {"id": row[0], "title": row[1], "source": row[2],
            "chunk_count": row[3], "tags": tags, "created_at": row[5]}


def get_document_chunks(slug: str, doc_id: str) -> list[dict]:
    """获取文档的所有 chunks"""
    conn = _get_db(slug)
    rows = conn.execute(
        "SELECT id, doc_id, content, chunk_index FROM chunks WHERE doc_id = ? ORDER BY chunk_index",
        (doc_id,)
    ).fetchall()
    conn.close()
    return [{"id": r[0], "doc_id": r[1], "content": r[2], "chunk_index": r[3]} for r in rows]


def delete_document(slug: str, doc_id: str) -> bool:
    """删除文档及其 chunks"""
    doc = get_document(slug, doc_id)
    if not doc:
        return False

    conn = _get_db(slug)
    conn.execute("DELETE FROM chunks WHERE doc_id = ?", (doc_id,))
    conn.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
    conn.commit()
    conn.close()

    _update_meta_counts(slug)
    return True


def _update_meta_counts(slug: str):
    """更新行业元数据中的文档和 chunk 计数"""
    industry = get_industry(slug)
    if not industry:
        return

    conn = _get_db(slug)
    doc_count = conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
    chunk_count = conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
    conn.close()

    industry["doc_count"] = doc_count
    industry["chunk_count"] = chunk_count
    industry["updated_at"] = datetime.now().isoformat()

    with open(_get_meta_path(slug), "w", encoding="utf-8") as f:
        json.dump(industry, f, ensure_ascii=False)