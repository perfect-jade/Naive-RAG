"""
对话业务逻辑
"""
import json
import uuid
import sqlite3
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Generator

from backend.config import DATA_DIR, MAX_CHAT_HISTORY_ROUNDS, get_llm_model
from backend.core.llm_client import chat_completion, route_industry as llm_route_industry
from backend.core.router import route_to_industry
from backend.core.retriever import HybridRetriever
from backend.core.faiss_engine import FAISSEngine
from backend.core.bm25_engine import BM25Engine
from backend.core.web_search import web_search
from backend.services.industry_service import (
    get_industry, list_industries, get_document_chunks,
    _get_industry_dir,
)

_log = logging.getLogger(__name__)

CHAT_DB_PATH = DATA_DIR / "chat.db"


def _get_chat_db() -> sqlite3.Connection:
    CHAT_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(CHAT_DB_PATH))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            title TEXT DEFAULT '',
            industry TEXT DEFAULT '',
            industry_name TEXT DEFAULT '',
            created_at TEXT DEFAULT '',
            updated_at TEXT DEFAULT ''
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id TEXT PRIMARY KEY,
            session_id TEXT,
            role TEXT,
            content TEXT,
            created_at TEXT DEFAULT '',
            FOREIGN KEY (session_id) REFERENCES sessions(id)
        )
    """)
    conn.commit()
    return conn


def create_session(industry: str = "", industry_name: str = "") -> dict:
    """创建会话"""
    conn = _get_chat_db()
    session_id = uuid.uuid4().hex[:12]
    now = datetime.now().isoformat()
    conn.execute(
        "INSERT INTO sessions (id, title, industry, industry_name, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
        (session_id, "", industry, industry_name, now, now)
    )
    conn.commit()
    conn.close()
    return {"id": session_id, "title": "", "industry": industry, "industry_name": industry_name,
            "message_count": 0, "created_at": now, "updated_at": now}


def get_session(session_id: str) -> Optional[dict]:
    """获取会话"""
    conn = _get_chat_db()
    row = conn.execute(
        "SELECT id, title, industry, industry_name, created_at, updated_at FROM sessions WHERE id = ?",
        (session_id,)
    ).fetchone()
    if not row:
        conn.close()
        return None
    msg_count = conn.execute(
        "SELECT COUNT(*) FROM messages WHERE session_id = ?", (session_id,)
    ).fetchone()[0]
    conn.close()
    return {"id": row[0], "title": row[1], "industry": row[2], "industry_name": row[3],
            "message_count": msg_count, "created_at": row[4], "updated_at": row[5]}


def add_message(session_id: str, role: str, content: str):
    """添加消息"""
    conn = _get_chat_db()
    msg_id = uuid.uuid4().hex[:12]
    now = datetime.now().isoformat()
    conn.execute(
        "INSERT INTO messages (id, session_id, role, content, created_at) VALUES (?, ?, ?, ?, ?)",
        (msg_id, session_id, role, content, now)
    )
    conn.execute(
        "UPDATE sessions SET updated_at = ? WHERE id = ?",
        (now, session_id)
    )
    conn.commit()
    conn.close()


def get_session_messages(session_id: str, limit: int = MAX_CHAT_HISTORY_ROUNDS * 2) -> list[dict]:
    """获取会话消息"""
    conn = _get_chat_db()
    rows = conn.execute(
        "SELECT role, content FROM messages WHERE session_id = ? ORDER BY created_at DESC LIMIT ?",
        (session_id, limit)
    ).fetchall()
    conn.close()
    return [{"role": r[0], "content": r[1]} for r in reversed(rows)]


def list_sessions() -> list[dict]:
    """获取所有会话列表"""
    conn = _get_chat_db()
    rows = conn.execute(
        "SELECT id, title, industry, industry_name, created_at, updated_at FROM sessions ORDER BY updated_at DESC"
    ).fetchall()
    sessions = []
    for row in rows:
        msg_count = conn.execute(
            "SELECT COUNT(*) FROM messages WHERE session_id = ?", (row[0],)
        ).fetchone()[0]
        sessions.append({
            "id": row[0], "title": row[1], "industry": row[2], "industry_name": row[3],
            "message_count": msg_count, "created_at": row[4], "updated_at": row[5]
        })
    conn.close()
    return sessions


def delete_session(session_id: str) -> bool:
    """删除会话"""
    conn = _get_chat_db()
    conn.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
    conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
    conn.commit()
    conn.close()
    return True


def _retrieve_from_industry(query: str, industry_slug: str) -> tuple[list[dict], list[dict]]:
    """
    从单个行业检索
    返回 (检索结果, 上下文 chunks)
    """
    industry_dir = _get_industry_dir(industry_slug)
    faiss = FAISSEngine(industry_dir / "faiss_index")
    bm25 = BM25Engine(industry_dir / "bm25_index")
    retriever = HybridRetriever(faiss, bm25)
    retrieval_results = retriever.retrieve(query)

    if not retrieval_results:
        return [], []

    context_chunks = []
    for r in retrieval_results:
        chunk_id = r["chunk_id"]
        parts = chunk_id.rsplit("_chunk_", 1)
        if len(parts) == 2:
            doc_id = parts[0]
            chunks = get_document_chunks(industry_slug, doc_id)
            for c in chunks:
                if c["id"] == chunk_id:
                    context_chunks.append(c)
                    break

    return retrieval_results, context_chunks


def stream_chat(
    query: str,
    history: list[dict] | None = None,
    industry_slug: str | None = None,
    session_id: str | None = None,
) -> Generator[str, None, None]:
    """
    SSE 流式对话
    检索策略：优先在路由行业检索 -> 多行业轮询检索 -> 网络搜索
    """
    import json as json_mod

    history = history or []

    # 1. 行业路由
    if industry_slug and get_industry(industry_slug):
        route_result = {
            "industry": get_industry(industry_slug)["name"],
            "slug": industry_slug,
            "confidence": "manual",
        }
    else:
        route_result = route_to_industry(query)
        industry_slug = route_result.get("slug")

    yield f"data: {json_mod.dumps({'type': 'route', 'data': route_result}, ensure_ascii=False)}\n\n"

    # 如果有 session_id，保存用户消息
    if session_id:
        add_message(session_id, "user", query)
        if route_result.get("slug") and route_result.get("slug") != "general":
            conn = _get_chat_db()
            conn.execute(
                "UPDATE sessions SET industry = ?, industry_name = ? WHERE id = ?",
                (route_result.get("slug"), route_result.get("industry", ""), session_id)
            )
            conn.commit()
            conn.close()

    # 2. 多行业轮询检索
    all_context_chunks = []
    all_retrieval_sources = []
    all_industries = list_industries()

    if all_industries:
        # 确定检索顺序：优先路由行业，然后是其他行业
        industry_order = []
        if industry_slug and industry_slug != "general":
            industry_order.append(industry_slug)
        for ind in all_industries:
            slug = ind.get("slug")
            if slug and slug != industry_slug:
                industry_order.append(slug)

        yield f"data: {json_mod.dumps({'type': 'retrieval', 'data': {'message': f'开始在 {len(industry_order)} 个行业中检索...'}}, ensure_ascii=False)}\n\n"

        for idx, slug in enumerate(industry_order):
            industry_name = next((ind["name"] for ind in all_industries if ind.get("slug") == slug), slug)
            yield f"data: {json_mod.dumps({'type': 'retrieval', 'data': {'message': f'正在检索 [{industry_name}] ({idx+1}/{len(industry_order)})...'}}, ensure_ascii=False)}\n\n"

            retrieval_results, context_chunks = _retrieve_from_industry(query, slug)

            if retrieval_results:
                yield f"data: {json_mod.dumps({'type': 'retrieval', 'data': {'message': f'在 [{industry_name}] 中找到 {len(retrieval_results)} 条相关内容'}}, ensure_ascii=False)}\n\n"
                for c in context_chunks:
                    c["industry_slug"] = slug
                    c["industry_name"] = industry_name
                all_context_chunks.extend(context_chunks)
                all_retrieval_sources.append({
                    "industry": industry_name,
                    "slug": slug,
                    "count": len(retrieval_results),
                })

            if len(all_context_chunks) >= 10:
                break

    # 3. 如果所有行业都检索不到，进行网络搜索
    if not all_context_chunks:
        yield f"data: {json_mod.dumps({'type': 'retrieval', 'data': {'message': '知识库中未找到相关内容，正在进行网络搜索...'}}, ensure_ascii=False)}\n\n"

        web_results = web_search(query)
        if web_results:
            for i, result in enumerate(web_results[:5]):
                all_context_chunks.append({
                    "id": f"web_{i}",
                    "content": f"【标题】{result.get('title', '')}\n【来源】{result.get('url', '')}\n【摘要】{result.get('snippet', '')}",
                    "industry_slug": "web",
                    "industry_name": "网络搜索",
                })
            yield f"data: {json_mod.dumps({'type': 'retrieval', 'data': {'message': f'网络搜索找到 {len(web_results)} 条相关内容'}}, ensure_ascii=False)}\n\n"
        else:
            yield f"data: {json_mod.dumps({'type': 'retrieval', 'data': {'message': '网络搜索也未找到相关内容'}}, ensure_ascii=False)}\n\n"

    # 4. 构建 Prompt 并生成回答
    context_text = "\n\n---\n\n".join([
        f"[参考资料 {i+1}] [来源: {c.get('industry_name', 'unknown')}]\n{c['content']}"
        for i, c in enumerate(all_context_chunks)
    ]) if all_context_chunks else "无相关参考资料"

    history_text = "\n".join([
        f"{'用户' if m['role'] == 'user' else '助手'}: {m['content']}"
        for m in history[-MAX_CHAT_HISTORY_ROUNDS * 2:]
    ]) if history else "无历史对话"

    system_prompt = (
        "你是一个专业的行业知识助手，请根据提供的参考资料回答用户问题。"
        "如果参考资料不足以回答问题，请如实告知用户无法回答，不要编造信息。"
        "回答时请注明引用的资料编号和来源。"
    )

    user_prompt = f"""## 参考资料
{context_text}

## 对话历史
{history_text}

## 用户问题
{query}

请基于以上参考资料回答问题。如果资料不足以回答，请明确说明。回答时请注明引用的资料编号和来源。"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    # 5. 流式调用 LLM
    try:
        response = chat_completion(messages, stream=True)
        full_answer = ""

        for chunk in response:
            if chunk and isinstance(chunk, dict) and 'output' in chunk:
                choices = chunk['output'].get('choices', [])
                if choices:
                    content = choices[0].get('message', {}).get('content', '')
                    finish_reason = choices[0].get('finish_reason', 'null')
                    if content:
                        full_answer += content
                        yield f"data: {json_mod.dumps({'type': 'token', 'data': content}, ensure_ascii=False)}\n\n"
                    if finish_reason == 'stop':
                        break

        yield f"data: {json_mod.dumps({'type': 'done', 'data': {'answer': full_answer, 'sources': [{'chunk_id': c['id'], 'content': c['content'][:100], 'source': c.get('industry_name', 'unknown')} for c in all_context_chunks[:5]], 'retrieval_sources': all_retrieval_sources}}, ensure_ascii=False)}\n\n"

        if session_id and full_answer:
            add_message(session_id, "assistant", full_answer)
            if full_answer:
                conn = _get_chat_db()
                conn.execute(
                    "UPDATE sessions SET title = ? WHERE id = ? AND title = ''",
                    (query[:20] if len(query) > 20 else query, session_id)
                )
                conn.commit()
                conn.close()

    except Exception as e:
        _log.error(f"LLM 调用失败: {e}")
        yield f"data: {json_mod.dumps({'type': 'error', 'data': str(e)}, ensure_ascii=False)}\n\n"