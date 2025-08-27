# v1.3 - LangChain 기반 메모리 시스템으로 업그레이드 (2025.08.23)
"""
문서 메모리 관리 모듈 - LangChain 통합
DocumentMemoryManager가 전체 문서 생성 과정에서 메모리를 관리합니다.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# LangChain 메모리 관련 임포트
from langchain.memory import ConversationSummaryMemory
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.messages import AIMessage, HumanMessage

from src.models.section_models import DocumentMemory, SectionContent, KeyFact
from src.utils.llm_factory import LLMFactory, LLMConfig
from src.utils.config import load_config


class DocumentMemoryManager:
    """
    문서 생성 과정에서 메모리를 관리하는 클래스
    LangChain의 ConversationSummaryMemory를 활용하여 섹션 간 자연스러운 연결성 제공
    """

    def __init__(self, llm_config: Optional[LLMConfig] = None):
        """
        DocumentMemoryManager 초기화

        Args:
            llm_config: LLM 설정 (None인 경우 기본 설정 사용)
        """
        self.logger = logging.getLogger(__name__)
        self.memory: Optional[DocumentMemory] = None
        self.save_path: Optional[Path] = None

        # LangChain 메모리 초기화
        if llm_config is None:
            config = load_config()
            llm_config = LLMConfig(
                provider=config["llm"]["default_provider"],
                model=config["llm"]["openai_model"],
                temperature=config["llm"]["temperature"],
                max_tokens=500,  # 요약용이므로 토큰 수 제한
            )

        # LLM 인스턴스 생성
        factory = LLMFactory()
        self.llm = factory.create_llm(llm_config)

        # LangChain ConversationSummaryMemory 초기화
        self.summary_memory = ConversationSummaryMemory(
            llm=self.llm,
            memory_key="section_history",
            return_messages=False,
            ai_prefix="생성된_섹션",
            human_prefix="섹션_요청",
        )

        self.logger.info(
            f"DocumentMemoryManager 초기화 완료: LLM={llm_config.provider}/{llm_config.model}"
        )

    def initialize_memory(
        self,
        title: str,
        keyword: str,
        outline,
        target_audience: str = "일반 독자",
    ) -> DocumentMemory:
        """
        새 문서를 위한 메모리 초기화

        Args:
            title: 문서 제목
            keyword: 타겟 키워드
            outline: 문서 아웃라인
            target_audience: 타겟 독자

        Returns:
            초기화된 DocumentMemory 객체
        """
        self.logger.info(f"문서 메모리 초기화: '{title}' (키워드: '{keyword}')")

        # 기본 DocumentMemory 초기화
        self.memory = DocumentMemory(
            document_title=title,
            target_keyword=keyword,
            document_intent=getattr(outline.meta, "intent", "guide"),
            target_audience=target_audience,
        )

        # LangChain 메모리 초기화
        self.summary_memory.clear()

        # 문서 시작을 메모리에 기록
        self.summary_memory.save_context(
            {
                "섹션_요청": f"문서 '{title}' 시작 - 키워드: '{keyword}', 대상: {target_audience}"
            },
            {
                "생성된_섹션": f"문서 구조 설정 완료. {len(outline.sections)}개 섹션으로 구성된 '{keyword}' 관련 가이드를 작성할 예정입니다."
            },
        )

        # 스타일 프로필 설정 (기존 로직 유지)
        if hasattr(outline.meta, "estimated_length"):
            if outline.meta.estimated_length > 3000:
                self.memory.style_profile.complexity_level = "advanced"
            elif outline.meta.estimated_length < 2000:
                self.memory.style_profile.complexity_level = "beginner"

        self.logger.info(
            f"메모리 초기화 완료: 스타일={self.memory.style_profile.tone}, "
            f"복잡도={self.memory.style_profile.complexity_level}"
        )
        return self.memory

    def get_context_for_section(
        self, section_id: str, section_title: str
    ) -> Dict[str, str]:
        """
        특정 섹션 생성을 위한 컨텍스트 제공
        LangChain의 요약 기능을 활용하여 자연스러운 연결성 제공

        Args:
            section_id: 섹션 ID (예: '1', '2.1')
            section_title: 섹션 제목

        Returns:
            섹션 생성에 필요한 컨텍스트 딕셔너리
        """
        if not self.memory:
            raise ValueError("메모리가 초기화되지 않았습니다.")

        # LangChain 요약 기능 사용
        section_summary = self.summary_memory.buffer

        # 기본 컨텍스트 구성
        context = {
            "document_title": self.memory.document_title,
            "target_keyword": self.memory.target_keyword,
            "document_intent": self.memory.document_intent,
            "target_audience": self.memory.target_audience,
            "section_id": section_id,
            "section_title": section_title,
            "style_tone": self.memory.style_profile.tone,
            "complexity_level": self.memory.style_profile.complexity_level,
            # LangChain 기반 자연스러운 요약
            "previous_sections": (
                section_summary if section_summary.strip() else "문서를 시작합니다."
            ),
            # 기존 사실 및 용어 정보
            "accumulated_facts": self.memory.get_accumulated_facts(),
            "terminology": self.memory.get_terminology_context(),
            "total_sections_so_far": len(self.memory.generated_sections),
            "total_words_so_far": self.memory.total_word_count,
        }

        return context

    def add_generated_section(self, section: SectionContent) -> None:
        """
        생성된 섹션을 메모리에 추가하고 LangChain 요약 업데이트

        Args:
            section: 생성된 섹션 콘텐츠
        """
        if not self.memory:
            raise ValueError("메모리가 초기화되지 않았습니다.")

        # 기존 DocumentMemory에 추가
        self.memory.add_section(section)

        # LangChain 메모리에 섹션 정보 추가 (자동 요약됨)
        section_request = f"섹션 {section.section_id}: '{section.title}' 생성 요청"
        section_summary = f"'{section.title}' 섹션 완성 ({section.word_count}자). 핵심 내용: {', '.join(section.key_points[:3])}"

        self.summary_memory.save_context(
            {"섹션_요청": section_request}, {"생성된_섹션": section_summary}
        )

        self.logger.info(
            f"섹션 추가됨: {section.section_id} - {section.title} ({section.word_count}자)"
        )

    def add_facts(self, facts: List[KeyFact]) -> None:
        """새로운 사실들을 메모리에 추가"""
        if not self.memory:
            raise ValueError("메모리가 초기화되지 않았습니다.")

        for fact in facts:
            self.memory.add_fact(fact)

        self.logger.info(f"{len(facts)}개의 새로운 사실이 추가됨")

    def add_terminology(self, terminology: Dict[str, str]) -> None:
        """새로운 용어들을 메모리에 추가"""
        if not self.memory:
            raise ValueError("메모리가 초기화되지 않았습니다.")

        for term, definition in terminology.items():
            self.memory.add_terminology(term, definition)

        self.logger.info(f"{len(terminology)}개의 새로운 용어가 정의됨")

    def get_memory_stats(self) -> Dict[str, any]:
        """현재 메모리 상태 통계 반환"""
        if not self.memory:
            return {"status": "메모리가 초기화되지 않음"}

        return {
            "document_title": self.memory.document_title,
            "sections_count": len(self.memory.generated_sections),
            "total_words": self.memory.total_word_count,
            "facts_count": len(self.memory.key_facts),
            "terminology_count": len(self.memory.terminology),
            "style_tone": self.memory.style_profile.tone,
            "complexity_level": self.memory.style_profile.complexity_level,
            "langchain_summary_length": len(self.summary_memory.buffer),
        }

    def get_natural_flow_context(self, current_section_title: str) -> str:
        """
        현재 섹션을 위한 자연스러운 흐름 컨텍스트 생성
        LangChain 요약을 기반으로 더 자연스러운 전환 문구 제공
        """
        if not self.summary_memory.buffer.strip():
            return "이 섹션부터 시작하겠습니다."

        # LangChain이 생성한 요약을 기반으로 자연스러운 연결 문구 생성
        summary = self.summary_memory.buffer
        flow_context = (
            f"이전까지의 내용: {summary}\n"
            f"→ 이제 '{current_section_title}' 섹션에서 이어서 설명하겠습니다."
        )

        return flow_context

    def save_memory(self, file_path: str) -> None:
        """메모리를 파일에 저장"""
        if not self.memory:
            raise ValueError("저장할 메모리가 없습니다.")

        try:
            memory_data = self.memory.model_dump()
            # LangChain 요약도 함께 저장
            memory_data["langchain_summary"] = self.summary_memory.buffer

            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(memory_data, f, ensure_ascii=False, indent=2, default=str)

            self.save_path = Path(file_path)
            self.logger.info(f"메모리 저장 완료: {file_path}")

        except Exception as e:
            self.logger.error(f"메모리 저장 실패: {e}")
            raise ValueError(f"메모리 저장 실패: {e}")

    def load_memory(self, file_path: str) -> DocumentMemory:
        """파일에서 메모리 로드"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                memory_data = json.load(f)

            # LangChain 요약 복원
            if "langchain_summary" in memory_data:
                # 요약 데이터로 LangChain 메모리 재구성
                summary_text = memory_data.pop("langchain_summary")
                self.summary_memory.buffer = summary_text

            self.memory = DocumentMemory.model_validate(memory_data)
            self.save_path = Path(file_path)

            self.logger.info(f"메모리 로드 완료: {file_path}")
            return self.memory

        except Exception as e:
            self.logger.error(f"메모리 로드 실패: {e}")
            raise ValueError(f"메모리 로드 실패: {e}")
