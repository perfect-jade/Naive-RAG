"""
行业路由器 - LLM 判断用户问题所属行业
"""
import logging
import json

from backend.core.llm_client import route_industry as llm_route
from backend.services.industry_service import list_industries

_log = logging.getLogger(__name__)


def route_to_industry(user_query: str) -> dict:
    """
    根据用户问题路由到最匹配的行业
    
    返回: {"industry": "行业名称", "slug": "slug", "confidence": "high/medium/low"}
    """
    industries = list_industries()

    if not industries:
        return {"industry": "general", "slug": "general", "confidence": "low"}

    # 确保有 slug 字段
    industry_list = []
    for ind in industries:
        industry_list.append({
            "name": ind["name"],
            "slug": ind.get("slug", ""),
            "description": ind.get("description", ""),
        })

    result = llm_route(user_query, industry_list)

    # 验证返回的行业名是否在列表中
    industry_name = result.get("industry", "general")
    if industry_name == "general":
        return {"industry": "general", "slug": "general", "confidence": result.get("confidence", "low")}

    # 按名称或 slug 匹配
    matched = None
    for ind in industry_list:
        if ind["name"] == industry_name or ind["slug"] == industry_name:
            matched = ind
            break

    if matched:
        return {
            "industry": matched["name"],
            "slug": matched["slug"],
            "confidence": result.get("confidence", "medium"),
        }

    # 未匹配到，返回 general
    return {"industry": "general", "slug": "general", "confidence": "low"}