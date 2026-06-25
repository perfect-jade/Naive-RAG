"""
网络搜索模块 - 当知识库检索失败时进行网络搜索
"""
import json
import logging
from typing import List, Dict, Optional

from backend.config import get_api_key
from backend.core.llm_client import chat_completion

_log = logging.getLogger(__name__)


def web_search(query: str, max_results: int = 5) -> List[Dict]:
    """
    使用 LLM 进行网络搜索
    返回搜索结果列表
    """
    import urllib.parse
    import urllib.request
    import ssl

    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    search_results = []

    try:
        search_url = "https://www.bing.com/search"
        params = urllib.parse.urlencode({"q": query, "count": max_results, "mkt": "zh-CN"})
        full_url = f"{search_url}?{params}"

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

        req = urllib.request.Request(full_url, headers=headers)
        with urllib.request.urlopen(req, context=ssl_context, timeout=15) as response:
            html = response.read().decode("utf-8", errors="ignore")

        search_results = _parse_bing_results(html, max_results)

    except Exception as e:
        _log.warning(f"网络搜索失败: {e}")
        search_results = _llm_generate_search_results(query)

    return search_results


def _parse_bing_results(html: str, max_results: int) -> List[Dict]:
    """解析 Bing 搜索结果"""
    import re

    results = []

    pattern = r'<li class="b_algo".*?</li>'
    matches = re.findall(pattern, html, re.DOTALL)

    for match in matches[:max_results]:
        try:
            title_match = re.search(r'<h2.*?>(.*?)</h2>', match, re.DOTALL)
            title = title_match.group(1).strip() if title_match else ""

            link_match = re.search(r'<a href="([^"]+)"', match)
            link = link_match.group(1) if link_match else ""

            snippet_match = re.search(r'<p class="b_lineclamp2".*?>(.*?)</p>', match, re.DOTALL)
            snippet = snippet_match.group(1).strip() if snippet_match else ""

            title = re.sub(r'<[^>]+>', '', title)
            snippet = re.sub(r'<[^>]+>', '', snippet)

            if title and snippet:
                results.append({
                    "title": title,
                    "url": link,
                    "snippet": snippet,
                    "source": "web_search",
                })
        except Exception as e:
            _log.debug(f"解析搜索结果失败: {e}")
            continue

    return results


def _llm_generate_search_results(query: str) -> List[Dict]:
    """使用 LLM 生成模拟搜索结果（当网络搜索不可用时）"""
    system_prompt = (
        "你是一个搜索引擎。请根据用户的问题生成相关的搜索结果。"
        "返回格式为 JSON 数组，包含 title、url、snippet 字段。"
        "确保信息准确，不要编造不存在的链接。"
    )

    user_prompt = f"请为以下问题生成搜索结果，最多返回3条：\n{query}"

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    try:
        response = chat_completion(messages, temperature=0.3, stream=False)
        if response and isinstance(response, dict) and 'output' in response:
            content = response['output']['choices'][0]['message']['content']
            content = content.strip()
            if content.startswith("```"):
                lines = content.split("\n")
                content = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
            result = json.loads(content)
            if isinstance(result, list):
                return result
    except Exception as e:
        _log.warning(f"LLM 生成搜索结果失败: {e}")

    return [{"title": "网络搜索不可用", "url": "", "snippet": "无法获取网络搜索结果，请检查网络连接。"}]