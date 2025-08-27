# -*- coding: utf-8 -*-
"""
키워드 전략 생성기
- LSI 키워드 생성
- 롱테일 키워드 생성
- 의미적 변형 표현 생성
- 키워드 밀도 최적화
"""

import logging
from typing import List, Dict, Any, Optional
import json
import re

from src.utils.config import load_config
from src.utils.llm_factory import LLMFactory, LLMConfig
from src.models.blog_models import KeywordStrategy, LSIKeyword, LongTailKeyword


class KeywordGenerator:
    """키워드 전략 생성을 위한 클래스"""

    def __init__(self):
        """KeywordGenerator 초기화"""
        self.logger = logging.getLogger(__name__)
        self.config = load_config()
        self.llm_config = self.config["llm"]
        self.llm = None
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
                max_tokens=1000,
            )

            self.llm = factory.create_llm(llm_config)
            self.logger.info(
                f"키워드 생성기 LLM 초기화 완료: {self.llm_config['default_provider']}/{self.llm_config['openai_model']}"
            )
        except Exception as e:
            self.logger.error(f"LLM 초기화 실패: {e}")
            raise

    def generate_keyword_strategy(
        self, primary_keyword: str, context: str = "블로그 콘텐츠"
    ) -> KeywordStrategy:
        """핵심 키워드를 기반으로 전체 키워드 전략 생성"""
        self.logger.info(f"키워드 전략 생성 시작: '{primary_keyword}'")

        try:
            # LSI 키워드 생성
            lsi_keywords = self._generate_lsi_keywords(primary_keyword, context)

            # 롱테일 키워드 생성
            longtail_keywords = self._generate_longtail_keywords(
                primary_keyword, context
            )

            # 의미적 변형 표현 생성
            semantic_variations = self._generate_semantic_variations(primary_keyword)

            strategy = KeywordStrategy(
                primary_keyword=primary_keyword,
                target_frequency=6,  # 핵심 키워드는 5-6개로 제한
                lsi_keywords=lsi_keywords,
                longtail_keywords=longtail_keywords,
                semantic_variations=semantic_variations,
            )

            self.logger.info(
                f"키워드 전략 생성 완료: LSI {len(lsi_keywords)}개, 롱테일 {len(longtail_keywords)}개"
            )
            return strategy

        except Exception as e:
            self.logger.error(f"키워드 전략 생성 실패: {e}")
            return self._create_fallback_strategy(primary_keyword)

    def _generate_lsi_keywords(
        self, primary_keyword: str, context: str
    ) -> List[LSIKeyword]:
        """LSI(Latent Semantic Indexing) 키워드 생성"""
        prompt = f"""
{primary_keyword}와 의미적으로 관련된 LSI 키워드를 생성해주세요.

**요구사항:**
- 핵심 키워드: {primary_keyword}
- 컨텍스트: {context}
- LSI 키워드 8-12개 생성
- 각 키워드의 연관성과 사용 맥락 제공

**JSON 형식으로 응답:**
```json
{{
  "lsi_keywords": [
    {{
      "keyword": "관련 키워드",
      "relevance_score": 0.9,
      "context": "어떤 맥락에서 사용할지"
    }}
  ]
}}
```

**LSI 키워드 예시:**
- 동의어/유의어
- 관련 기술/도구
- 상위/하위 개념
- 연관 프로세스
- 관련 문제/솔루션

연관성 점수는 0.0-1.0 사이로 설정하세요.
"""

        try:
            response = self.llm.invoke(prompt)
            content = response.content.strip()

            # JSON 파싱
            parsed_data = self._parse_json_response(content)

            lsi_keywords = []
            for item in parsed_data.get("lsi_keywords", []):
                lsi_keywords.append(
                    LSIKeyword(
                        keyword=item["keyword"],
                        relevance_score=float(item["relevance_score"]),
                        context=item["context"],
                    )
                )

            return lsi_keywords[:12]  # 최대 12개로 제한

        except Exception as e:
            self.logger.warning(f"LSI 키워드 생성 실패: {e}")
            return self._create_fallback_lsi_keywords(primary_keyword)

    def _generate_longtail_keywords(
        self, primary_keyword: str, context: str
    ) -> List[LongTailKeyword]:
        """롱테일 키워드 생성"""
        prompt = f"""
{primary_keyword}와 관련된 롱테일 키워드를 생성해주세요.

**요구사항:**
- 핵심 키워드: {primary_keyword}
- 컨텍스트: {context}
- 롱테일 키워드 6-10개 생성
- 각 키워드의 검색 의도와 경쟁 난이도 분석

**JSON 형식으로 응답:**
```json
{{
  "longtail_keywords": [
    {{
      "phrase": "구체적인 롱테일 키워드 구문",
      "search_intent": "informational|commercial|navigational|transactional",
      "difficulty": "low|medium|high"
    }}
  ]
}}
```

**롱테일 키워드 특징:**
- 3-5개 단어로 구성된 구체적인 검색어
- "어떻게", "방법", "가이드", "비교", "추천" 등 포함
- 사용자의 구체적인 니즈 반영
- 상대적으로 경쟁이 적은 키워드

검색 의도 유형:
- informational: 정보 탐색
- commercial: 구매 전 조사
- navigational: 특정 사이트 찾기
- transactional: 구매/행동 의도
"""

        try:
            response = self.llm.invoke(prompt)
            content = response.content.strip()

            # JSON 파싱
            parsed_data = self._parse_json_response(content)

            longtail_keywords = []
            for item in parsed_data.get("longtail_keywords", []):
                longtail_keywords.append(
                    LongTailKeyword(
                        phrase=item["phrase"],
                        search_intent=item["search_intent"],
                        difficulty=item["difficulty"],
                    )
                )

            return longtail_keywords[:10]  # 최대 10개로 제한

        except Exception as e:
            self.logger.warning(f"롱테일 키워드 생성 실패: {e}")
            return self._create_fallback_longtail_keywords(primary_keyword)

    def _generate_semantic_variations(self, primary_keyword: str) -> List[str]:
        """의미적 변형 표현 생성"""
        prompt = f"""
{primary_keyword}의 자연스러운 의미적 변형 표현을 생성해주세요.

**요구사항:**
- 핵심 키워드: {primary_keyword}
- 자연스러운 변형 표현 5-8개 생성
- 의미는 동일하지만 표현이 다른 구문들

**JSON 형식으로 응답:**
```json
{{
  "variations": [
    "자연스러운 변형 표현 1",
    "자연스러운 변형 표현 2"
  ]
}}
```

**변형 표현 예시:**
- 어순 변경: "앱 개발 효율" → "효율적인 앱 개발"
- 조사 변경: "의 중요성" → "이 중요한 이유"
- 동의어 활용: "로드맵" → "가이드", "방법론"
- 형태 변경: "효율 로드맵" → "효율화 방안"

자연스럽고 읽기 좋은 표현으로 생성하세요.
"""

        try:
            response = self.llm.invoke(prompt)
            content = response.content.strip()

            # JSON 파싱
            parsed_data = self._parse_json_response(content)

            variations = parsed_data.get("variations", [])
            return variations[:8]  # 최대 8개로 제한

        except Exception as e:
            self.logger.warning(f"의미적 변형 표현 생성 실패: {e}")
            return self._create_fallback_variations(primary_keyword)

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
            self.logger.warning(f"JSON 파싱 실패: {e}")
            # 간단한 정규식으로 재시도
            return self._fallback_json_parse(content)

    def _fallback_json_parse(self, content: str) -> Dict[str, Any]:
        """JSON 파싱 실패 시 폴백 파싱"""
        try:
            # 기본 구조 반환
            return {"keywords": [], "variations": []}
        except Exception:
            return {}

    def _create_fallback_strategy(self, primary_keyword: str) -> KeywordStrategy:
        """폴백 키워드 전략 생성"""
        return KeywordStrategy(
            primary_keyword=primary_keyword,
            target_frequency=6,
            lsi_keywords=self._create_fallback_lsi_keywords(primary_keyword),
            longtail_keywords=self._create_fallback_longtail_keywords(primary_keyword),
            semantic_variations=self._create_fallback_variations(primary_keyword),
        )

    def _create_fallback_lsi_keywords(self, primary_keyword: str) -> List[LSIKeyword]:
        """폴백 LSI 키워드 생성"""
        fallback_keywords = [
            LSIKeyword(keyword="개발", relevance_score=0.8, context="기술 개발"),
            LSIKeyword(keyword="효율성", relevance_score=0.9, context="성능 향상"),
            LSIKeyword(keyword="방법", relevance_score=0.7, context="실행 방안"),
        ]
        return fallback_keywords

    def _create_fallback_longtail_keywords(
        self, primary_keyword: str
    ) -> List[LongTailKeyword]:
        """폴백 롱테일 키워드 생성"""
        fallback_longtails = [
            LongTailKeyword(
                phrase=f"{primary_keyword} 시작하는 방법",
                search_intent="informational",
                difficulty="low",
            ),
            LongTailKeyword(
                phrase=f"{primary_keyword} 완벽 가이드",
                search_intent="informational",
                difficulty="medium",
            ),
        ]
        return fallback_longtails

    def _create_fallback_variations(self, primary_keyword: str) -> List[str]:
        """폴백 의미적 변형 표현 생성"""
        return [
            primary_keyword,
            f"{primary_keyword} 방법",
            f"효과적인 {primary_keyword}",
        ]
