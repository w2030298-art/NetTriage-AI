"""TextNormalizer 单元测试 — Module E Step 24."""

from __future__ import annotations

from nettriage.rules.text_normalizer import TextNormalizer, is_insufficient, normalize


class TestNormalize:
    """测试 normalize 方法的各个方面。"""

    def test_strip_and_collapse_whitespace(self) -> None:
        """多余空白应被去除/合并。"""
        result = TextNormalizer.normalize("  hello   world  \t\n")
        assert result == "hello world"

    def test_fullwidth_to_halfwidth_letters(self) -> None:
        """全角英文字母应转为半角。"""
        # 全角 'Ａ' (U+FF21) → 半角 'A' (U+0041)
        result = TextNormalizer.normalize("\uff28\uff45\uff4c\uff4c\uff4f")  # Ｈｅｌｌｏ
        assert result == "hello"

    def test_fullwidth_to_halfwidth_digits(self) -> None:
        """全角数字应转为半角（NFKC 归一化）。"""
        result = TextNormalizer.normalize("\uff11\uff12\uff13")  # １２３
        assert result == "123"

    def test_fullwidth_to_halfwidth_punctuation(self) -> None:
        """全角标点应转为半角。"""
        result = TextNormalizer.normalize("\uff08hello\uff09")  # （hello）
        assert result == "(hello)"

    def test_fullwidth_space_to_halfwidth(self) -> None:
        """全角空格 (U+3000) 应转为半角空格。"""
        result = TextNormalizer.normalize("hello\u3000world")
        assert result == "hello world"

    def test_lowercase_english(self) -> None:
        """英文大写应转为小写。"""
        result = TextNormalizer.normalize("HELLO World DNS Error")
        assert result == "hello world dns error"

    def test_preserve_chinese(self) -> None:
        """中文字符应保持不变。"""
        result = TextNormalizer.normalize("用户  反馈  DNS  解析  失败！")
        assert result == "用户 反馈 dns 解析 失败!"

    def test_combined_fullwidth_and_case(self) -> None:
        """同时测试全角转换和大小写。"""
        # 全角大写英文 → 半角小写英文
        result = TextNormalizer.normalize("\uff24\uff2e\uff33")  # ＤＮＳ
        assert result == "dns"

    def test_empty_string(self) -> None:
        """空字符串应返回空。"""
        result = TextNormalizer.normalize("")
        assert result == ""

    def test_only_whitespace(self) -> None:
        """仅含空白应返回空字符串。"""
        result = TextNormalizer.normalize("   \t\n  ")
        assert result == ""

    def test_module_level_convenience(self) -> None:
        """模块级 normalize 函数应与类方法等效。"""
        cls_result = TextNormalizer.normalize("  HELLO  WORLD  ")
        fn_result = normalize("  HELLO  WORLD  ")
        assert fn_result == cls_result == "hello world"


class TestIsInsufficient:
    """测试 is_insufficient 方法。"""

    def test_short_cjk_text_insufficient(self) -> None:
        """含 CJK 字符但不足 8 个非空白字符 → True。"""
        assert TextNormalizer.is_insufficient("信号弱") is True  # 3 chars

    def test_adequate_cjk_text_sufficient(self) -> None:
        """含 CJK 字符且 8+ 个非空白字符 → False。"""
        assert TextNormalizer.is_insufficient("用户反馈网络信号很弱需要处理") is False  # 13 chars

    def test_exactly_eight_cjk_chars(self) -> None:
        """正好 8 个非空白 CJK 字符 → False。"""
        assert TextNormalizer.is_insufficient("网络故障诊断系统检测到问题") is False  # 12 chars

    def test_seven_cjk_chars_insufficient(self) -> None:
        """7 个非空白 CJK 字符 → True。"""
        text = TextNormalizer.normalize("信号弱无法上网")  # 7 chars
        assert TextNormalizer.is_insufficient(text) is True

    def test_short_english_text_insufficient(self) -> None:
        """英文单词不足 4 个 → True。"""
        assert TextNormalizer.is_insufficient("dns error") is True  # 2 words

    def test_three_english_words_insufficient(self) -> None:
        """3 个英文单词 → True。"""
        assert TextNormalizer.is_insufficient("packet loss detected") is True  # 3 words

    def test_four_english_words_sufficient(self) -> None:
        """4 个英文单词 → False。"""
        assert (
            TextNormalizer.is_insufficient("dns resolution failure detected repeatedly")
            is False
        )  # 5 words

    def test_mixed_cjk_english_short(self) -> None:
        """混合 CJK+英文但不足 8 字符 → True。"""
        assert TextNormalizer.is_insufficient("dns 错") is True  # ~4 chars

    def test_module_level_convenience(self) -> None:
        """模块级 is_insufficient 函数应与类方法等效。"""
        cls_result = TextNormalizer.is_insufficient("short")
        fn_result = is_insufficient("short")
        assert fn_result == cls_result is True
