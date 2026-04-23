from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest

from app.agents.meta_report.schemas import (
    MetaReportAgentInput,
    MetaReportOutput,
    MetaReportSessionInput,
)
from app.agents.meta_report.service import MetaReportAgentService
from app.infra.llm.errors import LLMNetworkError
from tests.agents._fakes import ScriptedGateway


def _session(session_id: str, created_at: datetime, pass_prob: int, reasons: list[dict]) -> MetaReportSessionInput:
    return MetaReportSessionInput(
        session_id=session_id,
        session_created_at=created_at,
        config_snapshot={"level": "senior", "style": "deep_dive"},
        report_payload={
            "pass_probability": pass_prob,
            "summary": f"session {session_id} summary",
            "reasons": reasons,
            "next_actions": ["整理上线项目的指标体系表"],
        },
    )


@pytest.fixture
def multi_session_input() -> MetaReportAgentInput:
    t0 = datetime(2026, 4, 1, 9, 0, tzinfo=timezone.utc)
    t1 = datetime(2026, 4, 8, 9, 0, tzinfo=timezone.utc)
    t2 = datetime(2026, 4, 15, 9, 0, tzinfo=timezone.utc)
    return MetaReportAgentInput(
        sessions=[
            _session(
                "s-01",
                t0,
                52,
                [
                    {
                        "aspect": "失败复盘",
                        "verdict": "weak",
                        "evidence_turn_index": 3,
                        "quote": "那次项目我主要是配合执行",
                    },
                    {
                        "aspect": "指标设计",
                        "verdict": "mixed",
                        "evidence_turn_index": 1,
                        "quote": "我们当时选了完成率作为北极星指标",
                    },
                ],
            ),
            _session(
                "s-02",
                t1,
                64,
                [
                    {
                        "aspect": "失败复盘",
                        "verdict": "weak",
                        "evidence_turn_index": 2,
                        "quote": "失败那次我更多是收拾残局",
                    },
                    {
                        "aspect": "指标设计",
                        "verdict": "solid",
                        "evidence_turn_index": 0,
                        "quote": "我会先写清楚北极星再拆反指标",
                    },
                ],
            ),
            _session(
                "s-03",
                t2,
                71,
                [
                    {
                        "aspect": "失败复盘",
                        "verdict": "mixed",
                        "evidence_turn_index": 4,
                        "quote": "这次我回去做了 5 Whys",
                    },
                ],
            ),
        ],
    )


@pytest.fixture
def single_session_input() -> MetaReportAgentInput:
    return MetaReportAgentInput(
        sessions=[
            _session(
                "s-only",
                datetime(2026, 4, 20, 9, 0, tzinfo=timezone.utc),
                58,
                [
                    {
                        "aspect": "指标设计",
                        "verdict": "mixed",
                        "evidence_turn_index": 0,
                        "quote": "北极星指标选得还行,但反指标没讲",
                    }
                ],
            )
        ]
    )


_MULTI_PAYLOAD = {
    "overall_trend_summary": (
        "你在最近三场面试里整体通过概率从 52 稳步提升到 71。"
        "指标设计维度从 mixed 提升到 solid;失败复盘依然是反复出现的短板,"
        "建议下一轮系统补强。"
    ),
    "recurring_weaknesses": [
        {
            "aspect": "失败复盘",
            "occurrence_count": 3,
            "session_ids": ["s-01", "s-02", "s-03"],
            "evidence_quotes": [
                "那次项目我主要是配合执行",
                "失败那次我更多是收拾残局",
            ],
        }
    ],
    "improvement_signals": [
        {
            "aspect": "指标设计",
            "from_verdict": "mixed",
            "to_verdict": "solid",
            "earlier_session_id": "s-01",
            "later_session_id": "s-02",
        }
    ],
    "pass_probability_series": [
        {
            "session_id": "s-01",
            "session_created_at": "2026-04-01T09:00:00+00:00",
            "pass_probability": 52,
        },
        {
            "session_id": "s-02",
            "session_created_at": "2026-04-08T09:00:00+00:00",
            "pass_probability": 64,
        },
        {
            "session_id": "s-03",
            "session_created_at": "2026-04-15T09:00:00+00:00",
            "pass_probability": 71,
        },
    ],
    "next_focus_areas": [
        {
            "aspect": "失败复盘",
            "reason": "连续三场均落在 weak/mixed,最近一场仍未抵达 solid",
            "suggested_prep": "挑一个上季度失败项目,写 5 Whys 根因链并量化损失",
        },
        {
            "aspect": "跨团队协作",
            "reason": "最近两场均未主动举例,存在盲点",
            "suggested_prep": "准备一段跨三个团队交付的具体案例,带上关键决策节点",
        },
        {
            "aspect": "指标设计",
            "reason": "已稳住 solid,但 counter metric 未讨论",
            "suggested_prep": "为当前岗位设计一组北极星 + 反指标配对并写好取舍理由",
        },
    ],
}


_SINGLE_PAYLOAD = {
    "overall_trend_summary": (
        "这一场你的整体通过概率落在 58,指标设计维度评为 mixed,"
        "北极星指标选得合理但反指标没覆盖。这是本场唯一的明确短板,"
        "先补这一点再考虑其他方向。"
    ),
    "recurring_weaknesses": [],
    "improvement_signals": [],
    "pass_probability_series": [
        {
            "session_id": "s-only",
            "session_created_at": "2026-04-20T09:00:00+00:00",
            "pass_probability": 58,
        }
    ],
    "next_focus_areas": [
        {
            "aspect": "指标设计",
            "reason": "本场 verdict 为 mixed,缺 counter metric 讨论",
            "suggested_prep": "为目标岗位写一组北极星 + 反指标,并明确取舍逻辑",
        },
        {
            "aspect": "量化证据",
            "reason": "本场作答未给出具体数字",
            "suggested_prep": "把最近两个项目的关键结果用数字量化到三位有效数字",
        },
        {
            "aspect": "失败复盘",
            "reason": "尚未覆盖到的关键维度",
            "suggested_prep": "准备一段 5 Whys 形式的失败项目复盘",
        },
    ],
}


async def test_meta_report_happy_cross_session(multi_session_input: MetaReportAgentInput) -> None:
    gateway = ScriptedGateway([json.dumps(_MULTI_PAYLOAD)])

    result = await MetaReportAgentService().run(multi_session_input, gateway)

    assert isinstance(result, MetaReportOutput)
    assert len(result.pass_probability_series) == 3
    assert [p.pass_probability for p in result.pass_probability_series] == [52, 64, 71]
    assert result.recurring_weaknesses[0].aspect == "失败复盘"
    assert result.recurring_weaknesses[0].occurrence_count >= 2
    assert result.improvement_signals[0].from_verdict == "mixed"
    assert result.improvement_signals[0].to_verdict == "solid"
    assert 3 <= len(result.next_focus_areas) <= 5
    assert gateway.calls == 1


async def test_meta_report_single_session_degrade(single_session_input: MetaReportAgentInput) -> None:
    # First attempt returns malformed JSON — Instructor retries and recovers.
    gateway = ScriptedGateway(["not-json", json.dumps(_SINGLE_PAYLOAD)])

    result = await MetaReportAgentService().run(single_session_input, gateway)

    assert result.recurring_weaknesses == []
    assert result.improvement_signals == []
    assert len(result.pass_probability_series) == 1
    assert result.pass_probability_series[0].session_id == "s-only"
    assert 3 <= len(result.next_focus_areas) <= 5
    assert gateway.calls == 2
    # Single-session retrospective voice: must not pretend we have a trend.
    assert "几次面试" not in result.overall_trend_summary


async def test_meta_report_propagates_network_error(
    multi_session_input: MetaReportAgentInput,
) -> None:
    gateway = ScriptedGateway([LLMNetworkError("offline")] * 3)

    with pytest.raises(LLMNetworkError):
        await MetaReportAgentService().run(multi_session_input, gateway)
