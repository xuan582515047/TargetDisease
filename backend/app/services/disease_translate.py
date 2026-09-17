"""用 DeepSeek 将中文疾病名翻译为英文，用于 Open Targets 检索。

仅负责查询词的翻译，不参与疾病 ID 的最终映射；Open Targets 仍是疾病标识的
权威来源。模型未配置或翻译失败时由调用方回退到原始输入。
"""
from __future__ import annotations

import re

from app.services.deepseek import chat_completion

_CJK = re.compile(r"[\u4e00-\u9fff]")

SYSTEM_PROMPT = (
    "你是生物医药术语翻译助手。把用户输入的中文疾病名称翻译成一个最通用的"
    "英文疾病标准名（不是症状描述），只输出英文名称本身，不要解释、不要加引号或标点。"
)


def is_chinese(text: str) -> bool:
    """判断文本是否含中文字符。"""
    return bool(_CJK.search(text))


def translate_to_english(api_key: str, zh: str) -> str:
    """把中文疾病名翻译为英文标准名，失败时返回原输入。"""
    content = chat_completion(
        api_key,
        SYSTEM_PROMPT,
        zh,
        temperature=0.0,
        max_tokens=64,
    ).content
    name = content.strip().strip('"').strip("'")
    return name or zh
