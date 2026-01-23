"""페르소나 단위 테스트"""

import pytest
from app.services.claude import (
    PersonaType,
    detect_persona,
    get_persona,
    get_system_prompt,
    PERSONAS,
)


class TestDetectPersona:
    """페르소나 감지 테스트"""

    def test_detect_mallangi_with_suffix_a(self):
        """'말랑아' 호출 감지"""
        persona_type, prompt = detect_persona("말랑아 오늘 뭐해?")
        assert persona_type == PersonaType.MALLANGI
        assert prompt == "오늘 뭐해?"

    def test_detect_mallangi_with_suffix_iya(self):
        """'말랑이야' 호출 감지"""
        persona_type, prompt = detect_persona("말랑이야 안녕")
        assert persona_type == PersonaType.MALLANGI
        assert prompt == "안녕"

    def test_detect_lupin(self):
        """'루팡아' 호출 감지"""
        persona_type, prompt = detect_persona("루팡아 이거 알아?")
        assert persona_type == PersonaType.LUPIN
        assert prompt == "이거 알아?"

    def test_detect_pudding(self):
        """'푸딩아' 호출 감지"""
        persona_type, prompt = detect_persona("푸딩아 배고파")
        assert persona_type == PersonaType.PUDDING
        assert prompt == "배고파"

    def test_detect_michael(self):
        """'마이콜아' 호출 감지"""
        persona_type, prompt = detect_persona("마이콜아 영어로 뭐야?")
        assert persona_type == PersonaType.MICHAEL
        assert prompt == "영어로 뭐야?"

    def test_detect_legacy_ai_trigger(self):
        """'에이아이야' 레거시 호출 → 말랑이로 매핑"""
        persona_type, prompt = detect_persona("에이아이야 테스트")
        assert persona_type == PersonaType.MALLANGI
        assert prompt == "테스트"

    def test_no_trigger_detected(self):
        """호출어 없는 메시지"""
        persona_type, prompt = detect_persona("그냥 일반 메시지")
        assert persona_type is None
        assert prompt == "그냥 일반 메시지"

    def test_empty_message(self):
        """빈 메시지"""
        persona_type, prompt = detect_persona("")
        assert persona_type is None
        assert prompt == ""

    def test_legacy_trigger_without_space(self):
        """레거시 트리거 공백 없이 바로 연결 ('에이아이안녕')"""
        persona_type, prompt = detect_persona("에이아이안녕")
        assert persona_type == PersonaType.MALLANGI
        assert prompt == "안녕"

    def test_legacy_trigger_suffix_without_space(self):
        """레거시 트리거 접미사 후 공백 없이 연결 ('에이아이야안녕')"""
        persona_type, prompt = detect_persona("에이아이야안녕")
        assert persona_type == PersonaType.MALLANGI
        assert prompt == "안녕"

    def test_legacy_trigger_suffix_a_without_space(self):
        """레거시 트리거 '아' 접미사 후 공백 없이 연결"""
        persona_type, prompt = detect_persona("에이아이아안녕")
        assert persona_type == PersonaType.MALLANGI
        assert prompt == "안녕"


class TestGetPersona:
    """페르소나 조회 테스트"""

    def test_get_mallangi_persona(self):
        """말랑이 페르소나 조회"""
        persona = get_persona(PersonaType.MALLANGI)
        assert persona.name == "mallangi"
        assert persona.display_name == "말랑이"

    def test_get_lupin_persona(self):
        """루팡 페르소나 조회"""
        persona = get_persona(PersonaType.LUPIN)
        assert persona.name == "lupin"
        assert persona.display_name == "루팡"

    def test_all_personas_have_prompt(self):
        """모든 페르소나에 프롬프트 존재"""
        for persona_type in PersonaType:
            prompt = get_system_prompt(persona_type)
            assert len(prompt) > 0
            # 달력이는 JSON 전용이므로 공통 규칙이 없음
            if persona_type != PersonaType.CALENDAR:
                assert "공통 규칙" in prompt
