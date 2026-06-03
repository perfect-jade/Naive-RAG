"""
BM25 索引管理
"""
import pickle
import logging
from pathlib import Path
from typing import Optional

import jieba
from rank_bm25 import BM25Okapi

_log = logging.getLogger(__name__)


class BM25Engine:
    """BM25 关键词检索引擎"""

    def __init__(self, index_dir: Path):
        self.index_dir = Path(index_dir)
        self.index_dir.mkdir(parents=True, exist_ok=True)
        self.index_path = self.index_dir / "bm25_index.pkl"
        self.chunks_path = self.index_dir / "bm25_chunks.json"
        self._bm25: Optional[BM25Okapi] = None
        self._chunks: list[dict] = []
        self._load()

    def _load(self):
        """加载已有的索引"""
        import json
        if self.index_path.exists() and self.chunks_path.exists():
            try:
                with open(self.index_path, "rb") as f:
                    self._bm25 = pickle.load(f)
                with open(self.chunks_path, "r", encoding="utf-8") as f:
                    self._chunks = json.load(f)
            except Exception as e:
                _log.warning(f"加载 BM25 索引失败: {e}，将创建新索引")
                self._create_new()
        else:
            self._create_new()

    def _create_new(self):
        """创建空索引"""
        self._bm25 = None
        self._chunks = []

    def _save(self):
        """保存索引"""
        import json
        if self._bm25 is not None:
            with open(self.index_path, "wb") as f:
                pickle.dump(self._bm25, f)
            with open(self.chunks_path, "w", encoding="utf-8") as f:
                json.dump(self._chunks, f, ensure_ascii=False)

    def add(self, chunks: list[dict]):
        """添加文本块到 BM25 索引"""
        if not chunks:
            return

        self._chunks.extend(chunks)
        tokenized = [list(jieba.cut(chunk["content"])) for chunk in self._chunks]
        self._bm25 = BM25Okapi(tokenized)
        self._save()

    def search(self, query: str, k: int = 10) -> list[dict]:
        """检索 Top-K 结果"""
        if self._bm25 is None or len(self._chunks) == 0:
            return []

        tokenized_query = list(jieba.cut(query))
        k = min(k, len(self._chunks))
        scores = self._bm25.get_scores(tokenized_query)
        top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:k]

        results = []
        for idx in top_indices:
            results.append({
                "chunk_id": self._chunks[idx].get("chunk_id", ""),
                "doc_id": self._chunks[idx].get("doc_id", ""),
                "content": self._chunks[idx]["content"],
                "score": float(scores[idx]),
                "bm25_rank": idx,
            })
        return results

    def remove_by_doc_ids(self, doc_ids: list[str]):
        """删除指定文档的文本块"""
        ids_to_remove = set(doc_ids)
        self._chunks = [c for c in self._chunks if c.get("doc_id") not in ids_to_remove]
        if self._chunks:
            tokenized = [list(jieba.cut(chunk["content"])) for chunk in self._chunks]
            self._bm25 = BM25Okapi(tokenized)
        else:
            self._bm25 = None
        self._save()

    def remove_by_ids(self, chunk_ids: list[str]):
        """删除指定 ID 的文本块"""
        ids_to_remove = set(chunk_ids)
        self._chunks = [c for c in self._chunks if c.get("chunk_id") not in ids_to_remove]
        if self._chunks:
            tokenized = [list(jieba.cut(chunk["content"])) for chunk in self._chunks]
            self._bm25 = BM25Okapi(tokenized)
        else:
            self._bm25 = None
        self._save()

    @property
    def count(self) -> int:
        return len(self._chunks)