"""
API 层测试的 pytest 插件文件

提供 FastAPI TestClient 的 fixture，mock 了 DashScope 调用
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))


@pytest.fixture
def app():
    """
    创建 FastAPI 应用实例，mock 所有外部依赖
    """
    with patch("dashscope.TextEmbedding") as mock_embed, \
         patch("dashscope.Generation") as mock_gen:

        mock_embed_call = MagicMock()
        mock_embed_call.status_code = 200
        mock_embed_call.output = MagicMock()
        mock_embed_call.output.embeddings = [
            MagicMock(embedding=[0.1] * 1536)
        ]
        mock_embed.call = MagicMock(return_value=mock_embed_call)

        mock_gen_call = MagicMock()
        mock_gen_call.status_code = 200
        mock_gen_call.output = MagicMock()
        mock_gen_call.output.choices = [
            MagicMock(
                message=MagicMock(
                    content='{"industry": "医疗健康", "confidence": "high"}',
                    role="assistant"
                ),
                finish_reason="stop"
            )
        ]
        mock_gen.call = MagicMock(return_value=mock_gen_call)

        try:
            from main import app as fastapi_app
            yield fastapi_app
        except ImportError:
            from fastapi import FastAPI
            _app = FastAPI(title="RAG Knowledge Base")
            yield _app


@pytest.fixture
def client(app):
    """FastAPI TestClient"""
    return TestClient(app)


@pytest.fixture
def client_with_mock(app):
    """带完整 mock 的 TestClient"""
    with patch("dashscope.TextEmbedding.call") as mock_embed_call, \
         patch("dashscope.Generation.call") as mock_gen_call:

        mock_embed_ret = MagicMock()
        mock_embed_ret.status_code = 200
        mock_embed_ret.output = MagicMock()
        mock_embed_ret.output.embeddings = [
            MagicMock(embedding=[0.1] * 1536)
        ]
        mock_embed_call.return_value = mock_embed_ret

        mock_gen_ret = MagicMock()
        mock_gen_ret.status_code = 200
        mock_gen_ret.output = MagicMock()
        mock_gen_ret.output.choices = [
            MagicMock(
                message=MagicMock(
                    content='{"industry": "医疗健康", "confidence": "high"}',
                    role="assistant"
                ),
                finish_reason="stop"
            )
        ]
        mock_gen_call.return_value = mock_gen_ret

        yield TestClient(app)