"""
文件解析服务 - 支持 PDF/Word/TXT/Markdown
"""
import logging
from pathlib import Path

_log = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md"}


def parse_file(file_path: Path) -> str:
    """根据文件类型解析文本内容"""
    ext = file_path.suffix.lower()

    if ext not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"不支持的文件类型: {ext}，支持的类型: {', '.join(SUPPORTED_EXTENSIONS)}")

    if ext == ".txt":
        return _parse_txt(file_path)
    elif ext == ".md":
        return _parse_md(file_path)
    elif ext == ".docx":
        return _parse_docx(file_path)
    elif ext == ".pdf":
        return _parse_pdf(file_path)
    else:
        raise ValueError(f"不支持的文件类型: {ext}")


def _parse_txt(file_path: Path) -> str:
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except UnicodeDecodeError:
        with open(file_path, "r", encoding="gbk") as f:
            return f.read()


def _parse_md(file_path: Path) -> str:
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except UnicodeDecodeError:
        with open(file_path, "r", encoding="gbk") as f:
            return f.read()


def _parse_docx(file_path: Path) -> str:
    try:
        from docx import Document
        doc = Document(str(file_path))
        return "\n".join([p.text for p in doc.paragraphs if p.text.strip()])
    except ImportError:
        raise ImportError("python-docx 未安装，无法解析 .docx 文件")


def _parse_pdf(file_path: Path) -> str:
    try:
        from PyPDF2 import PdfReader
        reader = PdfReader(str(file_path))
        text_parts = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                text_parts.append(text)
        return "\n".join(text_parts)
    except ImportError:
        raise ImportError("PyPDF2 未安装，无法解析 .pdf 文件")


def get_file_title(file_path: Path) -> str:
    """从文件名中提取标题"""
    return file_path.stem