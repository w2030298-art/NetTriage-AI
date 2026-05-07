"""基于关键词权重的规则分类器 — Module E Step 22."""

from __future__ import annotations

from dataclasses import dataclass, field

from nettriage.rules.text_normalizer import TextNormalizer
from nettriage.schemas.enums import FaultCategory


@dataclass
class RuleClassificationResult:
    """规则分类结果数据结构。

    Attributes:
        primary_category: 主分类（得分最高的类别）。
        scores: 各类别得分映射。
        strong_match: 是否强匹配（最高得分 >= 3）。
    """

    primary_category: FaultCategory
    scores: dict[FaultCategory, float] = field(default_factory=dict)
    strong_match: bool = False


class RuleBasedClassifier:
    """基于关键词权重匹配的规则分类器。

    对归一化后的文本按各类别的关键词进行权重求和，
    选取得分最高的类别作为主分类。
    """

    def __init__(self, keyword_rules: dict[FaultCategory, dict[str, int]]) -> None:
        """初始化规则分类器。

        Args:
            keyword_rules: 关键词规则字典，{分类: {关键词: 权重}}。
        """
        self._rules = keyword_rules
        self._normalizer = TextNormalizer()

    def classify(self, description: str) -> RuleClassificationResult:
        """对故障描述进行规则分类。

        Args:
            description: 原始故障描述文本。

        Returns:
            RuleClassificationResult 包含主分类、各类得分和强匹配标志。
        """
        # 1. 归一化文本
        text = self._normalizer.normalize(description)

        # 2. 按类别计算关键词加权得分
        scores: dict[FaultCategory, float] = {}
        for category, keywords in self._rules.items():
            score: float = 0.0
            for keyword, weight in keywords.items():
                if keyword in text:
                    score += weight
            scores[category] = score

        # 3. 找到最高分
        if not scores:
            return RuleClassificationResult(
                primary_category=FaultCategory.UNKNOWN,
                scores={},
                strong_match=False,
            )

        best_category: FaultCategory = max(scores, key=lambda k: scores[k])
        best_score = scores[best_category]

        # 4. 无命中 → UNKNOWN
        if best_score == 0:
            return RuleClassificationResult(
                primary_category=FaultCategory.UNKNOWN,
                scores=scores,
                strong_match=False,
            )

        return RuleClassificationResult(
            primary_category=best_category,
            scores=scores,
            strong_match=best_score >= 3,
        )
