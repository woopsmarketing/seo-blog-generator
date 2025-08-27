# src/generators/content/memory/fact_tracker.py
# 사실 추적 시스템 - 콘텐츠에서 핵심 사실을 추출하고 관리

import logging
import re
from typing import List, Dict, Set, Optional
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage

from src.models.section_models import KeyFact, SectionContent
from src.utils.config import load_config, get_api_key
from src.utils.llm_factory import LLMFactory, LLMConfig

logger = logging.getLogger(__name__)


class FactTracker:
    """사실 추적기 - 생성된 콘텐츠에서 핵심 사실을 자동으로 추출하고 관리"""

    def __init__(self, config: Optional[Dict] = None):
        """
        사실 추적기 초기화

        Args:
            config: LLM 설정 (기본값: None, 자동 로드)
        """
        self.config = config or load_config()
        self.llm = None
        self.logger = logger
        self._initialize_llm()

    def _initialize_llm(self) -> None:
        """LLM 초기화"""
        try:
            llm_config = LLMConfig(
                provider=self.config["llm"]["default_provider"],
                model=self.config["llm"]["openai_model"],
                temperature=0.3,  # 정확한 사실 추출을 위해 낮은 온도
                max_tokens=800,
            )

            factory = LLMFactory()
            self.llm = factory.create_llm(llm_config)
            self.logger.info(
                f"사실 추적기 LLM 초기화 완료: {llm_config.provider}/{llm_config.model}"
            )

        except Exception as e:
            self.logger.error(f"LLM 초기화 실패: {e}")
            raise

    def extract_facts_from_content(
        self,
        section: SectionContent,
        keyword: str,
        existing_facts: List[KeyFact] = None,
    ) -> List[KeyFact]:
        """
        섹션 콘텐츠에서 핵심 사실들을 추출

        Args:
            section: 분석할 섹션 콘텐츠
            keyword: 문서의 타겟 키워드
            existing_facts: 기존에 추출된 사실들 (중복 방지용)

        Returns:
            추출된 핵심 사실들의 리스트
        """
        if not self.llm:
            self.logger.warning(
                "LLM이 초기화되지 않았습니다. 빈 사실 목록을 반환합니다."
            )
            return []

        try:
            # 기존 사실들을 문자열로 변환 (중복 방지용)
            existing_facts_text = ""
            if existing_facts:
                existing_facts_list = [f"- {fact.fact}" for fact in existing_facts]
                existing_facts_text = "\n".join(existing_facts_list)

            # 사실 추출 프롬프트 생성
            prompt = self._create_fact_extraction_prompt(
                section, keyword, existing_facts_text
            )

            # LLM을 통한 사실 추출
            messages = [
                SystemMessage(
                    content="당신은 블로그 콘텐츠에서 핵심 사실을 정확하게 추출하는 전문가입니다."
                ),
                HumanMessage(content=prompt),
            ]

            response = self.llm.invoke(messages)

            # 응답에서 사실들 파싱
            extracted_facts = self._parse_facts_response(
                response.content, section.section_id
            )

            self.logger.info(
                f"섹션 {section.section_id}에서 {len(extracted_facts)}개의 사실 추출됨"
            )
            return extracted_facts

        except Exception as e:
            self.logger.error(f"사실 추출 실패 (섹션 {section.section_id}): {e}")
            return []

    def extract_terminology_from_content(
        self, section: SectionContent, keyword: str
    ) -> Dict[str, str]:
        """
        섹션 콘텐츠에서 전문 용어와 정의를 추출

        Args:
            section: 분석할 섹션 콘텐츠
            keyword: 문서의 타겟 키워드

        Returns:
            용어 정의 딕셔너리 (용어: 정의)
        """
        if not self.llm:
            self.logger.warning(
                "LLM이 초기화되지 않았습니다. 빈 용어 사전을 반환합니다."
            )
            return {}

        try:
            # 용어 추출 프롬프트 생성
            prompt = self._create_terminology_extraction_prompt(section, keyword)

            # LLM을 통한 용어 추출
            messages = [
                SystemMessage(
                    content="당신은 전문 용어를 정확하게 추출하고 정의하는 전문가입니다."
                ),
                HumanMessage(content=prompt),
            ]

            response = self.llm.invoke(messages)

            # 응답에서 용어들 파싱
            terminology = self._parse_terminology_response(response.content)

            self.logger.info(
                f"섹션 {section.section_id}에서 {len(terminology)}개의 용어 추출됨"
            )
            return terminology

        except Exception as e:
            self.logger.error(f"용어 추출 실패 (섹션 {section.section_id}): {e}")
            return {}

    def validate_fact_consistency(
        self, new_facts: List[KeyFact], existing_facts: List[KeyFact]
    ) -> List[Dict[str, str]]:
        """
        새로운 사실들이 기존 사실들과 일관성이 있는지 검증

        Args:
            new_facts: 새로 추출된 사실들
            existing_facts: 기존 사실들

        Returns:
            일관성 문제가 있는 사실들의 정보 리스트
        """
        inconsistencies = []

        if not new_facts or not existing_facts:
            return inconsistencies

        # 간단한 키워드 기반 일관성 검사
        for new_fact in new_facts:
            for existing_fact in existing_facts:
                # 비슷한 주제를 다루는 사실들 간의 충돌 검사
                if self._facts_potentially_conflict(new_fact, existing_fact):
                    inconsistencies.append(
                        {
                            "new_fact": new_fact.fact,
                            "existing_fact": existing_fact.fact,
                            "new_section": new_fact.section_id,
                            "existing_section": existing_fact.section_id,
                            "issue": "잠재적 일관성 문제",
                        }
                    )

        if inconsistencies:
            self.logger.warning(f"{len(inconsistencies)}개의 잠재적 일관성 문제 발견")

        return inconsistencies

    def _create_fact_extraction_prompt(
        self, section: SectionContent, keyword: str, existing_facts: str
    ) -> str:
        """사실 추출을 위한 프롬프트 생성"""
        prompt = f"""
다음 블로그 섹션에서 핵심 사실들을 추출해주세요.

**문서 정보:**
- 타겟 키워드: {keyword}
- 섹션 ID: {section.section_id}
- 섹션 제목: {section.title}

**섹션 내용:**
{section.content}

**기존에 추출된 사실들 (중복 방지 참고용):**
{existing_facts if existing_facts else "없음"}

**추출 기준:**
1. 구체적이고 검증 가능한 사실만 추출
2. 일반적인 상식이나 의견은 제외
3. 숫자, 통계, 구체적인 방법론 포함
4. 기존 사실과 중복되지 않는 새로운 정보만

**출력 형식:**
각 사실을 다음 형식으로 한 줄씩 작성해주세요:
FACT: [구체적인 사실 내용]

예시:
FACT: SEO 최적화를 통해 웹사이트 트래픽을 평균 150% 증가시킬 수 있음
FACT: 메타 태그 최적화는 검색 엔진 순위에 직접적인 영향을 미침
"""
        return prompt

    def _create_terminology_extraction_prompt(
        self, section: SectionContent, keyword: str
    ) -> str:
        """용어 추출을 위한 프롬프트 생성"""
        prompt = f"""
다음 블로그 섹션에서 전문 용어와 그 정의를 추출해주세요.

**문서 정보:**
- 타겟 키워드: {keyword}
- 섹션 제목: {section.title}

**섹션 내용:**
{section.content}

**추출 기준:**
1. 전문적이거나 기술적인 용어만 추출
2. 일반적으로 알려진 용어는 제외
3. 섹션 내에서 설명되거나 정의된 용어 우선
4. 약어나 영어 용어 포함

**출력 형식:**
각 용어를 다음 형식으로 한 줄씩 작성해주세요:
TERM: [용어] | [정의]

예시:
TERM: CTR | 클릭율(Click Through Rate)의 약자로, 광고나 링크가 노출된 횟수 대비 클릭된 비율
TERM: 백링크 | 다른 웹사이트에서 자신의 웹사이트로 연결되는 링크
"""
        return prompt

    def _parse_facts_response(self, response: str, section_id: str) -> List[KeyFact]:
        """LLM 응답에서 사실들을 파싱"""
        facts = []

        # FACT: 패턴으로 사실 추출
        fact_pattern = r"FACT:\s*(.+)"
        matches = re.findall(fact_pattern, response, re.MULTILINE)

        for match in matches:
            fact_text = match.strip()
            if len(fact_text) > 10:  # 너무 짧은 사실은 제외
                fact = KeyFact(
                    fact=fact_text,
                    section_id=section_id,
                    confidence=0.8,  # 기본 신뢰도
                    related_terms=self._extract_terms_from_fact(fact_text),
                )
                facts.append(fact)

        return facts

    def _parse_terminology_response(self, response: str) -> Dict[str, str]:
        """LLM 응답에서 용어들을 파싱"""
        terminology = {}

        # TERM: 패턴으로 용어 추출
        term_pattern = r"TERM:\s*([^|]+)\s*\|\s*(.+)"
        matches = re.findall(term_pattern, response, re.MULTILINE)

        for term, definition in matches:
            term = term.strip()
            definition = definition.strip()
            if len(term) > 1 and len(definition) > 5:
                terminology[term] = definition

        return terminology

    def _extract_terms_from_fact(self, fact_text: str) -> List[str]:
        """사실 텍스트에서 관련 용어들을 추출"""
        # 간단한 키워드 추출 (향후 더 정교한 NLP 기법 적용 가능)
        terms = []

        # 기본적인 전문 용어 패턴들
        patterns = [
            r"\b[A-Z]{2,}\b",  # 대문자 약어 (SEO, API 등)
            r"\b\w+(?:율|도|법|화|성)\b",  # 한국어 전문 용어 (-율, -도, -법 등)
            r"\b\w+\s*\([^)]+\)\b",  # 괄호로 설명된 용어
        ]

        for pattern in patterns:
            matches = re.findall(pattern, fact_text)
            terms.extend(matches)

        return list(set(terms))  # 중복 제거

    def _facts_potentially_conflict(self, fact1: KeyFact, fact2: KeyFact) -> bool:
        """두 사실이 잠재적으로 충돌할 수 있는지 확인"""
        # 간단한 키워드 기반 충돌 검사
        fact1_words = set(fact1.fact.lower().split())
        fact2_words = set(fact2.fact.lower().split())

        # 공통 키워드가 있고, 상반된 표현이 있는지 확인
        common_words = fact1_words.intersection(fact2_words)

        if len(common_words) >= 2:  # 최소 2개 이상의 공통 단어
            # 상반된 표현 확인
            conflicting_pairs = [
                ("증가", "감소"),
                ("향상", "저하"),
                ("좋음", "나쁨"),
                ("권장", "비권장"),
                ("가능", "불가능"),
                ("효과적", "비효과적"),
            ]

            for word1, word2 in conflicting_pairs:
                if word1 in fact1.fact and word2 in fact2.fact:
                    return True
                if word2 in fact1.fact and word1 in fact2.fact:
                    return True

        return False
