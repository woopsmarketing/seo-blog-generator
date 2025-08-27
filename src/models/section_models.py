# src/models/section_models.py
# 섹션 콘텐츠 생성을 위한 데이터 모델

from typing import Dict, List, Optional, Any
from datetime import datetime
from pydantic import BaseModel, Field


class KeyFact(BaseModel):
    """문서에서 추출된 핵심 사실"""

    fact: str = Field(..., description="핵심 사실 내용")
    section_id: str = Field(..., description="사실이 언급된 섹션 ID")
    confidence: float = Field(default=1.0, description="사실의 신뢰도 (0.0-1.0)")
    related_terms: List[str] = Field(default_factory=list, description="관련 용어들")


class StyleProfile(BaseModel):
    """문서의 스타일 프로필"""

    tone: str = Field(
        default="professional", description="문서 톤 (professional, casual, technical)"
    )
    complexity_level: str = Field(default="intermediate", description="복잡도 수준")
    sentence_length: str = Field(default="medium", description="문장 길이 선호도")
    technical_depth: str = Field(default="moderate", description="기술적 깊이")
    examples_style: str = Field(default="practical", description="예시 스타일")


class SectionContent(BaseModel):
    """생성된 섹션 콘텐츠"""

    section_id: str = Field(..., description="섹션 ID (예: '1', '2.1')")
    title: str = Field(..., description="섹션 제목")
    content: str = Field(..., description="생성된 콘텐츠 (300-500자)")
    word_count: int = Field(..., description="단어 수")
    key_points: List[str] = Field(
        default_factory=list, description="섹션의 핵심 포인트들"
    )
    mentioned_facts: List[str] = Field(
        default_factory=list, description="언급된 주요 사실들"
    )
    generated_at: datetime = Field(
        default_factory=datetime.now, description="생성 시간"
    )


class DocumentMemory(BaseModel):
    """문서 전체 컨텍스트를 관리하는 메모리"""

    # 기본 문서 정보
    document_title: str = Field(..., description="문서 제목")
    target_keyword: str = Field(..., description="타겟 키워드")
    document_intent: str = Field(
        ..., description="문서 의도 (guide, tutorial, review 등)"
    )
    target_audience: str = Field(default="general", description="타겟 독자")

    # 생성된 콘텐츠
    generated_sections: List[SectionContent] = Field(
        default_factory=list, description="생성된 섹션들"
    )

    # 축적된 지식
    key_facts: List[KeyFact] = Field(
        default_factory=list, description="문서의 핵심 사실들"
    )
    terminology: Dict[str, str] = Field(
        default_factory=dict, description="용어 정의 (용어: 정의)"
    )

    # 스타일 일관성
    style_profile: StyleProfile = Field(
        default_factory=StyleProfile, description="문서 스타일"
    )

    # 메타데이터
    total_word_count: int = Field(default=0, description="전체 단어 수")
    last_updated: datetime = Field(
        default_factory=datetime.now, description="마지막 업데이트 시간"
    )

    def add_section(self, section: SectionContent) -> None:
        """새 섹션을 메모리에 추가"""
        self.generated_sections.append(section)
        self.total_word_count += section.word_count
        self.last_updated = datetime.now()

    def add_fact(self, fact: KeyFact) -> None:
        """새 사실을 메모리에 추가"""
        # 중복 사실 확인
        existing_facts = [f.fact for f in self.key_facts]
        if fact.fact not in existing_facts:
            self.key_facts.append(fact)

    def add_terminology(self, term: str, definition: str) -> None:
        """용어 정의 추가"""
        self.terminology[term] = definition

    def get_previous_sections_summary(self, limit: int = 3) -> str:
        """최근 생성된 섹션들의 요약 반환"""
        if not self.generated_sections:
            return "이전에 생성된 섹션이 없습니다."

        recent_sections = self.generated_sections[-limit:]
        summary_parts = []

        for section in recent_sections:
            summary_parts.append(f"[{section.title}]: {', '.join(section.key_points)}")

        return " | ".join(summary_parts)

    def get_accumulated_facts(self) -> str:
        """축적된 사실들을 문자열로 반환"""
        if not self.key_facts:
            return "축적된 사실이 없습니다."

        facts_list = [f"- {fact.fact}" for fact in self.key_facts]
        return "\n".join(facts_list)

    def get_terminology_context(self) -> str:
        """용어 정의들을 문자열로 반환"""
        if not self.terminology:
            return "정의된 용어가 없습니다."

        terms_list = [
            f"- {term}: {definition}" for term, definition in self.terminology.items()
        ]
        return "\n".join(terms_list)


class SectionGenerationOptions(BaseModel):
    """섹션 생성 옵션"""

    target_length: int = Field(default=400, description="목표 길이 (글자 수)")
    min_length: int = Field(default=300, description="최소 길이")
    max_length: int = Field(default=500, description="최대 길이")
    include_examples: bool = Field(default=True, description="예시 포함 여부")
    include_actionable_tips: bool = Field(
        default=True, description="실행 가능한 팁 포함 여부"
    )
    tone: str = Field(default="professional", description="톤앤매너")
    use_memory_context: bool = Field(
        default=True, description="메모리 컨텍스트 사용 여부"
    )


class SectionGenerationResult(BaseModel):
    """섹션 생성 결과"""

    section_content: SectionContent = Field(..., description="생성된 섹션 콘텐츠")
    extracted_facts: List[KeyFact] = Field(
        default_factory=list, description="추출된 새로운 사실들"
    )
    new_terminology: Dict[str, str] = Field(
        default_factory=dict, description="새로 정의된 용어들"
    )
    generation_time: float = Field(..., description="생성 소요 시간 (초)")
    token_usage: Dict[str, int] = Field(default_factory=dict, description="토큰 사용량")
    success: bool = Field(default=True, description="생성 성공 여부")
    error_message: Optional[str] = Field(default=None, description="오류 메시지")
