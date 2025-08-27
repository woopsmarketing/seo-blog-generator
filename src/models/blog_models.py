# src/models/blog_models.py
# SEO 블로그 생성 파이프라인을 위한 핵심 데이터 모델들

from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from datetime import datetime


class BlogSection(BaseModel):
    """블로그 섹션 구조 정의"""

    h2: str = Field(..., description="H2 섹션 제목")
    h3: List[str] = Field(default=[], description="H3 하위 섹션 목록")
    h4_map: Dict[str, List[str]] = Field(
        default={}, description="H3별 H4 하위 섹션 매핑"
    )


class LSIKeyword(BaseModel):
    """LSI 키워드 정의"""

    keyword: str = Field(..., description="LSI 키워드")
    relevance_score: float = Field(..., description="연관성 점수 (0.0-1.0)")
    context: str = Field(..., description="사용 맥락")


class LongTailKeyword(BaseModel):
    """롱테일 키워드 정의"""

    phrase: str = Field(..., description="롱테일 키워드 구문")
    search_intent: str = Field(..., description="검색 의도 유형")
    difficulty: str = Field(..., description="경쟁 난이도 (low/medium/high)")


class KeywordStrategy(BaseModel):
    """키워드 전략 정의"""

    primary_keyword: str = Field(..., description="핵심 키워드")
    target_frequency: int = Field(default=6, description="핵심 키워드 목표 빈도")
    lsi_keywords: List[LSIKeyword] = Field(default=[], description="LSI 키워드 목록")
    longtail_keywords: List[LongTailKeyword] = Field(
        default=[], description="롱테일 키워드 목록"
    )
    semantic_variations: List[str] = Field(default=[], description="의미적 변형 표현")


class BlogMeta(BaseModel):
    """블로그 메타데이터"""

    intent: str = Field(..., description="글의 의도 (guide/checklist/compare 등)")
    estimated_length: int = Field(..., description="예상 글자 수")
    target_keyword: str = Field(..., description="타겟 키워드")
    seo_strategy: str = Field(..., description="SEO 전략")
    keyword_strategy: Optional[KeywordStrategy] = Field(
        default=None, description="키워드 전략"
    )


class BlogOutline(BaseModel):
    """블로그 아웃라인 구조"""

    title: str = Field(..., description="블로그 제목")
    sections: List[BlogSection] = Field(..., description="섹션 목록")
    meta: BlogMeta = Field(..., description="메타데이터")


class BlogState(BaseModel):
    """블로그 생성 상태 관리"""

    keyword: str = Field(..., description="입력 키워드")
    title: Optional[str] = Field(default=None, description="생성된 제목")
    outline: Optional[BlogOutline] = Field(default=None, description="생성된 아웃라인")
    sections: Dict[str, str] = Field(default={}, description="생성된 섹션 콘텐츠")
    metadata: Dict = Field(default={}, description="추가 메타데이터")

    def add_section(self, section_id: str, content: str) -> None:
        """섹션 추가"""
        self.sections[section_id] = content

    def get_section(self, section_id: str) -> Optional[str]:
        """섹션 조회"""
        return self.sections.get(section_id)

    def get_completion_rate(self) -> float:
        """완성률 계산"""
        if not self.outline:
            return 0.0
        total_sections = len(self.outline.sections)
        completed_sections = len(self.sections)
        return completed_sections / total_sections if total_sections > 0 else 0.0
