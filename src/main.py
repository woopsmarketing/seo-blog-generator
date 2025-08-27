# src/main.py
# SEO 블로그 자동 생성 시스템 메인 엔트리포인트

import logging
import asyncio
import sys
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime

from src.generators.content.title_generator import TitleGenerator, TitleOptions
from src.generators.content.outline_generator import OutlineGenerator
from src.utils.config import load_config

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("logs/blog_generation.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)


@dataclass
class BlogGenerationRequest:
    """블로그 생성 요청 데이터"""

    keyword: str
    title_options: Optional[TitleOptions] = None
    output_format: str = "html"  # html, markdown, json
    save_to_file: bool = True


class BlogPipeline:
    """
    SEO 블로그 자동 생성 파이프라인

    단계:
    1. 키워드 → 제목 생성
    2. 키워드 + 제목 → 아웃라인 생성
    3. 아웃라인 → 섹션별 콘텐츠 생성
    4. HTML 조립
    5. WordPress 업로드 (선택사항)
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """파이프라인 초기화"""
        self.config = config or load_config()

        # 제네레이터 초기화
        self.title_generator = TitleGenerator(self.config)
        self.outline_generator = OutlineGenerator(self.config)

        logger.info("BlogPipeline 초기화 완료")

    async def generate_blog(self, request: BlogGenerationRequest) -> Dict[str, Any]:
        """
        완전한 블로그 글 생성

        Args:
            request: 블로그 생성 요청

        Returns:
            Dict: 생성 결과 및 메타데이터
        """
        start_time = datetime.now()
        logger.info(f"블로그 생성 시작: 키워드='{request.keyword}'")

        try:
            # 1단계: 제목 생성
            logger.info("1단계: SEO 최적화 제목 생성 중...")
            title_result = self.title_generator.generate_title(
                keyword=request.keyword, options=request.title_options
            )

            # 2단계: 아웃라인 생성
            logger.info("2단계: 블로그 아웃라인 생성 중...")
            outline = self.outline_generator.generate_outline(
                keyword=request.keyword,
                title=title_result.title,
            )

            # 3단계: 섹션별 콘텐츠 생성 (현재는 아웃라인만)
            logger.info("3단계: 섹션별 콘텐츠 생성 준비...")
            # TODO: SectionGenerator 구현 후 추가

            # 4단계: HTML 조립 (현재는 기본 구조만)
            logger.info("4단계: HTML 조립 중...")
            # TODO: HTMLAssembler 구현 후 추가

            # 결과 생성
            result = {
                "success": True,
                "title": title_result.title,
                "seo_score": title_result.seo_score,
                "outline": outline.model_dump(),
                "sections_count": len(outline.sections),
                "estimated_length": outline.meta.get("est_length", 0),
                "generation_time": (datetime.now() - start_time).total_seconds(),
                "timestamp": datetime.now().isoformat(),
            }

            # 파일 저장
            if request.save_to_file:
                await self._save_result(result, request.keyword)

            logger.info(f"블로그 생성 완료: {result['generation_time']:.2f}초")
            return result

        except Exception as e:
            logger.error(f"블로그 생성 실패: {e}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }

    async def _save_result(self, result: Dict[str, Any], keyword: str) -> None:
        """생성 결과를 파일에 저장"""
        try:
            # data 디렉토리 생성
            data_dir = Path("data")
            data_dir.mkdir(exist_ok=True)

            # 타임스탬프로 파일명 생성
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"blog_{keyword.replace(' ', '_')}_{timestamp}.json"

            # JSON 파일로 저장
            import json

            with open(data_dir / filename, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)

            logger.info(f"결과 저장: {filename}")

        except Exception as e:
            logger.error(f"결과 저장 실패: {e}")


async def main():
    """메인 실행 함수"""
    print("🚀 SEO 블로그 자동 생성 시스템")
    print("=" * 50)

    # 키워드 입력
    keyword = input("생성할 블로그의 키워드를 입력하세요: ").strip()

    if not keyword:
        print("❌ 키워드를 입력해주세요.")
        return

    # 파이프라인 초기화
    pipeline = BlogPipeline()

    # 생성 요청 설정
    request = BlogGenerationRequest(
        keyword=keyword,
        title_options=TitleOptions(
            max_length=60, include_numbers=True, include_year=True, tone="professional"
        ),
    )

    # 블로그 생성 실행
    print(f"\n📝 '{keyword}' 키워드로 블로그 생성 중...")
    result = await pipeline.generate_blog(request)

    # 결과 출력
    if result["success"]:
        print("\n✅ 블로그 생성 성공!")
        print(f"📌 제목: {result['title']}")
        print(f"⭐ SEO 점수: {result['seo_score']}/10")
        print(f"📊 섹션 수: {result['sections_count']}개")
        print(f"📏 예상 길이: {result['estimated_length']:,}자")
        print(f"⏱️ 생성 시간: {result['generation_time']:.2f}초")

        # 아웃라인 미리보기
        print(f"\n📋 아웃라인 미리보기:")
        outline = result["outline"]
        for i, section in enumerate(outline["sections"], 1):
            print(f"  {i}. {section['h2']}")
            for j, h3 in enumerate(section.get("h3", []), 1):
                print(f"     {i}.{j} {h3}")

    else:
        print(f"\n❌ 블로그 생성 실패: {result['error']}")


if __name__ == "__main__":
    # 로그 디렉토리 생성
    Path("logs").mkdir(exist_ok=True)

    # 비동기 실행
    asyncio.run(main())
