"""关键词匹配规则库 — Module E Step 21.

定义各故障分类的关键词及其权重。
"""

from __future__ import annotations

from nettriage.schemas.enums import FaultCategory

# 关键词规则：{分类: {关键词: 权重}}
KEYWORD_RULES: dict[FaultCategory, dict[str, int]] = {
    FaultCategory.DNS_FAILURE: {
        "dns": 3,
        "域名解析": 3,
        "无法解析": 2,
        "能ping ip": 3,
    },
    FaultCategory.AUTH_FAILURE: {
        "认证失败": 3,
        "pppoe": 3,
        "radius": 3,
        "账号密码": 2,
    },
    FaultCategory.WEAK_SIGNAL: {
        "信号弱": 3,
        "rssi": 3,
        "sinr": 3,
        "wifi弱": 2,
        "wi-fi弱": 2,
    },
    FaultCategory.PACKET_LOSS: {
        "丢包": 3,
        "packet loss": 3,
        "ping丢": 2,
        "抖动": 2,
    },
    FaultCategory.HIGH_LATENCY: {
        "延迟高": 3,
        "时延高": 3,
        "ping高": 2,
        "卡顿": 2,
    },
    FaultCategory.DROPPED_CONNECTION: {
        "掉线": 3,
        "断开": 2,
        "频繁中断": 3,
    },
    FaultCategory.CONFIG_ERROR: {
        "vlan": 3,
        "acl": 3,
        "nat": 3,
        "路由配置": 2,
        "dhcp": 2,
    },
    FaultCategory.DEVICE_FAILURE: {
        "光猫故障": 3,
        "路由器故障": 3,
        "端口故障": 2,
        "硬件告警": 3,
    },
    FaultCategory.SERVICE_OUTAGE: {
        "大面积": 3,
        "区域故障": 3,
        "全站不可用": 3,
        "出口异常": 2,
    },
    FaultCategory.BANDWIDTH_DEGRADATION: {
        "下载慢": 3,
        "速率低": 3,
        "带宽不达标": 3,
    },
}
