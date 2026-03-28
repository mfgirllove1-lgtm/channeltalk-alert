"""
테스트: 에스컬레이션 탐지 로직
"""
import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.detector import detect


def test_normal_message():
    result = detect("배송이 언제 오나요?")
    assert result.should_escalate is False
    assert result.level == "NORMAL"


def test_legal_threat():
    result = detect("이거 해결 안 되면 소비자원에 신고할게요")
    assert result.should_escalate is True
    assert result.level == "CRITICAL"
    assert "소비자원" in result.matched_keywords


def test_media_threat():
    result = detect("SNS 올린다 진짜로")
    assert result.should_escalate is True
    assert result.level == "CRITICAL"


def test_strong_complaint():
    result = detect("환불 안 해주면 가만 안 있을게요 사기야 진짜")
    assert result.should_escalate is True
    assert result.level in ("CRITICAL", "HIGH")


def test_agent_complaint():
    result = detect("상담사가 너무 불친절해요 태도가 왜 그래요")
    assert result.should_escalate is True
    assert result.level == "HIGH"


def test_personal_info():
    result = detect("제 개인정보가 유출된 것 같아요")
    assert result.should_escalate is True
    assert result.level == "CRITICAL"


def test_multiple_rules():
    result = detect("이거 소송 걸고 뉴스에도 제보할 거예요")
    assert result.should_escalate is True
    assert result.level == "CRITICAL"
    assert len(result.triggered_rules) >= 2


def test_empty_message():
    result = detect("")
    assert result.should_escalate is False


def test_preview_truncation():
    long_text = "테스트 " * 100
    result = detect(long_text)
    assert len(result.message_preview) <= 130
