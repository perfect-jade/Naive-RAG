"""
DashScope LLM 调用封装
"""
import json
import logging
import dashscope
from dashscope import Generation

from backend.config import get_api_key, get_llm_model

_log = logging.getLogger(__name__)


def _ensure_api_key():
    """确保设置了 API Key"""
    key = get_api_key()
    if key:
        dashscope.api_key = key
    return key


def chat_completion(
    messages: list[dict],
    model: str | None = None,
    temperature: float = 0.7,
    stream: bool = False,
):
    """调用 DashScope LLM 进行对话补全"""
    _ensure_api_key()
    model = model or get_llm_model()
    return Generation.call(
        model=model,
        messages=messages,
        temperature=temperature,
        result_format='message',
        stream=stream,
        incremental_output=True,
    )


def route_industry(user_query: str, industries: list[dict]) -> dict:
    """调用 LLM 判断用户问题属于哪个行业"""
    _ensure_api_key()

    industry_list = json.dumps(
        [{"name": ind["name"], "description": ind.get("description", "")} for ind in industries],
        ensure_ascii=False
    )

    prompt = f"""你是一个行业分类助手。当前知识库包含以下行业：
{industry_list}

请判断以下用户问题属于哪个行业，只返回 JSON 格式，不要包含其他内容：
{{"industry": "行业名称", "confidence": "high/medium/low"}}

如果问题不属于任何行业，返回：
{{"industry": "general", "confidence": "low"}}

用户问题：{user_query}"""

    try:
        model = get_llm_model()
        resp = Generation.call(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            result_format='message',
        )

        if resp and isinstance(resp, dict) and 'output' in resp:
            content = resp['output']['choices'][0]['message']['content']
            content = content.strip()
            if content.startswith("```"):
                lines = content.split("\n")
                content = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
            result = json.loads(content)
            return {
                "industry": result.get("industry", "general"),
                "confidence": result.get("confidence", "low"),
            }
        return {"industry": "general", "confidence": "low"}
    except (json.JSONDecodeError, Exception) as e:
        _log.warning(f"行业路由判断失败: {e}")
        return {"industry": "general", "confidence": "low"}