# src/generators/content/section_generator.py
# 섹션 콘텐츠 생성기 - 메모리 관리를 통한 일관성 있는 섹션 생성

import logging
import time
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
from langchain.schema import HumanMessage, SystemMessage

from src.models.section_models import (
    SectionGenerationOptions,
    SectionGenerationResult,
    SectionContent,
    DocumentMemory,
)
from src.models.blog_models import BlogOutline, BlogSection
from src.generators.content.memory import DocumentMemoryManager, FactTracker
from src.utils.config import load_config
from src.utils.llm_factory import LLMFactory, LLMConfig
from src.utils.rag import SimpleRAG

logger = logging.getLogger(__name__)


class SectionGenerator:
    """
    섹션 콘텐츠 생성기

    메모리 관리를 통해 문서 전반의 일관성을 유지하면서
    각 섹션별로 300-500자의 고품질 콘텐츠를 생성
    """

    def __init__(
        self,
        config: Optional[Dict] = None,
        memory_save_path: Optional[str] = None,
        rag: Optional[SimpleRAG] = None,
    ):
        """
        섹션 생성기 초기화

        Args:
            config: LLM 설정 (기본값: None, 자동 로드)
            memory_save_path: 메모리 저장 경로 (선택사항)
            rag: 선택적 RAG 주입 객체
        """
        self.config = config or load_config()
        self.llm = None
        self.memory_save_path = memory_save_path
        self.rag = rag

        # LLM 설정 먼저 생성
        self.llm_config = LLMConfig(
            provider=self.config["llm"]["default_provider"],
            model=self.config["llm"]["openai_model"],
            temperature=self.config["llm"]["temperature"],
            max_tokens=self.config["llm"]["max_tokens"],
        )

        # 메모리 관리 컴포넌트들 초기화 (LLM 설정 전달)
        self.memory_manager = DocumentMemoryManager(self.llm_config)
        self.fact_tracker = FactTracker(self.config)

        self.logger = logger
        self._initialize_llm()

    def _initialize_llm(self) -> None:
        """콘텐츠 생성을 위한 LLM 초기화"""
        try:
            factory = LLMFactory()
            self.llm = factory.create_llm(self.llm_config)
            self.logger.info(
                f"섹션 생성기 LLM 초기화 완료: {self.llm_config.provider}/{self.llm_config.model}"
            )

        except Exception as e:
            self.logger.error(f"LLM 초기화 실패: {e}")
            raise RuntimeError(f"LLM 초기화 실패: {e}")

    def initialize_document(
        self,
        title: str,
        keyword: str,
        outline: BlogOutline,
        target_audience: str = "general",
    ) -> DocumentMemory:
        """
        새 문서에 대한 메모리 초기화

        Args:
            title: 문서 제목
            keyword: 타겟 키워드
            outline: 블로그 아웃라인
            target_audience: 타겟 독자

        Returns:
            초기화된 DocumentMemory 객체
        """
        self.logger.info(f"문서 초기화: '{title}' (키워드: '{keyword}')")

        memory = self.memory_manager.initialize_memory(
            title=title,
            keyword=keyword,
            outline=outline,
            target_audience=target_audience,
        )

        self.logger.info(f"문서 메모리 초기화 완료: {len(outline.sections)}개 섹션")
        return memory

    def generate_section_content(
        self,
        section: BlogSection,
        section_index: int,
        context: Dict[str, Any],
        options: SectionGenerationOptions = None,
    ) -> SectionGenerationResult:
        """특정 섹션의 콘텐츠 생성"""

        if options is None:
            options = SectionGenerationOptions()

        section_id = str(section_index)
        section_title = section.h2
        subsection_titles = section.h3

        self.logger.info(f"섹션 생성 시작: {section_index} - {section_title}")

        try:
            start_time = time.time()

            # 메모리에서 컨텍스트 가져오기 + 키워드 전략 추가
            memory_context = self.memory_manager.get_context_for_section(
                section_id, section_title
            )

            # 키워드 전략을 컨텍스트에 추가
            if "keyword_strategy" in context:
                memory_context["keyword_strategy"] = context["keyword_strategy"]

            # 기본 컨텍스트와 메모리 컨텍스트 병합
            combined_context = {**context, **memory_context}

            # 콘텐츠 생성 프롬프트 생성
            prompt = self._create_section_generation_prompt(
                section, section_index, combined_context
            )

            # RAG 주입: rag가 있다면 관련 컨텍스트를 앞단에 추가
            if self.rag:
                rag_query = f"{combined_context.get('document_title','')} - {section_title} 핵심 내용 요약"
                rag_context = self.rag.query(rag_query)
                if rag_context:
                    prompt = f"{rag_context}\n\n---\n\n{prompt}"

            # LLM으로 콘텐츠 생성
            message = HumanMessage(content=prompt)
            response = self.llm.invoke([message])
            section_content = response.content.strip()

            # SectionContent 객체 생성
            section_content_obj = SectionContent(
                section_id=section_id,
                title=section_title,
                content=section_content,
                word_count=len(section_content),
                key_points=[],  # 간단히 빈 리스트로 설정
                mentioned_facts=[],  # 간단히 빈 리스트로 설정
            )

            # 메모리에 생성된 섹션 추가
            self.memory_manager.add_generated_section(section_content_obj)

            # 사실 및 용어 추출
            extracted_facts = []
            new_terminology = {}

            if self.fact_tracker:
                extracted_facts = self.fact_tracker.extract_facts_from_content(
                    section_content_obj, combined_context["target_keyword"]
                )
                new_terminology = self.fact_tracker.extract_terminology_from_content(
                    section_content_obj, combined_context["target_keyword"]
                )

                # 메모리에 추가
                if extracted_facts:
                    self.memory_manager.add_facts(extracted_facts)
                if new_terminology:
                    self.memory_manager.add_terminology(new_terminology)

            generation_time = time.time() - start_time

            # 결과 객체 생성
            result = SectionGenerationResult(
                section_content=section_content_obj,
                extracted_facts=extracted_facts,
                new_terminology=new_terminology,
                generation_time=generation_time,
                token_usage={},  # 실제 토큰 사용량은 LLM 응답에서 가져올 수 있음
                success=True,
            )

            self.logger.info(
                f"섹션 생성 완료: {section_index} ({len(section_content)}자, {generation_time:.1f}초)"
            )
            return result

        except Exception as e:
            self.logger.error(f"섹션 생성 실패: {section_index} - {e}")

            # 빈 SectionContent 객체 생성
            empty_section_content = SectionContent(
                section_id=section_id,
                title=section_title,
                content="",
                word_count=0,
                key_points=[],
                mentioned_facts=[],
            )

            return SectionGenerationResult(
                section_content=empty_section_content,
                extracted_facts=[],
                new_terminology={},
                generation_time=0,
                token_usage={},
                success=False,
                error_message=str(e),
            )

    def generate_full_document_content(
        self, outline: BlogOutline, options: Optional[SectionGenerationOptions] = None
    ) -> List[SectionGenerationResult]:
        """
        전체 문서의 모든 섹션 콘텐츠를 순차적으로 생성

        Args:
            outline: 블로그 아웃라인
            options: 생성 옵션

        Returns:
            모든 섹션의 생성 결과 리스트
        """
        self.logger.info(f"전체 문서 생성 시작: {len(outline.sections)}개 섹션")

        results = []

        for i, section in enumerate(outline.sections, 1):
            section_id = str(i)

            # 하위 섹션 제목들 준비
            subsection_titles = section.h3 if section.h3 else []

            # 섹션 콘텐츠 생성
            result = self.generate_section_content(
                section=section,
                section_index=i,
                context={
                    "document_title": outline.title,
                    "target_keyword": outline.meta.target_keyword,
                    "target_audience": "general",
                },
                options=options,
            )

            results.append(result)

            # 성공한 경우에만 진행 (실패 시 로그만 남기고 계속)
            if result.success:
                self.logger.info(f"섹션 {section_id} 생성 완료")
            else:
                self.logger.warning(f"섹션 {section_id} 생성 실패, 계속 진행")

        # 전체 통계 로깅
        successful_sections = sum(1 for r in results if r.success)
        total_words = sum(r.section_content.word_count for r in results if r.success)
        total_time = sum(r.generation_time for r in results)

        self.logger.info(
            f"전체 문서 생성 완료: {successful_sections}/{len(results)} 섹션 성공, "
            f"총 {total_words:,}자, {total_time:.2f}초"
        )

        return results

    def get_memory_stats(self) -> Dict[str, any]:
        """현재 메모리 상태 통계 반환"""
        return self.memory_manager.get_memory_stats()

    def _create_section_generation_prompt(
        self,
        section: BlogSection,
        section_index: int,
        context: Dict[str, Any],
    ) -> str:
        """섹션별 맞춤형 프롬프트 생성 - 다음 섹션 연결 포함"""

        # 다음 섹션 정보 확인
        all_sections = context.get("all_sections", [])
        next_section = (
            all_sections[section_index] if section_index < len(all_sections) else None
        )

        # 섹션 타입별 프롬프트 생성
        return self._create_section_specific_prompt(
            section, section_index, context, next_section
        )

    def _create_section_specific_prompt(
        self,
        section: BlogSection,
        section_index: int,
        context: Dict[str, Any],
        next_section: BlogSection = None,
    ) -> str:
        """섹션 타입별 세부 프롬프트 생성 - GPT-5-nano 최적화 및 자연스러운 콘텐츠 플로우"""

        # 키워드 전략 정보 추출
        keyword_strategy = context.get("keyword_strategy")

        # 전체 섹션 수를 기반으로 한 최적 길이 계산
        total_sections = len(context.get("all_sections", []))
        total_target_length = 4500  # 4000-6000 범위의 중간값

        # 섹션별 권장 길이 계산 (첫 섹션은 짧게, 나머지는 균등 분배)
        if section_index == 1:  # 개요 섹션
            target_length = "400-500자"
            per_section_target = 400
        elif (
            section_index == total_sections and "FAQ" in section.h2.upper()
        ):  # 마지막 FAQ 섹션
            target_length = "300-400자"
            per_section_target = 350
        else:  # 일반 섹션들
            remaining_length = (
                total_target_length - 400 - (350 if total_sections > 2 else 0)
            )
            remaining_sections = max(
                1, total_sections - (2 if total_sections > 2 else 1)
            )
            per_section_target = remaining_length // remaining_sections
            target_length = f"{per_section_target-50}-{per_section_target+100}자"

        is_overview_section = section_index == 1

        # 키워드 전략 정보 구성
        keyword_info = ""
        if keyword_strategy:
            primary_keyword = keyword_strategy.primary_keyword
            target_frequency = keyword_strategy.target_frequency

            # LSI 키워드 정보
            lsi_keywords = [lsi.keyword for lsi in keyword_strategy.lsi_keywords[:6]]
            lsi_keywords_str = ", ".join(lsi_keywords) if lsi_keywords else "없음"

            # 롱테일 키워드 정보
            longtail_keywords = [
                lt.phrase for lt in keyword_strategy.longtail_keywords[:3]
            ]
            longtail_keywords_str = (
                ", ".join(longtail_keywords) if longtail_keywords else "없음"
            )

            # 의미적 변형 정보
            variations = keyword_strategy.semantic_variations[:4]
            variations_str = ", ".join(variations) if variations else "없음"

            keyword_info = f"""
**키워드 전략 (매우 중요):**
- 핵심 키워드 '{primary_keyword}': 이 섹션에서 최대 1-2회만 사용 (전체 문서에서 총 {target_frequency}회 목표)
- LSI 키워드 활용: {lsi_keywords_str}
- 롱테일 키워드 참고: {longtail_keywords_str}  
- 의미적 변형 표현: {variations_str}

**키워드 사용 원칙:**
1. 핵심 키워드를 과도하게 반복하지 마세요 (자연스러움 우선)
2. LSI 키워드를 자연스럽게 본문에 포함하세요
3. 의미적 변형 표현을 활용하여 다양성을 높이세요
4. 키워드 밀도보다는 자연스러운 내용 흐름을 우선하세요
"""
        else:
            keyword_info = f"""
**키워드 사용:**
- 타겟 키워드 '{context['target_keyword']}': 이 섹션에서 1-2회 자연스럽게 포함
"""

        # 이전 섹션 컨텍스트 (LangChain 메모리 활용)
        previous_context = ""
        if section_index > 1:
            previous_context = self.memory_manager.get_natural_flow_context(section.h2)
            if previous_context:
                previous_context = f"""
**이전 내용과의 연결:**
{previous_context}

이를 자연스럽게 참고하여 매끄럽게 이어가되, 명시적인 연결 문구("이전 섹션에서", "앞에서 언급한")는 피하세요.
"""

        # 다음 섹션 연결 정보 생성 (개선된 플로우)
        next_section_hint = ""
        if next_section and section_index < len(context.get("all_sections", [])):
            # 마지막 섹션이 아닌 경우에만 다음 섹션 힌트 추가
            next_section_hint = f"""
**🔄 다음 섹션 연결 가이드 (매우 중요):**
다음에 '{next_section.h2}' 섹션이 이어집니다. 
이 섹션의 마지막 부분에 다음 섹션으로 자연스럽게 이어지는 한 문장을 포함하세요.

예시 연결 문구:
- "이제 {next_section.h2.lower()}에 대해 구체적으로 살펴보겠습니다."
- "다음으로는 {next_section.h2.lower()}에 대해 알아보도록 하겠습니다."
- "그렇다면 {next_section.h2.lower()}은 어떻게 해야 할까요?"

**중요**: 연결 문구는 섹션의 마지막 문단에 자연스럽게 포함되어야 하며, 억지스럽지 않아야 합니다.
"""
        else:
            # 마지막 섹션인 경우
            next_section_hint = """
**✅ 마지막 섹션 마무리:**
이 섹션이 마지막이므로, 전체 내용을 자연스럽게 마무리하되 결론형 표현은 피하고 독자에게 도움이 되는 내용으로 끝내세요.
"""

        prompt = f"""
당신은 전문적인 블로그 콘텐츠 작성자입니다. 
다음 섹션의 고품질 콘텐츠를 생성해주세요.

**섹션 정보:**
- 섹션 제목: {section.h2}
- 목표 길이: {target_length}
- 하위 섹션: {section.h3 if section.h3 else '없음'}
- 문서 제목: {context['document_title']}
- 타겟 키워드: {context['target_keyword']}

{keyword_info}

{previous_context}

{next_section_hint}

**🚨 중요 - 출력 형식:**
- 절대로 "섹션:", "제목:", "내용:" 같은 메타 정보를 출력하지 마세요
- 섹션 제목 {section.h2}을 다시 출력하지 마세요 (별도 처리됨)
- 바로 본문 내용부터 시작하세요
- H3 하위 섹션이 있는 경우: ### 하위섹션제목 형태로 작성

**작성 가이드라인:**
1. 목표 길이 {target_length}를 정확히 준수
2. 키워드 '{context['target_keyword']}'를 자연스럽게 포함 (과도한 반복 금지)
3. {'간결하고 핵심적인 소개로 독자 관심 유도' if is_overview_section else '구체적이고 실용적인 정보 제공'}
4. 독자가 바로 활용할 수 있는 실질적 내용 중심
5. 전문 용어 사용 시 간단한 설명 포함

**절대 금지 사항:**
- 섹션 메타정보 출력: "섹션: XXX", "제목: XXX", "내용: XXX"
- 섹션 제목 재출력: "{section.h2}" 다시 쓰지 마세요
- 결론형 표현: "마지막으로", "결론적으로", "정리하자면", "요약하면"
- 명시적 참조: "앞에서 말한", "이전 섹션에서", "위에서 언급한"

**섹션별 특화 지침:**
{'개요 섹션: 핵심 개념 간단 소개, 독자 호기심 자극' if is_overview_section else ('FAQ 섹션: Q: 질문, A: 답변 형식, 각 Q&A는 2-3문장' if 'FAQ' in section.h2.upper() else '본문 섹션: 상세 정보, 구체적 예시, 단계별 설명')}

**연결성:**
- 이전 내용을 자연스럽게 이어받되 명시적 참조는 피하세요
- {'마지막 문단에 다음 섹션 연결 문구 포함' if next_section else '자연스럽게 마무리'}

**출력 예시:**
```
### 하위섹션제목 (있는 경우만)
본문 내용이 바로 시작됩니다. 섹션 제목이나 메타 정보는 절대 출력하지 않습니다.

각 문단은 3-5문장으로 구성하며, 독자에게 유용한 정보를 제공합니다.

{'다음으로는 ' + next_section.h2.lower() + '에 대해 알아보겠습니다.' if next_section else ''}
```

**핵심: 바로 본문 내용부터 출력하고, 어떤 메타 정보도 포함하지 마세요!**
"""
        return prompt

    def _generate_content_with_llm(self, prompt: str) -> str:
        """LLM을 통한 실제 콘텐츠 생성"""
        if not self.llm:
            raise ValueError("LLM이 초기화되지 않았습니다.")

        try:
            messages = [
                SystemMessage(
                    content="당신은 전문적이고 실용적인 블로그 콘텐츠를 작성하는 전문가입니다."
                ),
                HumanMessage(content=prompt),
            ]

            response = self.llm.invoke(messages)
            content = response.content.strip()

            # 기본적인 콘텐츠 검증
            if len(content) < 100:
                raise ValueError("생성된 콘텐츠가 너무 짧습니다.")

            return content

        except Exception as e:
            self.logger.error(f"LLM 콘텐츠 생성 실패: {e}")
            raise

    def _extract_key_points_from_content(self, content: str) -> List[str]:
        """콘텐츠에서 핵심 포인트들을 추출"""
        # 간단한 키 포인트 추출 로직
        # 향후 더 정교한 NLP 기법으로 개선 가능

        key_points = []

        # 문장 단위로 분리
        sentences = [s.strip() for s in content.split(".") if len(s.strip()) > 10]

        # 중요해 보이는 문장들 추출 (키워드 기반)
        important_keywords = [
            "중요한",
            "핵심",
            "필수",
            "반드시",
            "주목할",
            "기억할",
            "포인트",
            "방법",
            "전략",
            "기법",
            "노하우",
            "팁",
            "비결",
        ]

        for sentence in sentences[:10]:  # 최대 10개 문장만 검토
            if any(keyword in sentence for keyword in important_keywords):
                if len(sentence) < 100:  # 너무 긴 문장은 제외
                    key_points.append(sentence.strip())

        # 최대 5개의 핵심 포인트만 반환
        return key_points[:5]
