# src/generators/content/memory/style_analyzer.py
# 스타일 분석기 - 문서의 스타일을 분석하고 일관성을 유지

import logging
from typing import Dict, List, Optional
from src.models.section_models import StyleProfile, SectionContent

logger = logging.getLogger(__name__)


class StyleAnalyzer:
    """
    스타일 분석기

    문서의 스타일을 분석하고 일관성을 유지하는 역할
    현재는 기본적인 기능만 제공 (향후 확장 가능)
    """

    def __init__(self):
        """스타일 분석기 초기화"""
        self.logger = logger

    def analyze_section_style(self, section: SectionContent) -> Dict[str, any]:
        """
        섹션의 스타일을 분석

        Args:
            section: 분석할 섹션 콘텐츠

        Returns:
            스타일 분석 결과 딕셔너리
        """
        content = section.content

        # 기본적인 스타일 분석
        analysis = {
            "average_sentence_length": self._calculate_avg_sentence_length(content),
            "paragraph_count": content.count("\n\n") + 1,
            "tone_indicators": self._detect_tone_indicators(content),
            "complexity_score": self._calculate_complexity_score(content),
            "formality_level": self._detect_formality_level(content),
        }

        return analysis

    def update_style_profile(
        self, current_profile: StyleProfile, section_analysis: Dict[str, any]
    ) -> StyleProfile:
        """
        섹션 분석 결과를 바탕으로 스타일 프로필 업데이트

        Args:
            current_profile: 현재 스타일 프로필
            section_analysis: 섹션 스타일 분석 결과

        Returns:
            업데이트된 스타일 프로필
        """
        # 현재는 기본 프로필을 그대로 유지
        # 향후 더 정교한 스타일 학습 및 적응 로직 추가 가능

        return current_profile

    def _calculate_avg_sentence_length(self, content: str) -> float:
        """평균 문장 길이 계산"""
        sentences = [s.strip() for s in content.split(".") if s.strip()]
        if not sentences:
            return 0.0

        total_chars = sum(len(s) for s in sentences)
        return total_chars / len(sentences)

    def _detect_tone_indicators(self, content: str) -> List[str]:
        """톤 지시어 감지"""
        indicators = []

        # 전문적인 톤 지시어
        professional_words = ["중요합니다", "권장됩니다", "필수적입니다", "반드시"]
        if any(word in content for word in professional_words):
            indicators.append("professional")

        # 캐주얼한 톤 지시어
        casual_words = ["~하죠", "~네요", "정말", "쉽게"]
        if any(word in content for word in casual_words):
            indicators.append("casual")

        # 기술적인 톤 지시어
        technical_words = ["구현", "알고리즘", "시스템", "프로세스"]
        if any(word in content for word in technical_words):
            indicators.append("technical")

        return indicators

    def _calculate_complexity_score(self, content: str) -> float:
        """복잡도 점수 계산 (0.0-1.0)"""
        # 간단한 복잡도 측정
        factors = []

        # 문장 길이 기반
        avg_sentence_length = self._calculate_avg_sentence_length(content)
        length_complexity = min(avg_sentence_length / 100, 1.0)
        factors.append(length_complexity)

        # 전문 용어 밀도
        technical_terms = ["최적화", "알고리즘", "시스템", "프로세스", "전략", "방법론"]
        tech_count = sum(1 for term in technical_terms if term in content)
        tech_complexity = min(tech_count / 10, 1.0)
        factors.append(tech_complexity)

        # 평균 계산
        return sum(factors) / len(factors) if factors else 0.0

    def _detect_formality_level(self, content: str) -> str:
        """격식 수준 감지"""
        formal_indicators = ["입니다", "습니다", "됩니다", "있습니다"]
        informal_indicators = ["이에요", "해요", "~죠", "~네요"]

        formal_count = sum(1 for indicator in formal_indicators if indicator in content)
        informal_count = sum(
            1 for indicator in informal_indicators if indicator in content
        )

        if formal_count > informal_count * 2:
            return "formal"
        elif informal_count > formal_count:
            return "informal"
        else:
            return "neutral"
