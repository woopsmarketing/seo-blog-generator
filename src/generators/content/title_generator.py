# src/generators/content/title_generator.py
# SEO 최적화 제목 생성기 - 키워드 기반 매력적인 제목 생성

import logging
from typing import List, Optional, Dict, Any
from dataclasses import dataclass

from langchain.schema import BaseMessage, HumanMessage
from langchain.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field

from src.utils.llm_factory import LLMFactory, LLMConfig
from src.utils.config import load_config

logger = logging.getLogger(__name__)


@dataclass
class TitleOptions:
    """제목 생성 옵션 설정"""

    max_length: int = 60  # SEO 권장 제목 길이
    min_length: int = 20
    include_numbers: bool = True  # "5가지", "10개" 등 숫자 포함
    include_year: bool = True  # "2025년" 등 연도 포함
    tone: str = "professional"  # professional, casual, expert
    target_audience: str = "general"  # general, beginners, experts


class GeneratedTitle(BaseModel):
    """생성된 제목 데이터 모델"""

    title: str = Field(description="생성된 SEO 최적화 제목")
    seo_score: int = Field(description="SEO 점수 (1-10)", ge=1, le=10)
    keyword_density: float = Field(description="키워드 밀도 (0-1)", ge=0, le=1)
    reasoning: str = Field(description="제목 선택 이유 및 SEO 전략")
    alternatives: List[str] = Field(description="대안 제목 목록", max_items=3)


class TitleGenerator:
    """
    키워드 기반 SEO 최적화 제목 생성기

    기능:
    - 키워드 중심의 매력적인 제목 생성
    - SEO 최적화 (길이, 키워드 밀도, 구조)
    - 다양한 제목 스타일 지원
    - 대안 제목 제공
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        제목 생성기 초기화

        Args:
            config: 설정 정보 딕셔너리
        """
        self.config = config or load_config()
        self.llm_factory = LLMFactory()
        self.llm = None
        self._initialize_llm()

        # 출력 파서 설정
        self.output_parser = PydanticOutputParser(pydantic_object=GeneratedTitle)

        logger.info("TitleGenerator 초기화 완료")

    def _initialize_llm(self) -> None:
        """LLM 인스턴스 초기화"""
        try:
            llm_config = LLMConfig(
                provider=self.config["llm"]["default_provider"],
                model=self.config["llm"]["openai_model"],
                temperature=self.config["llm"]["temperature"],
                max_tokens=500,  # GPT-4용 토큰 수
            )
            self.llm = self.llm_factory.create_llm(llm_config)
            logger.info(f"LLM 초기화 성공: {llm_config.provider}/{llm_config.model}")
        except Exception as e:
            logger.error(f"LLM 초기화 실패: {e}")
            raise

    def generate_title(
        self, keyword: str, options: Optional[TitleOptions] = None
    ) -> GeneratedTitle:
        """
        키워드를 기반으로 SEO 최적화 제목 생성

        Args:
            keyword: 타겟 키워드
            options: 제목 생성 옵션

        Returns:
            GeneratedTitle: 생성된 제목 및 메타데이터
        """
        if not keyword.strip():
            raise ValueError("키워드는 비워둘 수 없습니다")

        options = options or TitleOptions()

        logger.info(f"제목 생성 시작: 키워드='{keyword}'")

        try:
            # 프롬프트 생성
            prompt = self._create_title_prompt(keyword, options)

            # LLM으로 제목 생성
            messages = [HumanMessage(content=prompt)]
            response = self.llm.invoke(messages)

            # JSON 응답 직접 파싱
            title_result = self._parse_json_response(response.content)

            # 결과 검증
            self._validate_title(title_result, keyword, options)

            logger.info(f"제목 생성 성공: '{title_result.title}'")
            return title_result

        except Exception as e:
            logger.error(f"제목 생성 실패: {e}")
            # 폴백: 기본 제목 생성
            return self._create_fallback_title(keyword, options)

    def _parse_json_response(self, response_content: str) -> GeneratedTitle:
        """JSON 응답을 직접 파싱하여 GeneratedTitle 객체로 변환"""
        import json
        import re

        try:
            # 응답에서 JSON 부분만 추출
            content = response_content.strip()

            # 코드 블록이나 마크다운 제거
            if content.startswith("```"):
                # ```json ... ``` 형태 처리
                content = re.sub(r"^```\w*\n", "", content)
                content = re.sub(r"\n```$", "", content)

            # JSON 파싱
            data = json.loads(content)

            # GeneratedTitle 객체 생성
            return GeneratedTitle(
                title=data.get("title", ""),
                seo_score=int(float(data.get("seo_score", 5))),  # 소수점을 정수로 변환
                keyword_density=float(data.get("keyword_density", 0.0)),
                reasoning=data.get("reasoning", ""),
                alternatives=data.get("alternatives", []),
            )

        except (json.JSONDecodeError, KeyError, TypeError) as e:
            logger.error(f"JSON 파싱 오류: {e}")
            logger.error(f"응답 내용: {response_content}")
            raise ValueError(f"JSON 파싱 실패: {e}")

    def _create_title_prompt(self, keyword: str, options: TitleOptions) -> str:
        """제목 생성을 위한 프롬프트 생성"""

        # JSON 스키마 정의
        json_schema = """
{
  "title": "생성된 블로그 제목",
  "seo_score": 8,
  "keyword_density": 0.15,
  "reasoning": "제목 선택 이유",
  "alternatives": ["대안 제목 1", "대안 제목 2", "대안 제목 3"]
}
        """

        prompt = f"""
당신은 SEO 전문가이자 블로그 제목 작성 전문가입니다.
주어진 키워드를 바탕으로 매력적이고 SEO에 최적화된 블로그 제목을 **정확한 JSON 형식**으로 생성해주세요.

현재 날짜: 2025년 8월 (참고용, 꼭 제목에 포함할 필요 없음)
타겟 키워드: "{keyword}"

제목 생성 조건:
- 길이: {options.min_length}-{options.max_length}자 사이
- 키워드 포함 필수
- 톤: {options.tone}
- 타겟 독자: {options.target_audience}
- 숫자 포함: {"권장" if options.include_numbers else "비권장"}
- 연도 포함: {"선택사항 - 트렌드/최신성이 핵심 가치인 경우에만 2025년 사용 (대부분 불필요)" if options.include_year else "비권장"}

SEO 최적화 요소:
1. 키워드를 제목 앞부분에 배치
2. 클릭을 유도하는 감정적 요소 포함
3. 명확하고 구체적인 베네핏 제시
4. 검색 의도에 맞는 제목 구조

효과적인 제목 패턴 (연도 없이도 충분히 매력적):
- "키워드 완벽 가이드", "키워드 5가지 방법", "키워드 총정리"
- "키워드 마스터하기", "키워드 실전 전략", "키워드 핵심 포인트"
- "키워드 실무 노하우", "키워드 성공 비결", "키워드 전문가 되기"
- 연도는 정말 필요한 경우에만: "AI 기술 2025년 트렌드" (AI/기술 분야)

중요: 반드시 아래 JSON 형식을 정확히 따라주세요. 추가 설명 없이 JSON만 반환하세요.

{json_schema}
"""
        return prompt

    def _validate_title(
        self, title_result: GeneratedTitle, keyword: str, options: TitleOptions
    ) -> None:
        """생성된 제목 검증"""
        title = title_result.title

        # 길이 검증
        if not (options.min_length <= len(title) <= options.max_length):
            logger.warning(
                f"제목 길이 초과: {len(title)}자 (권장: {options.min_length}-{options.max_length}자)"
            )

        # 키워드 포함 검증
        if keyword.lower() not in title.lower():
            logger.warning(f"제목에 키워드 '{keyword}' 미포함")

        # SEO 점수 검증
        if title_result.seo_score < 5:
            logger.warning(f"낮은 SEO 점수: {title_result.seo_score}/10")

    def _create_fallback_title(
        self, keyword: str, options: TitleOptions
    ) -> GeneratedTitle:
        """LLM 실패 시 폴백 제목 생성"""
        fallback_title = f"{keyword} 완벽 가이드 (2025년 최신)"

        return GeneratedTitle(
            title=fallback_title,
            seo_score=6,
            keyword_density=0.2,
            reasoning="LLM 생성 실패로 인한 기본 템플릿 사용",
            alternatives=[
                f"{keyword} 총정리",
                f"{keyword} 5가지 핵심 포인트",
                f"초보자를 위한 {keyword} 가이드",
            ],
        )

    def generate_multiple_titles(
        self, keyword: str, count: int = 5, options: Optional[TitleOptions] = None
    ) -> List[GeneratedTitle]:
        """
        여러 개의 제목 후보 생성

        Args:
            keyword: 타겟 키워드
            count: 생성할 제목 개수
            options: 제목 생성 옵션

        Returns:
            List[GeneratedTitle]: 생성된 제목 목록
        """
        titles = []

        for i in range(count):
            try:
                # 각 제목마다 약간 다른 스타일로 생성
                modified_options = options or TitleOptions()
                if i % 2 == 0:
                    modified_options.include_numbers = True

                title = self.generate_title(keyword, modified_options)
                titles.append(title)

            except Exception as e:
                logger.error(f"제목 {i+1} 생성 실패: {e}")
                continue

        # SEO 점수 순으로 정렬
        titles.sort(key=lambda x: x.seo_score, reverse=True)

        logger.info(f"{len(titles)}개 제목 생성 완료")
        return titles
