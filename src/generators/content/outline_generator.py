# -*- coding: utf-8 -*-
"""
아웃라인 생성기 - 키워드 전략 통합 버전
블로그 아웃라인을 JSON 형태로 생성하며, LSI/롱테일 키워드를 활용합니다.
"""

import logging
from typing import Dict, Any, Optional
import json
import re

from src.utils.config import load_config
from src.utils.llm_factory import LLMFactory, LLMConfig
from src.models.blog_models import BlogOutline, BlogSection, BlogMeta, KeywordStrategy
from src.generators.content.keyword_generator import KeywordGenerator


class OutlineGenerator:
    """블로그 아웃라인 생성을 위한 클래스"""

    def __init__(self):
        """OutlineGenerator 초기화"""
        self.logger = logging.getLogger(__name__)
        self.config = load_config()
        self.llm_config = self.config["llm"]
        self.llm = None
        self.keyword_generator = KeywordGenerator()
        self._initialize_llm()

    def _initialize_llm(self) -> None:
        """LLM 초기화"""
        try:
            factory = LLMFactory()

            # LLMConfig 객체 생성
            llm_config = LLMConfig(
                provider=self.llm_config["default_provider"],
                model=self.llm_config["openai_model"],
                temperature=self.llm_config["temperature"],
                max_tokens=1500,
            )

            self.llm = factory.create_llm(llm_config)
            self.logger.info(
                f"LLM 초기화 성공: {self.llm_config['default_provider']}/{self.llm_config['openai_model']}"
            )
            self.logger.info("OutlineGenerator 초기화 완료")
        except Exception as e:
            self.logger.error(f"LLM 초기화 실패: {e}")
            raise

    def generate_outline(self, keyword: str, title: str) -> BlogOutline:
        """키워드 전략을 포함한 블로그 아웃라인 생성"""
        self.logger.info(f"아웃라인 생성 시작: 키워드='{keyword}', 제목='{title}'")

        try:
            # 1단계: 키워드 전략 생성
            keyword_strategy = self.keyword_generator.generate_keyword_strategy(keyword)

            # 2단계: 아웃라인 생성 (키워드 전략 반영)
            outline_data = self._create_outline_with_strategy(
                keyword, title, keyword_strategy
            )

            # 3단계: BlogOutline 객체 생성
            outline = self._parse_outline_response(outline_data, keyword_strategy)

            self.logger.info(f"아웃라인 생성 성공: {len(outline.sections)}개 섹션")
            return outline

        except Exception as e:
            self.logger.error(f"아웃라인 생성 실패: {e}")
            return self._create_fallback_outline(keyword, title)

    def _create_outline_with_strategy(
        self, keyword: str, title: str, strategy: KeywordStrategy
    ) -> Dict[str, Any]:
        """키워드 전략을 반영한 아웃라인 생성"""

        # LSI 키워드들을 문자열로 변환
        lsi_keywords_str = ", ".join([lsi.keyword for lsi in strategy.lsi_keywords[:8]])
        longtail_keywords_str = ", ".join(
            [lt.phrase for lt in strategy.longtail_keywords[:5]]
        )
        variations_str = ", ".join(strategy.semantic_variations[:5])

        prompt = f"""
SEO 최적화된 블로그 아웃라인을 JSON 형식으로 생성해주세요.

**기본 정보:**
- 핵심 키워드: {keyword} (목표 빈도: {strategy.target_frequency}회)
- 블로그 제목: {title}
- 현재 날짜: 2025년 8월 (참고용, 최신 정보 반영 시에만 활용)

**키워드 전략:**
- LSI 키워드: {lsi_keywords_str}
- 롱테일 키워드: {longtail_keywords_str}
- 의미적 변형: {variations_str}

**중요 가이드라인:**
1. **개요 섹션 (첫 번째 섹션)**: 300-400자로 간결하게 작성 (너무 길면 독자가 이탈)
2. **키워드 사용법**:
   - 핵심 키워드 '{keyword}': 전체 콘텐츠에서 5-6회만 사용
   - LSI 키워드: 자연스럽게 분산 배치 
   - 롱테일 키워드: H2/H3 제목에 우선 활용
   - 의미적 변형: 본문에서 자연스럽게 활용
3. **섹션 구성**: 6개 섹션 (개요 → 시작하기 → 핵심방법 → 실무노하우 → 마무리 → FAQ)
4. **H3 개수**: 섹션에 따라 0-4개 (자유롭게 조정)

**중요: 제목은 반드시 주어진 제목을 그대로 사용하세요!**

**필수 JSON 스키마:**
```json
{{
  "title": "{title}",
  "sections": [
    {{
      "h2": "섹션 제목",
      "h3": ["하위섹션1", "하위섹션2"],
      "h4_map": {{"하위섹션1": ["세부항목1", "세부항목2"]}}
    }}
  ],
  "meta": {{
    "intent": "guide",
    "estimated_length": 3000,
    "target_keyword": "{keyword}",
    "seo_strategy": "키워드 전략 설명"
  }}
}}
```

**중요: 섹션 순서를 정확히 지켜주세요!**
**섹션별 세부 가이드:**
1. **개요**: 간단한 소개, 300-400자, H3 없음 또는 1개
2. **시작하기**: 기본 준비사항, 첫 단계 (H3: 2개)
3. **핵심 방법**: 기본 전략, 고급 기법, 실전 적용, 효과 측정 (H3: 4개)
4. **실무 노하우**: 흔한 실수, 문제 해결 (H3: 2개)
5. **마무리**: 요약 및 실행 방안, H3 없음
6. **FAQ**: 간결한 Q&A 형식, 400-500자, H3: 2개 (기초/고급)

LSI 키워드와 롱테일 키워드를 자연스럽게 제목에 활용하여 SEO 효과를 극대화하세요.
필요시에만 최신 트렌드와 정보 반영 (자연스럽게).
"""

        try:
            response = self.llm.invoke(prompt)
            content = response.content.strip()

            # JSON 파싱
            parsed_data = self._parse_json_response(content)

            # 키워드 검증
            self._validate_keyword_usage(parsed_data, keyword)

            return parsed_data

        except Exception as e:
            self.logger.error(f"아웃라인 생성 중 오류: {e}")
            raise

    def _parse_json_response(self, content: str) -> Dict[str, Any]:
        """LLM 응답에서 JSON 파싱"""
        try:
            # 마크다운 코드 블록 제거
            json_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", content, re.DOTALL)
            if json_match:
                content = json_match.group(1).strip()

            # JSON 파싱
            return json.loads(content)

        except json.JSONDecodeError as e:
            self.logger.warning(f"JSON 파싱 오류: {e}")
            raise

    def _validate_keyword_usage(
        self, outline_data: Dict[str, Any], keyword: str
    ) -> None:
        """키워드 사용 빈도 검증"""
        try:
            sections = outline_data.get("sections", [])
            keyword_count = 0

            for section in sections:
                h2_title = section.get("h2", "")
                if keyword in h2_title:
                    keyword_count += 1

            if keyword_count == 0:
                self.logger.warning(f"H2 제목에 키워드 '{keyword}' 미포함")

        except Exception as e:
            self.logger.warning(f"키워드 검증 중 오류: {e}")

    def _parse_outline_response(
        self, outline_data: Dict[str, Any], strategy: KeywordStrategy
    ) -> BlogOutline:
        """JSON 응답을 BlogOutline 객체로 변환"""
        try:
            # 섹션 파싱
            sections = []
            for section_data in outline_data.get("sections", []):
                section = BlogSection(
                    h2=section_data.get("h2", ""),
                    h3=section_data.get("h3", []),
                    h4_map=section_data.get("h4_map", {}),
                )
                sections.append(section)

            # 메타데이터 파싱
            meta_data = outline_data.get("meta", {})
            meta = BlogMeta(
                intent=meta_data.get("intent", "guide"),
                estimated_length=self._parse_estimated_length(meta_data),
                target_keyword=meta_data.get(
                    "target_keyword", strategy.primary_keyword
                ),
                seo_strategy=meta_data.get("seo_strategy", "키워드 최적화 전략"),
                keyword_strategy=strategy,  # 키워드 전략 포함
            )

            # BlogOutline 생성
            outline = BlogOutline(
                title=outline_data.get("title", ""),
                sections=sections,
                meta=meta,
            )

            return outline

        except Exception as e:
            self.logger.error(f"아웃라인 파싱 실패: {e}")
            raise

    def _parse_estimated_length(self, meta_data: Dict[str, Any]) -> int:
        """예상 길이 파싱 (여러 필드명 지원)"""
        try:
            # 다양한 필드명 시도
            for field in ["estimated_length", "est_length", "length"]:
                if field in meta_data:
                    return int(meta_data[field])
            return 3000  # 기본값
        except (ValueError, TypeError):
            return 3000

    def _create_fallback_outline(self, keyword: str, title: str) -> BlogOutline:
        """폴백 아웃라인 생성"""
        self.logger.warning("폴백 아웃라인 생성")

        # 기본 키워드 전략 생성
        fallback_strategy = KeywordStrategy(
            primary_keyword=keyword,
            target_frequency=6,
            lsi_keywords=[],
            longtail_keywords=[],
            semantic_variations=[keyword],
        )

        # 기본 섹션들 생성
        sections = [
            BlogSection(h2=f"{keyword} 개요", h3=[], h4_map={}),
            BlogSection(
                h2=f"{keyword} 시작하기", h3=["기본 준비사항", "첫 단계"], h4_map={}
            ),
            BlogSection(
                h2=f"{keyword} 핵심 방법",
                h3=["기본 전략", "고급 기법", "실전 적용", "효과 측정"],
                h4_map={},
            ),
            BlogSection(
                h2=f"{keyword} 실무 노하우", h3=["흔한 실수", "문제 해결"], h4_map={}
            ),
            BlogSection(h2="자주 묻는 질문", h3=["기초 FAQ", "고급 FAQ"], h4_map={}),
            BlogSection(h2="마무리", h3=[], h4_map={}),
        ]

        meta = BlogMeta(
            intent="guide",
            estimated_length=3000,
            target_keyword=keyword,
            seo_strategy="기본 SEO 최적화",
            keyword_strategy=fallback_strategy,
        )

        return BlogOutline(title=title, sections=sections, meta=meta)
