"""RuleBasedClassifier 单元测试 — Module E Step 24."""

from __future__ import annotations

import pytest

from nettriage.rules.keyword_rules import KEYWORD_RULES
from nettriage.rules.rule_classifier import RuleBasedClassifier
from nettriage.schemas.enums import FaultCategory


class TestRuleBasedClassifier:
    """测试 RuleBasedClassifier 的 classify 方法。"""

    @pytest.fixture
    def classifier(self) -> RuleBasedClassifier:
        """提供预初始化的规则分类器实例。"""
        return RuleBasedClassifier(KEYWORD_RULES)

    def test_dns_hit(self, classifier: RuleBasedClassifier) -> None:
        """包含 DNS 关键词的文本应分类为 DNS_FAILURE。"""
        result = classifier.classify("用户反馈 DNS 解析失败，域名无法解析")
        assert result.primary_category == FaultCategory.DNS_FAILURE
        assert result.strong_match is True

    def test_pppoe_hit(self, classifier: RuleBasedClassifier) -> None:
        """包含 PPPoE 关键词的文本应分类为 AUTH_FAILURE。"""
        result = classifier.classify("pppoe 拨号认证失败，radius 超时")
        assert result.primary_category == FaultCategory.AUTH_FAILURE
        assert result.strong_match is True

    def test_wifi_weak_hit(self, classifier: RuleBasedClassifier) -> None:
        """包含 WiFi 信号弱关键词的文本应分类为 WEAK_SIGNAL。"""
        result = classifier.classify("用户反馈 wifi 信号弱，rssi 很低")
        assert result.primary_category == FaultCategory.WEAK_SIGNAL
        assert result.strong_match is True

    def test_packet_loss_hit(self, classifier: RuleBasedClassifier) -> None:
        """包含丢包关键词的文本应分类为 PACKET_LOSS。"""
        result = classifier.classify("ping 测试发现大量丢包，packet loss 严重")
        assert result.primary_category == FaultCategory.PACKET_LOSS
        assert result.strong_match is True

    def test_latency_hit(self, classifier: RuleBasedClassifier) -> None:
        """包含延迟高关键词的文本应分类为 HIGH_LATENCY。"""
        result = classifier.classify("用户反映网络延迟高，时延很大")
        assert result.primary_category == FaultCategory.HIGH_LATENCY
        assert result.strong_match is True

    def test_dropped_connection_hit(self, classifier: RuleBasedClassifier) -> None:
        """包含掉线关键词的文本应分类为 DROPPED_CONNECTION。"""
        result = classifier.classify("网络频繁中断，老是掉线")
        assert result.primary_category == FaultCategory.DROPPED_CONNECTION
        assert result.strong_match is True

    def test_config_error_hit(self, classifier: RuleBasedClassifier) -> None:
        """包含 VLAN/ACL 配置关键词的文本应分类为 CONFIG_ERROR。"""
        result = classifier.classify("vlan 配置错误导致 acl 不生效")
        assert result.primary_category == FaultCategory.CONFIG_ERROR
        assert result.strong_match is True

    def test_device_failure_hit(self, classifier: RuleBasedClassifier) -> None:
        """包含设备故障关键词的文本应分类为 DEVICE_FAILURE。"""
        result = classifier.classify("光猫故障导致路由器故障，硬件告警")
        assert result.primary_category == FaultCategory.DEVICE_FAILURE
        assert result.strong_match is True

    def test_service_outage_hit(self, classifier: RuleBasedClassifier) -> None:
        """包含大面积故障关键词的文本应分类为 SERVICE_OUTAGE。"""
        result = classifier.classify("大面积区域故障，全站不可用")
        assert result.primary_category == FaultCategory.SERVICE_OUTAGE
        assert result.strong_match is True

    def test_bandwidth_degradation_hit(self, classifier: RuleBasedClassifier) -> None:
        """包含带宽不达标关键词的文本应分类为 BANDWIDTH_DEGRADATION。"""
        result = classifier.classify("下载慢，带宽不达标，速率低")
        assert result.primary_category == FaultCategory.BANDWIDTH_DEGRADATION
        assert result.strong_match is True

    def test_no_keyword_returns_unknown(self, classifier: RuleBasedClassifier) -> None:
        """不包含任何关键词的文本应返回 UNKNOWN。"""
        result = classifier.classify("这是一段完全没有网络故障相关信息的文本描述")
        assert result.primary_category == FaultCategory.UNKNOWN
        assert result.strong_match is False
        # 所有得分应为 0
        for score in result.scores.values():
            assert score == 0.0

    def test_weak_match_not_strong(self, classifier: RuleBasedClassifier) -> None:
        """低权重关键词命中但总分不足 3 → strong_match=False。"""
        # "卡顿" 权重 2，不足 3
        result = classifier.classify("偶尔有点卡顿")
        assert result.primary_category == FaultCategory.HIGH_LATENCY
        assert result.strong_match is False

    def test_case_insensitive_matching(self, classifier: RuleBasedClassifier) -> None:
        """英文关键词匹配应不区分大小写（归一化后已小写）。"""
        result = classifier.classify("DNS RESOLUTION FAILURE")
        assert result.primary_category == FaultCategory.DNS_FAILURE
        assert result.strong_match is True

    def test_scores_contain_all_categories(self, classifier: RuleBasedClassifier) -> None:
        """分类结果应包含所有有规则的类别得分。"""
        result = classifier.classify("dns 解析失败")
        # 所有 10 个有规则的类别都应有得分记录
        assert len(result.scores) == 10
        for category in KEYWORD_RULES:
            assert category in result.scores

    def test_highest_score_wins(self, classifier: RuleBasedClassifier) -> None:
        """当多个类别有关键词命中时，应选择得分最高的类别。"""
        # "dns" 在 DNS_FAILURE 权重 3，"丢包" 在 PACKET_LOSS 权重 3
        # 但 "dns" 只有一个命中，"丢包" 中 "packet loss" 权重 3 也命中
        result = classifier.classify("dns 解析错误同时伴有丢包现象")
        # DNS_FAILURE: "dns":3 = 3, PACKET_LOSS: "丢包":3 = 3
        # 得分相同，应取第一个最大值（max 的行为是遇到 tie 取第一个）
        assert result.scores[FaultCategory.DNS_FAILURE] == 3.0
        assert result.scores[FaultCategory.PACKET_LOSS] == 3.0
        assert result.strong_match is True
