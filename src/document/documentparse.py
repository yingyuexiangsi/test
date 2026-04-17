"""
PDF 解析服务。

职责：调用 Paddle OCR 进行版面解析，并整理为结构化结果。
"""

from __future__ import annotations

from typing import BinaryIO

import base64
import httpx
import re

from src.document.config import settings


TEXT_LIKE_LABELS = {
    "text",
    "abstract",
}

# 结构化块标签集合
TABLE_LABELS = {"table"}
FIGURE_LABELS = {"figure_title"}
FORMULA_LABELS = {"formula"}
REFERENCE_LABELS = {"reference"}
DOC_TITLE_LABELS = {"doc_title"}
PARAGRAPH_TITLE_LABELS = {"paragraph_title"}




def _normalize_heading_text(text: str) -> str:
    """
    清理标题文本中的井号与编号前缀。

    - 去除 Markdown 标题前缀
    - 去除开头的数字/点号等编号
    """
    cleaned = re.sub(r"^#+", "", text or "").strip()
    cleaned = re.sub(r"^[\d\s\.\-]+", "", cleaned).strip()
    return cleaned


def _extract_heading_level_and_title(text: str) -> tuple[int, str]:
    """
    解析标题层级与标题文本。

    - 通过 '#' 数量推断层级
    - 无匹配时默认层级为 1
    """
    match = re.match(r"^(#+)\s*(.*)$", (text or "").strip())
    if match:
        level = len(match.group(1))
        title = match.group(2).strip()
        return max(level, 1), title
    cleaned = (text or "").strip()
    return 1, cleaned


def _is_noise_text(text: str) -> bool:
    """判断文本是否过短或缺少有效字符。"""
    if not text:
        return True
    stripped = re.sub(r"\s+", " ", text).strip()
    if len(stripped) < 15:
        return True
    meaningful_chars = re.findall(r"[A-Za-z0-9\u4e00-\u9fff]", stripped)
    if len(meaningful_chars) < 15:
        return True
    return False


def parse_pdf_with_paddle(fileobj: BinaryIO) -> dict:
    """调用 Paddle OCR 解析 PDF，并整理结构化结果。"""
    if not settings.paddle_ocr_api_key:
        raise ValueError("paddle_ocr_api_key is required")
    if not settings.paddle_ocr_api_url:
        raise ValueError("paddle_ocr_api_url is required")

    # 读取并编码文件
    file_bytes = fileobj.read()
    file_data = base64.b64encode(file_bytes).decode("ascii")

    headers = {
        "Authorization": f"token {settings.paddle_ocr_api_key}",
        "Content-Type": "application/json",
    }

    # Paddle OCR 必填参数
    required_payload = {
        "file": file_data,
        "fileType": 0,
    }

    # Paddle OCR 可选能力开关
    optional_payload = {
        "useDocOrientationClassify": False,
        "useDocUnwarping": False,
        "useTextlineOrientation": False,
        "useChartRecognition": False,
    }

    payload = {**required_payload, **optional_payload}

    response = httpx.post(
        settings.paddle_ocr_api_url,
        json=payload,
        headers=headers,
        timeout=120,
    )
    response.raise_for_status()
    data = response.json()

    result = data.get("result", {})
    layout_results = result.get("layoutParsingResults", [])

    # 聚合解析结果
    chunks = []
    tables = []
    figures = []
    formulas = []
    sections: dict[str, dict] = {}
    doc_title = ""

    chunk_idx = 0
    table_idx = 0
    figure_idx = 0
    formula_idx = 0

    heading_stack: list[tuple[int, str]] = []
    in_reference = False
    reference_level: int | None = None

    for page_index, page in enumerate(layout_results, start=1):
        pruned_result = page.get("prunedResult", {})
        parsing_res_list = pruned_result.get("parsing_res_list", [])
        # 按 block_order 保持版面顺序
        ordered_blocks = sorted(
            parsing_res_list,
            key=lambda block: (
                block.get("block_order") is None,
                block.get("block_order") if block.get("block_order") is not None else 0,
            ),
        )
        for block in ordered_blocks:
            label = (block.get("block_label") or "").strip()
            block_id = block.get("block_id")
            block_content = block.get("block_content") or ""

            # 文档标题
            if label in DOC_TITLE_LABELS:
                doc_title = block_content.strip()
                continue

            # 参考文献标题块直接跳过
            if label in REFERENCE_LABELS:
                continue

            # 表格块
            if label in TABLE_LABELS:
                tables.append(
                    {
                        "id": f"{page_index}_" + str(block_id or table_idx),
                        "page": page_index,
                        "text": block_content,
                    }
                )
                table_idx += 1
                continue

            # 图片块
            if label in FIGURE_LABELS:
                figures.append(
                    {
                        "id": f"{page_index}_" + str(block_id or figure_idx),
                        "page": page_index,
                    }
                )
                figure_idx += 1
                continue

            # 公式块
            if label in FORMULA_LABELS:
                formulas.append(
                    {
                        "id": f"{page_index}_" + str(block_id or formula_idx),
                        "page": page_index,
                    }
                )
                formula_idx += 1
                continue

            # 章节标题块
            if label in PARAGRAPH_TITLE_LABELS:
                heading_level, raw_title = _extract_heading_level_and_title(block_content)
                title = _normalize_heading_text(raw_title)
                if not title:
                    continue
                normalized_title = title.strip().lower()
                if normalized_title in {"reference", "references"}:
                    in_reference = True
                    reference_level = heading_level
                    continue
                while heading_stack and heading_stack[-1][0] >= heading_level:
                    heading_stack.pop()
                heading_stack.append((heading_level, title))
                in_reference = False
                reference_level = None
                continue

            # 跳过参考文献正文
            if in_reference:
                if heading_stack and reference_level is not None:
                    current_level = heading_stack[-1][0]
                    if current_level <= reference_level:
                        in_reference = False
                if in_reference:
                    continue

            # 正文/摘要
            if label in TEXT_LIKE_LABELS:
                if _is_noise_text(block_content):
                    continue
                section_path = " > ".join([item[1] for item in heading_stack])
                if label == "abstract":
                    section_path = "Abstract"
                chunk_id = f"{page_index}_" + str(block_id or chunk_idx)
                chunks.append(
                    {
                        "chunk_id": chunk_id,
                        "text": block_content,
                        "page": page_index,
                        "section_path": section_path,
                        "doc_title": doc_title,
                    }
                )
                # 维护章节索引
                if section_path:
                    section_entry = sections.setdefault(
                        section_path,
                        {
                            "level": heading_stack[-1][0] if heading_stack else 1,
                            "parent": heading_stack[-2][1] if len(heading_stack) > 1 else None,
                            "chunk_ids": [],
                            "pages": [],
                        },
                    )
                    section_entry["chunk_ids"].append(chunk_id)
                    section_entry["pages"].append(page_index)
                chunk_idx += 1

    # 补全文档标题
    if doc_title:
        for chunk in chunks:
            chunk["doc_title"] = doc_title

    return {
        "page_count": result.get("page_count") or len(layout_results),
        "chunks": chunks,
        "figures": figures,
        "tables": tables,
        "formulas": formulas,
        "sections": sections,
        "doc_title": doc_title,
    }
