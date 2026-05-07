"""ReviewPolicy 单元测试 — Module E Step 24."""

from __future__ import annotations

import pytest

from nettriage.rules.review_policy import ReviewPolicy
from nettriage.rules.rule_classifier import RuleClassificationResult
from nettriage.schemas.classification import LLMClassificationOutput
from nettriage.schemas.enums import FaultCategory


def _make_llm_result(
    primary: FaultCategory = FaultCategory.DNS_FAILURE,
    confidence: float = 0.90,
    scores: dict[str, float] | None = None,
    secondary: list[FaultCategory] | None = None,
) -> LLMClassificationOutput:
    """构建测试用的 LLM 分类输出。"""
    return LLMClassificationOutput(
        primary_category=primary,
        secondary_categories=secondary or [],
        confidence=confidence,
        category_scores=scores or {primary.value: 0.90},
        key_symptoms=["test"],
        summary="test summary for unit test purposes",
        troubleshooting_steps=["step 1"],
    )


def _make_rule_result(
    primary: FaultCategory = FaultCategory.DNS_FAILURE,
    strong_match: bool = True,
) -> RuleClassificationResult:
    """构建测试用的规则分类结果。"""
    return RuleClassificationResult(
        primary_category=primary,
        scores={FaultCategory.DNS_FAILURE: 3.0},
        strong_match=strong_match,
    )


class TestReviewPolicy:
    """测试 ReviewPolicy 的 evaluate 方法。"""

    @pytest.fixture
    def policy(self) -> ReviewPolicy:
        """提供默认参数的 ReviewPolicy 实例。"""
        return ReviewPolicy(confidence_threshold=0.80, conflict_score_delta=0.08)

    def test_low_confidence_triggers_review(self, policy: ReviewPolicy) -> None:
        """LLM 置信度低于阈值 → review_required=True，理由是 REVIEW_LOW_CONFIDENCE。"""
        llm = _make_llm_result(confidence=0.50)
        rule = _make_rule_result()
        decision = policy.evaluate(llm_result=llm, rule_result=rule)
        assert decision.review_required is True
        assert "REVIEW_LOW_CONFIDENCE" in decision.reasons

    def test_high_confidence_no_review(self, policy: ReviewPolicy) -> None:
        """LLM 置信度达标且无冲突 → review_required=False。"""
        llm = _make_llm_result(confidence=0.95)
        rule = _make_rule_result(strong_match=False)
        decision = policy.evaluate(llm_result=llm, rule_result=rule)
        assert decision.review_required is False
        assert len(decision.reasons) == 0

    def test_score_conflict_triggers_review(self, policy: ReviewPolicy) -> None:
        """top1 与 top2 得分差距小于 delta → review_required=True。"""
        llm = _make_llm_result(
            scores={"DNS_FAILURE": 0.45, "PACKET_LOSS": 0.42}  # delta = 0.03 < 0.08
        )
        rule = _make_rule_result(strong_match=False)
        decision = policy.evaluate(llm_result=llm, rule_result=rule)
        assert decision.review_required is True
        assert "REVIEW_CATEGORY_CONFLICT" in decision.reasons

    def test_no_score_conflict_wide_gap(self, policy: ReviewPolicy) -> None:
        """top1 与 top2 差距大 → 不触发 REVIEW_CATEGORY_CONFLICT。"""
        llm = _make_llm_result(
            scores={"DNS_FAILURE": 0.90, "PACKET_LOSS": 0.10}  # delta = 0.80 > 0.08
        )
        rule = _make_rule_result(strong_match=False)
        decision = policy.evaluate(llm_result=llm, rule_result=rule)
        assert "REVIEW_CATEGORY_CONFLICT" not in decision.reasons

    def test_single_score_no_conflict(self, policy: ReviewPolicy) -> None:
        """只有一个类别得分 → 不触发 REVIEW_CATEGORY_CONFLICT。"""
        llm = _make_llm_result(scores={"DNS_FAILURE": 0.90})
        rule = _make_rule_result(strong_match=False)
        decision = policy.evaluate(llm_result=llm, rule_result=rule)
        assert "REVIEW_CATEGORY_CONFLICT" not in decision.reasons

    def test_rule_llm_conflict_triggers_review(self, policy: ReviewPolicy) -> None:
        """规则强匹配与 LLM 主分类不同 → review_required=True。"""
        llm = _make_llm_result(primary=FaultCategory.AUTH_FAILURE)
        rule = _make_rule_result(
            primary=FaultCategory.DNS_FAILURE, strong_match=True
        )
        decision = policy.evaluate(llm_result=llm, rule_result=rule)
        assert decision.review_required is True
        assert "REVIEW_RULE_LLM_CONFLICT" in decision.reasons

    def test_rule_llm_same_no_conflict(self, policy: ReviewPolicy) -> None:
        """规则强匹配与 LLM 主分类相同 → 不触发 REVIEW_RULE_LLM_CONFLICT。"""
        llm = _make_llm_result(primary=FaultCategory.DNS_FAILURE)
        rule = _make_rule_result(
            primary=FaultCategory.DNS_FAILURE, strong_match=True
        )
        decision = policy.evaluate(llm_result=llm, rule_result=rule)
        assert "REVIEW_RULE_LLM_CONFLICT" not in decision.reasons

    def test_weak_rule_match_no_conflict(self, policy: ReviewPolicy) -> None:
        """规则非强匹配 + LLM 不同分类 → 不触发 REVIEW_RULE_LLM_CONFLICT。"""
        llm = _make_llm_result(primary=FaultCategory.AUTH_FAILURE)
        rule = _make_rule_result(
            primary=FaultCategory.DNS_FAILURE, strong_match=False
        )
        decision = policy.evaluate(llm_result=llm, rule_result=rule)
        assert "REVIEW_RULE_LLM_CONFLICT" not in decision.reasons

    def test_fallback_triggers_review(self, policy: ReviewPolicy) -> None:
        """使用了规则兜底 → review_required=True，理由是 REVIEW_FALLBACK_USED。"""
        llm = _make_llm_result()
        rule = _make_rule_result(strong_match=False)
        decision = policy.evaluate(
            llm_result=llm, rule_result=rule, fallback_used=True
        )
        assert decision.review_required is True
        assert "REVIEW_FALLBACK_USED" in decision.reasons

    def test_parse_error_triggers_review(self, policy: ReviewPolicy) -> None:
        """LLM 输出有解析错误 → review_required=True。"""
        llm = _make_llm_result()
        rule = _make_rule_result(strong_match=False)
        decision = policy.evaluate(
            llm_result=llm, rule_result=rule, parse_error="invalid json"
        )
        assert decision.review_required is True
        assert "REVIEW_LLM_OUTPUT_INVALID" in decision.reasons

    def test_llm_result_none_triggers_review(self, policy: ReviewPolicy) -> None:
        """LLM 结果为 None → review_required=True，理由是 REVIEW_LLM_RESULT_MISSING。"""
        rule = _make_rule_result()
        decision = policy.evaluate(llm_result=None, rule_result=rule)
        assert decision.review_required is True
        assert "REVIEW_LLM_RESULT_MISSING" in decision.reasons

    def test_llm_result_none_returns_immediately(self, policy: ReviewPolicy) -> None:
        """LLM 结果为 None 时应立即返回，不检查置信度等后续规则。"""
        rule = _make_rule_result()
        decision = policy.evaluate(
            llm_result=None, rule_result=rule, fallback_used=True
        )
        # REVIEW_FALLBACK_USED 和 REVIEW_LLM_RESULT_MISSING 都应出现
        # 但不会继续检查 LLM 相关的后续规则
        assert decision.review_required is True
        assert "REVIEW_LLM_RESULT_MISSING" in decision.reasons
        # 后续规则不会执行（因为已经 return 了）
        assert "REVIEW_RULE_LLM_CONFLICT" not in decision.reasons


class TestReviewPolicyCustomThresholds:
    """测试自定义阈值参数。"""

    def test_custom_confidence_threshold(self) -> None:
        """自定义置信度阈值应正确生效。"""
        policy = ReviewPolicy(confidence_threshold=0.50)
        llm = _make_llm_result(confidence=0.60)
        rule = _make_rule_result(strong_match=False)
        decision = policy.evaluate(llm_result=llm, rule_result=rule)
        # 0.60 >= 0.50 → 不应触发
        assert "REVIEW_LOW_CONFIDENCE" not in decision.reasons

    def test_custom_conflict_delta(self) -> None:
        """自定义分数差阈值应正确生效。"""
        policy = ReviewPolicy(conflict_score_delta=0.20)
        llm = _make_llm_result(
            scores={"DNS_FAILURE": 0.50, "PACKET_LOSS": 0.35}  # delta = 0.15 < 0.20
        )
        rule = _make_rule_result(strong_match=False)
        decision = policy.evaluate(llm_result=llm, rule_result=rule)
        assert "REVIEW_CATEGORY_CONFLICT" in decision.reasons

    def test_custom_conflict_delta_no_trigger(self) -> None:
        """自定义分数差阈值大于实际 delta → 不触发。"""
        policy = ReviewPolicy(conflict_score_delta=0.05)
        llm = _make_llm_result(
            scores={"DNS_FAILURE": 0.50, "PACKET_LOSS": 0.35}  # delta = 0.15 > 0.05
        )
        rule = _make_rule_result(strong_match=False)
        decision = policy.evaluate(llm_result=llm, rule_result=rule)
        assert "REVIEW_CATEGORY_CONFLICT" not in decision.reasons
