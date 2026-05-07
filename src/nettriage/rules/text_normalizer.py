"""文本归一化器 — Module E Step 20.

支持类方法和模块级便捷函数两种调用方式。
"""

from __future__ import annotations

import re
import unicodedata


class TextNormalizer:
    """文本归一化器：去空白、全半角转换、英文字母小写、中文保留。"""

    # 全角空格 U+3000 → 半角空格 U+0020
    _FULLWIDTH_SPACE = "\u3000"
    _HALFWIDTH_SPACE = "\u0020"

    # 全角字符范围：U+FF01–U+FF5E → 半角 U+0021–U+007E
    _FULLWIDTH_START = 0xFF01
    _FULLWIDTH_END = 0xFF5E
    _FULLWIDTH_OFFSET = 0xFF01 - 0x0021

    # CJK 统一表意文字主要范围
    _CJK_RE = re.compile(r"[\u4E00-\u9FFF\u3400-\u4DBF\uF900-\uFAFF]")
    # 英文单词（字母序列）
    _WORD_RE = re.compile(r"[a-zA-Z]+")

    @classmethod
    def normalize(cls, text: str) -> str:
        """归一化文本：去首尾空白、合并连续空白、全角→半角、英文小写。

        Args:
            text: 原始故障描述文本。

        Returns:
            归一化后的文本。
        """
        # 1. 去除首尾空白，合并连续空白为单个空格
        text = " ".join(text.split())

        # 2. 全角空格 → 半角空格
        text = text.replace(cls._FULLWIDTH_SPACE, cls._HALFWIDTH_SPACE)

        # 3. 全角字符 → 半角字符
        result: list[str] = []
        for ch in text:
            code = ord(ch)
            if cls._FULLWIDTH_START <= code <= cls._FULLWIDTH_END:
                result.append(chr(code - cls._FULLWIDTH_OFFSET))
            else:
                result.append(ch)
        text = "".join(result)

        # 4. Unicode NFKC 归一化（全角数字/字母等）
        text = unicodedata.normalize("NFKC", text)

        # 5. 英文大写 → 小写（保留中文等非 ASCII 字符不变）
        text = text.lower()

        return text

    @classmethod
    def is_insufficient(cls, text: str) -> bool:
        """判断文本是否信息不足。

        规则：
        - 含中文/CJK字符的文本：去除空白后不足 8 个字符 → True
        - 纯英文文本：英文单词不足 4 个 → True

        Args:
            text: 归一化后的文本（通常是 normalize() 的输出）。

        Returns:
            True 表示信息不足，不应进行后续分类。
        """
        # 判断是否包含 CJK 字符
        has_cjk = bool(cls._CJK_RE.search(text))

        if has_cjk:
            # 去除所有空白字符后统计非空白字符数
            non_ws = "".join(text.split())
            return len(non_ws) < 8

        # 纯英文：统计单词数
        words = cls._WORD_RE.findall(text)
        return len(words) < 4


# 模块级便捷函数，等同于调用类方法
_normalizer = TextNormalizer()


def normalize(text: str) -> str:
    """模块级便捷函数：归一化文本。"""
    return TextNormalizer.normalize(text)


def is_insufficient(text: str) -> bool:
    """模块级便捷函数：判断文本是否信息不足。"""
    return TextNormalizer.is_insufficient(text)
