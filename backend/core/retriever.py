"""
混合检索 + RRF 融合排序
"""
import logging
from typing import Optional

from backend.core.faiss_engine import FAISSEngine
from backend.core.bm25_engine import BM25Engine
from backend.core.embedding import get_single_embedding, normalize_embedding
from backend.config import FAISS_TOP_K, BM25_TOP_K, FUSION_TOP_K, RRF_K

_log = logging.getLogger(__name__)


class HybridRetriever:
    """混合检索器：FAISS + BM25 + RRF 融合"""

    def __init__(self, faiss_engine: FAISSEngine, bm25_engine: BM25Engine):
        self.faiss = faiss_engine
        self.bm25 = bm25_engine

    def retrieve(
        self,
        query: str,
        faiss_top_k: int = FAISS_TOP_K,
        bm25_top_k: int = BM25_TOP_K,
        fusion_top_k: int = FUSION_TOP_K,
        rrf_k: int = RRF_K,
    ) -> list[dict]:
        """
        混合检索
        1. FAISS 语义检索
        2. BM25 关键词检索
        3. RRF 融合排序
        """
        query_embedding = get_single_embedding(query)
        faiss_results = self.faiss.search(query_embedding, k=faiss_top_k)
        bm25_results = self.bm25.search(query, k=bm25_top_k)

        return self._rrf_fusion(faiss_results, bm25_results, fusion_top_k, rrf_k)

    def _rrf_fusion(
        self,
        faiss_results: list[dict],
        bm25_results: list[dict],
        top_k: int,
        k: int = RRF_K,
    ) -> list[dict]:
        """RRF 融合排序算法"""
        # 如果只有一个检索源有结果，直接返回
        if not faiss_results and not bm25_results:
            return []
        if not bm25_results:
            return faiss_results[:top_k]
        if not faiss_results:
            return bm25_results[:top_k]

        # 构建 rank 映射
        faiss_ranks = {r["chunk_id"]: i + 1 for i, r in enumerate(faiss_results)}
        bm25_ranks = {r["chunk_id"]: i + 1 for i, r in enumerate(bm25_results)}

        # 合并结果信息
        all_results = {}
        for r in faiss_results:
            all_results[r["chunk_id"]] = {"faiss_score": r["score"], "bm25_score": 0.0}
        for r in bm25_results:
            if r["chunk_id"] in all_results:
                all_results[r["chunk_id"]]["bm25_score"] = r["score"]
            else:
                all_results[r["chunk_id"]] = {"faiss_score": 0.0, "bm25_score": r["score"]}

        # 计算 RRF 分数
        rrf_scores = {}
        for chunk_id in all_results:
            score = 0.0
            if chunk_id in faiss_ranks:
                score += 1.0 / (k + faiss_ranks[chunk_id])
            if chunk_id in bm25_ranks:
                score += 1.0 / (k + bm25_ranks[chunk_id])
            rrf_scores[chunk_id] = score

        ranked = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)
        top_results = ranked[:top_k]

        return [
            {
                "chunk_id": chunk_id,
                "rrf_score": round(score, 6),
                "faiss_score": all_results[chunk_id]["faiss_score"],
                "bm25_score": all_results[chunk_id]["bm25_score"],
            }
            for chunk_id, score in top_results
        ]