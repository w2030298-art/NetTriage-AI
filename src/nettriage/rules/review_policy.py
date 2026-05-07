"""人工复核决策策略 — Module E Step 23.

综合 LLM 分类结果与规则分类结果判断是否需要人工复核。
"""

from __future__ import annotations

from dataclasses import dataclass, field

from nettriage.rules.rule_classifier import RuleClassificationResult
from nettriage.schemas.classification import LLMClassificationOutput


@dataclass
class ReviewDecision:
    """复核决策结果数据结构。

    Attributes:
        review_required: 是否需要进行人工复核。
        reasons: 需要复核的原因列表（可多条）。
    """

    review_required: bool
    reasons: list[str] = field(default_factory=list)


class ReviewPolicy:
    """综合 LLM 与规则分类结果的复核决策策略。

    按优先级评估以下条件：
    1. 是否使用了规则兜底（fallback）
    2. LLM 输出是否有解析错误
    3. LLM 结果是否缺失
    4. LLM 置信度是否不足
    5. 类别得分是否存在冲突（top1 与 top2 差距过小）
    6. 规则强匹配结果与 LLM 主分类是否冲突
    """

    def __init__(
        self,
        confidence_threshold: float = 0.80,
        conflict_score_delta: float = 0.08,
    ) -> None:
        """初始化复核策略。

        Args:
            confidence_threshold: LLM 置信度阈值，低于此值触发复核。
            conflict_score_delta: top1 与 top2 得分差阈值，低于此值视为冲突。
        """
        self.confidence_threshold = confidence_threshold
        self.conflict_score_delta = conflict_score_delta

    def _has_score_conflict(self, llm_result: LLMClassificationOutput) -> bool:
        """检查 LLM 类别得分中 top1 与 top2 差距是否低于阈值。

        Args:
            llm_result: LLM 分类输出。

        Returns:
            True 表示存在得分冲突（top1 - top2 < delta）。
        """
        scores = llm_result.category_scores
        if len(scores) < 2:
            return False

        sorted_scores = sorted(scores.values(), reverse=True)
        delta = sorted_scores[0] - sorted_scores[1]
        return delta < self.conflict_score_delta

    def evaluate(
        self,
        llm_result: LLMClassificationOutput | None,
        rule_result: RuleClassificationResult,
        parse_error: str | None = None,
        fallback_used: bool = False,
    ) -> ReviewDecision:
        """综合评估是否需要人工复核。

        Args:
            llm_result: LLM 分类输出，可为 None。
            rule_result: 规则分类器结果。
            parse_error: LLM 输出的解析错误信息（如有）。
            fallback_used: 是否使用了规则兜底。

        Returns:
            ReviewDecision 包含 review_required 和 reasons。
        """
        reasons: list[str] = []

        # Rule 1: 使用了规则兜底
        if fallback_used:
            reasons.append("REVIEW_FALLBACK_USED")

        # Rule 2: LLM 输出解析错误
        if parse_error is not None:
            reasons.append("REVIEW_LLM_OUTPUT_INVALID")

        # Rule 3: LLM 结果缺失 — 立即返回
        if llm_result is None:
            reasons.append("REVIEW_LLM_RESULT_MISSING")
            return ReviewDecision(review_required=True, reasons=reasons)

        # Rule 4: LLM 置信度不足
        if llm_result.confidence < self.confidence_threshold:
            reasons.append("REVIEW_LOW_CONFIDENCE")

        # Rule 5: 类别得分冲突（top1 vs top2 差距过小）
        if self._has_score_conflict(llm_result):
            reasons.append("REVIEW_CATEGORY_CONFLICT")

        # Rule 6: 规则强匹配与 LLM 主分类冲突
        if (
            rule_result.strong_match
            and rule_result.primary_category != llm_result.primary_category
        ):
            reasons.append("REVIEW_RULE_LLM_CONFLICT")

        return ReviewDecision(
            review_required=len(reasons) > 0,
            reasons=reasons,
        )
