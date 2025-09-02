#!/usr/bin/env python3
"""
Enhanced RAG Pipeline for SEO Blog Generation - Clean Version
- Detailed cost analysis
- LSI and longtail keywords
- Structured HTML output
- Token tracking
"""

import sys
import os
import time
import json
import asyncio
import base64
import random
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Tuple, Optional
import re
from openai import OpenAI

# 프로젝트 루트 디렉토리를 Python 경로에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.utils.config import load_config
from src.utils.llm_factory import create_gpt5_nano, LLMFactory, LLMConfig
from src.utils.rag import SimpleRAG
from src.utils.image_optimizer import ImageOptimizer
from src.utils.external_link_builder import ExternalLinkBuilder
from src.utils.wordpress_poster import WordPressPoster, create_wordpress_poster
from src.utils.content_storage import ContentStorage, create_content_storage
from src.utils.internal_link_builder import (
    InternalLinkBuilder,
    create_internal_link_builder,
)
from langchain_core.messages import HumanMessage


class EnhancedRAGPipeline:
    """Enhanced RAG Pipeline with detailed analytics"""

    def __init__(self):
        self.config = load_config()
        self.llm = create_gpt5_nano()
        self.rag = None
        # OpenAI 클라이언트 초기화 (이미지 생성용)
        self.openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        # 이미지 최적화 도구 초기화
        self.image_optimizer = ImageOptimizer()
        # 외부링크 생성 도구 초기화
        self.external_link_builder = ExternalLinkBuilder()
        # 워드프레스 포스터 초기화 (옵션)
        self.wordpress_poster = None
        # 콘텐츠 저장소 초기화 (옵션)
        self.content_storage = None
        # 내부링크 빌더 초기화 (옵션)
        self.internal_link_builder = None
        self.cost_tracker = {
            "total_calls": 0,
            "total_tokens": {"prompt": 0, "completion": 0},
            "total_duration": 0,
            "total_images": 0,  # 이미지 생성 횟수 추적
            "step_details": [],
            "image_details": [],  # 이미지 생성 비용 추적
        }

    def _safe_fragment(self, text: str, max_len: int = 120) -> str:
        """윈도우 호환 파일명 조각 생성 (금지문자 제거/치환)"""
        frag = re.sub(r"[\\/:*?\"<>|]", "_", text)
        frag = re.sub(r"\s+", "_", frag)
        frag = frag.strip("._")
        if not frag:
            frag = "output"
        return frag[:max_len]

    def setup_rag(self, data_dir: str = "data"):
        """RAG 시스템 초기화"""
        data_path = project_root / data_dir
        if data_path.exists():
            self.rag = SimpleRAG(docs_dir=str(data_path))
            self.rag.build()
            return self.rag.vs is not None
        return False

    def track_llm_call(
        self,
        step_name: str,
        prompt_tokens: int,
        completion_tokens: int,
        duration: float,
        output: str,
        purpose: str,
    ):
        """LLM 호출 추적"""
        self.cost_tracker["total_calls"] += 1
        self.cost_tracker["total_tokens"]["prompt"] += prompt_tokens
        self.cost_tracker["total_tokens"]["completion"] += completion_tokens
        self.cost_tracker["total_duration"] += duration

        # GPT-5-nano 비용 계산 (추정)
        input_cost_per_1k = 0.00005  # $0.05 per 1M tokens = $0.00005 per 1K tokens
        output_cost_per_1k = 0.0004  # $0.40 per 1M tokens = $0.0004 per 1K tokens

        step_cost = (prompt_tokens * input_cost_per_1k / 1000) + (
            completion_tokens * output_cost_per_1k / 1000
        )

        self.cost_tracker["step_details"].append(
            {
                "step": step_name,
                "timestamp": datetime.now().strftime("%H:%M:%S"),
                "duration_seconds": duration,
                "tokens": {"prompt": prompt_tokens, "completion": completion_tokens},
                "estimated_cost_usd": step_cost,
                "purpose": purpose,
                "output_summary": output[:100] + "..." if len(output) > 100 else output,
            }
        )

    async def generate_title_keywords(self, keyword: str) -> Dict[str, Any]:
        """단일 호출: 제목, LSI 키워드, 롱테일 키워드 생성"""
        start_time = time.time()
        # 1단계: 키워드 먼저 생성
        keywords_prompt = f"""
메인 키워드: {keyword}

이 메인 키워드를 중심으로 아래를 생성하세요:

1) lsi_keywords: 의미적으로 연관된 LSI 키워드 5-10개 배열
2) longtail_keywords: 구체적인 롱테일 키워드 5-10개 배열

반드시 아래 형식의 JSON만 출력하세요:
{{
  "lsi_keywords": ["..."],
  "longtail_keywords": ["..."]
}}
"""
        print("   📝 1단계: LSI/롱테일 키워드 생성 중...")

        # 키워드 생성 호출
        messages = [HumanMessage(content=keywords_prompt)]
        keywords_response = self.llm.invoke(messages)

        try:
            import re, json as _json

            m = re.search(r"\{[\s\S]*\}$", keywords_response.content.strip())
            keywords_data = (
                _json.loads(m.group(0)) if m else _json.loads(keywords_response.content)
            )
            lsi_keywords = keywords_data.get("lsi_keywords", [])
            longtail_keywords = keywords_data.get("longtail_keywords", [])
        except Exception:
            lsi_keywords = [f"{keyword} 팁", f"{keyword} 방법"]
            longtail_keywords = [f"{keyword} 초보 가이드"]

        print("   📝 2단계: 제목 생성 중...")

        # 2단계: 키워드들을 조합해서 제목 생성 (최대 3번 시도)
        max_attempts = 3
        final_title = None

        for attempt in range(max_attempts):
            # 1단계: 제목 생성 (먼저 LLM 호출)
            all_keywords = [keyword] + lsi_keywords[:5] + longtail_keywords[:3]

            title_prompt = f"""
메인 키워드: {keyword}
LSI 키워드: {', '.join(lsi_keywords[:5])}
롱테일 키워드: {', '.join(longtail_keywords[:3])}

위 키워드들을 자연스럽게 조합하여 SEO 최적화된 블로그 제목을 만드세요.
- 메인 키워드는 반드시 포함
- LSI나 롱테일 키워드 1-2개도 자연스럽게 포함
- 60자 이내
- 클릭을 유도하는 매력적인 제목

제목만 출력하세요 (JSON이나 다른 형식 없이):
"""

            # 제목 생성
            title_messages = [HumanMessage(content=title_prompt)]
            title_response = self.llm.invoke(title_messages)
            generated_title = title_response.content.strip().strip('"')

            print(f"   📝 생성된 제목: {generated_title}")

            # 2단계: 기존 제목들과 유사도 검사
            avoid_titles = []
            if self.content_storage:
                try:
                    similar_posts = self.content_storage.find_similar_posts(
                        query_text=keyword,
                        k=5,
                        min_similarity_score=0.2,
                        search_titles_only=True,
                    )
                    avoid_titles = [post["metadata"]["title"] for post in similar_posts]
                    if avoid_titles:
                        print(
                            f"   📋 기존 제목 {len(avoid_titles)}개와 유사도 검사 중..."
                        )
                except Exception as e:
                    print(f"   ⚠️ 제목 중복 검사 실패: {e}")

            # 3단계: 유사도 검사 수행
            if avoid_titles:
                is_similar = False
                for existing_title in avoid_titles:
                    # 간단한 유사도 검사 (키워드 겹침 비율)
                    title_words = set(generated_title.lower().split())
                    existing_words = set(existing_title.lower().split())

                    intersection = len(title_words & existing_words)
                    union = len(title_words | existing_words)
                    similarity = intersection / union if union > 0 else 0

                    if similarity > 0.6:  # 60% 이상 유사하면
                        is_similar = True
                        print(
                            f"   ⚠️ 유사한 제목 발견 (유사도 {similarity:.1%}): {existing_title}"
                        )
                        break

                if not is_similar:
                    print(f"   ✅ 고유한 제목 생성 완료")
                    final_title = generated_title
                    break
                elif attempt < max_attempts - 1:
                    print(f"   🔄 제목 재생성 시도 {attempt + 2}/{max_attempts}")
            else:
                final_title = generated_title
                break

        if not final_title:
            final_title = generated_title  # 마지막 시도 결과 사용

        # 비용 추적
        duration = time.time() - start_time
        prompt_tokens = int(len(keywords_prompt.split()) * 1.3) + int(
            len(title_prompt.split()) * 1.3
        )
        completion_tokens = int(len(keywords_response.content.split()) * 1.3) + int(
            len(title_response.content.split()) * 1.3
        )

        self.track_llm_call(
            "generate_title_keywords",
            prompt_tokens,
            completion_tokens,
            duration,
            f"키워드: {len(lsi_keywords + longtail_keywords)}개, 제목: {final_title}",
            "키워드 먼저 생성 → 제목 조합 생성",
        )

        return {
            "title": final_title,
            "lsi_keywords": lsi_keywords,
            "longtail_keywords": longtail_keywords,
            "notes": f"메인 키워드 '{keyword}' 기반으로 LSI/롱테일 키워드를 먼저 생성한 후 제목을 조합 생성",
        }

    async def generate_structure_json(
        self, title: str, keyword: str, lsi: List[str], longtail: List[str]
    ) -> Dict[str, Any]:
        """블로그 구조 JSON 생성 (7-10개 H2 섹션, 개요+마무리+FAQ 포함)"""
        import random

        start_time = time.time()
        target_sections = random.randint(7, 10)
        joined = ", ".join((lsi or [])[:5] + (longtail or [])[:3])
        prompt = f"""
제목: {title}
키워드: {keyword}
연관 키워드: {joined}

아래 조건으로 블로그 문서 구조를 JSON으로 생성하세요.
- H2 섹션 수: 정확히 {target_sections}개
- 첫 번째 H2는 반드시 '개요', '소개', '시작하기' 중 하나의 성격을 가진 도입 섹션이어야 합니다 (자유롭게 표현 가능)
- 마지막에서 두 번째 H2는 '정리와 마무리', '요약과 결론', '핵심 포인트' 등 전체 내용을 요약하는 섹션이어야 합니다
- 마지막 H2는 반드시 '자주 묻는 질문', 'FAQ', '궁금한 점들' 등 질문-답변 형태의 섹션이어야 합니다
- 각 H2마다 H3/H4는 유동적으로 0개 이상 포함 가능
- 한국어 제목 사용, 키워드는 자연스럽게 포함

반환 형식 예시:
{{
  "title": "{title}",
  "sections": [
    {{
      "h2": "섹션 제목",
      "h3": ["소제목1", "소제목2"],
      "h4_map": {{"소제목1": ["항목1", "항목2"]}}
    }}
  ]
}}
반드시 위의 JSON 스키마만 출력하세요.
"""
        # 구조 중복 방지를 위한 RAG 검색 제거 - 제목 중복 검사로 충분함

        messages = [HumanMessage(content=prompt)]
        response = self.llm.invoke(messages)
        duration = time.time() - start_time
        prompt_tokens = int(len(prompt.split()) * 1.3)
        completion_tokens = int(len(response.content.split()) * 1.3)

        self.track_llm_call(
            "structure_generation",
            prompt_tokens,
            completion_tokens,
            duration,
            response.content,
            "7-10개의 H2와 유동 H3/H4 구조 JSON (개요+마무리+FAQ 포함)",
        )

        try:
            import re, json as _json

            m = re.search(r"\{[\s\S]*\}$", response.content.strip())
            data = _json.loads(m.group(0)) if m else _json.loads(response.content)
            return data
        except Exception:
            return {"title": title, "sections": []}

    async def summarize_previous(self, text: str) -> str:
        """이전 섹션 내용 요약"""
        prompt = f"""
다음 텍스트의 핵심만 2-3문장으로 한국어 요약:
---
{text}
---
요약:
"""
        messages = [HumanMessage(content=prompt)]
        response = self.llm.invoke(messages)
        return response.content.strip()

    async def generate_image(self, prompt: str, purpose: str) -> Optional[str]:
        """이미지 생성 (gpt-image-1 모델 사용)

        Args:
            prompt: 이미지 생성을 위한 영문 프롬프트
            purpose: 이미지 용도 (cost tracking용)

        Returns:
            생성된 이미지의 base64 문자열 또는 None
        """
        try:
            start_time = time.time()

            # OpenAI Image API 호출 (gpt-image-1은 항상 base64로 반환)
            response = self.openai_client.images.generate(
                model="gpt-image-1",
                prompt=prompt,
                quality="low",  # 저품질 (가격 효율성)
                size="1024x1024",  # 표준 사이즈
                n=1,  # 1개 이미지
            )

            duration = time.time() - start_time

            # 비용 계산 (gpt-image-1 low quality 1024x1024: $0.011)
            image_cost = 0.011

            # 이미지 생성 추적
            self.cost_tracker["total_images"] += 1
            self.cost_tracker["image_details"].append(
                {
                    "purpose": purpose,
                    "timestamp": datetime.now().strftime("%H:%M:%S"),
                    "duration_seconds": duration,
                    "prompt": prompt[:100] + "..." if len(prompt) > 100 else prompt,
                    "cost_usd": image_cost,
                    "model": "gpt-image-1",
                    "quality": "low",
                    "size": "1024x1024",
                }
            )

            # base64 이미지 데이터 반환 (gpt-image-1은 항상 b64_json 형태)
            return response.data[0].b64_json

        except Exception as e:
            print(f"이미지 생성 실패 ({purpose}): {e}")
            return None

    def save_image_from_base64(
        self, b64_data: str, file_path: Path, optimize: bool = True
    ) -> bool:
        """base64 이미지 데이터를 파일로 저장 및 최적화

        Args:
            b64_data: base64 인코딩된 이미지 데이터
            file_path: 저장할 파일 경로
            optimize: 이미지 최적화 여부

        Returns:
            저장 성공 여부
        """
        try:
            # base64 디코딩하여 PNG 파일로 저장
            image_data = base64.b64decode(b64_data)
            file_path.parent.mkdir(exist_ok=True)

            with open(file_path, "wb") as f:
                f.write(image_data)

            # 이미지 최적화 (옵션)
            if optimize:
                # 블로그용 최적화: 512x512 이하, 50KB 이하로 압축
                optimization_result = self.image_optimizer.optimize_for_web(
                    file_path,
                    max_size=(512, 512),
                    target_file_size_kb=50,
                    quality_range=(70, 90),
                )

                if optimization_result["success"]:
                    reduction = optimization_result["size_reduction_percent"]
                    print(
                        f"     📉 이미지 최적화: {optimization_result['file_size_change']} ({reduction}% 감소)"
                    )
                else:
                    print(
                        f"     ⚠️ 이미지 최적화 실패: {optimization_result.get('error', '알 수 없는 오류')}"
                    )

            return True
        except Exception as e:
            print(f"이미지 저장 실패: {e}")
            return False

    async def generate_and_save_images(
        self,
        title: str,
        sections: List[Dict],
        keyword: str,
        lsi_keywords: List[str] = None,
        longtail_keywords: List[str] = None,
    ) -> Dict[str, str]:
        """메인 및 섹션별 이미지 생성 및 저장

        Args:
            title: 블로그 제목
            sections: 섹션 리스트
            keyword: 메인 키워드
            lsi_keywords: LSI 키워드 리스트
            longtail_keywords: 롱테일 키워드 리스트

        Returns:
            이미지 경로 딕셔너리 {"main": "path", "section_1": "path", ...}
        """
        images = {}
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_keyword = self._safe_fragment(keyword)
        images_dir = project_root / "data" / "images"
        images_dir.mkdir(parents=True, exist_ok=True)

        # 1. 메인 이미지 생성 (100% 확률)
        print("4. 이미지 생성 중...")
        main_prompt = f"Create a professional diagram or infographic about '{title}'. Chart, concept diagram, or infographic style. No text or words in the image. Clean, modern design."

        main_image_data = await self.generate_image(
            main_prompt, f"메인 이미지: {title}"
        )
        if main_image_data:
            main_image_path = images_dir / f"main_{safe_keyword}_{timestamp}.png"
            if self.save_image_from_base64(
                main_image_data, main_image_path, optimize=True
            ):
                images["main"] = str(main_image_path)
                print(f"   ✅ 메인 이미지 생성: {main_image_path.name}")

        # 2. 섹션별 이미지 생성 (33% 확률)
        for i, section in enumerate(sections):
            if random.random() <= 0.33:  # 33% 확률
                section_title = section.get("h2_title", f"섹션 {i+1}")
                section_prompt = f"Create a diagram or concept illustration about '{section_title}'. Professional infographic style. No text or words. Clean design."

                section_image_data = await self.generate_image(
                    section_prompt, f"섹션 이미지: {section_title}"
                )
                if section_image_data:
                    section_image_path = (
                        images_dir / f"section_{i+1}_{safe_keyword}_{timestamp}.png"
                    )
                    if self.save_image_from_base64(
                        section_image_data, section_image_path, optimize=True
                    ):
                        images[f"section_{i+1}"] = str(section_image_path)
                        print(
                            f"   ✅ 섹션 {i+1} 이미지 생성: {section_image_path.name}"
                        )

        return images

    def generate_table_of_contents(self, sections_content: List[Dict]) -> str:
        """H2 기반 목차 생성 (앵커 링크 포함, 핵심 용어 정리 포함)"""
        toc_lines = ["## 📚 목차\n"]

        # 첫 번째: 핵심 용어 정리
        toc_lines.append("1. [핵심 용어 정리](#핵심-용어-정리)")

        # 나머지 섹션들 (번호 +1)
        for i, section in enumerate(sections_content, 2):  # 2부터 시작
            h2_title = section.get("h2_title", f"섹션 {i}")
            # 마크다운 앵커 링크 생성 (한글 -> 영어, 공백 -> 하이픈)
            anchor_id = (
                h2_title.lower()
                .replace(" ", "-")
                .replace(":", "")
                .replace("?", "")
                .replace("!", "")
            )
            # 한글은 그대로 유지하되 특수문자만 제거
            anchor_id = (
                h2_title.replace(" ", "-")
                .replace(":", "")
                .replace("?", "")
                .replace("!", "")
                .replace(",", "")
                .replace(".", "")
            )
            toc_lines.append(f"{i}. [{h2_title}](#{anchor_id})")

        return "\n".join(toc_lines) + "\n"

    async def extract_and_explain_terms(self, full_content: str, keyword: str) -> str:
        """콘텐츠에서 어려운 용어 추출 및 설명 생성"""
        start_time = time.time()

        prompt = f"""
다음은 '{keyword}' 주제의 블로그 콘텐츠입니다.
초보자나 중급자가 읽을 때 이해하기 어려울 수 있는 전문 용어를 5-8개 선별하고, 각각을 한 줄로 쉽게 설명해주세요.

=== 블로그 콘텐츠 ===
{full_content[:4000]}  # 토큰 제한을 위해 일부만 사용

=== 작업 지시 ===
1. 위 콘텐츠에서 초보자가 모를 만한 전문 용어를 선별하세요
2. 각 용어를 한 줄(25자 이내)로 간단명료하게 설명하세요
3. 중복 용어나 너무 쉬운 용어는 제외하세요
4. 반드시 아래 형식으로만 출력하세요

=== 출력 형식 (예시) ===
크롤링: 검색엔진이 웹페이지를 읽어가는 과정
백링크: 다른 사이트에서 내 사이트로 연결되는 링크
메타태그: 검색엔진에게 페이지 정보를 알려주는 코드
인덱싱: 검색엔진이 페이지를 데이터베이스에 저장하는 작업
앵커텍스트: 링크에 표시되는 클릭 가능한 텍스트

위 형식으로 용어와 설명만 출력하세요:
"""

        messages = [HumanMessage(content=prompt)]
        response = self.llm.invoke(messages)

        # 용어 섹션 포맷팅 (앙커 ID 포함)
        terms_section = '<h2 id="terms-section">📖 핵심 용어 정리</h2>\n\n'
        terms_section += "본문을 읽기 전에 알아두면 좋은 용어들입니다.\n\n"

        # LLM 응답을 파싱하여 용어 정리 (개선된 파싱)
        response_text = response.content.strip()
        lines = response_text.split("\n")
        terms_found = 0

        print(f"   🔍 LLM 응답 길이: {len(response_text)}자")
        print(f"   📝 응답 라인 수: {len(lines)}개")
        print(f"   📄 LLM 원본 응답:")
        print(f"   {response_text}")
        print("   " + "=" * 50)

        for line in lines:
            line = line.strip()
            # 불필요한 텍스트 제거
            if any(
                skip in line.lower()
                for skip in ["출력 형식", "예시", "작업 지시", "블로그 콘텐츠", "==="]
            ):
                continue

            if ":" in line and len(line) > 8:  # 최소 길이 체크 강화
                try:
                    # 콜론으로 분할
                    parts = line.split(":", 1)
                    if len(parts) == 2:
                        term = (
                            parts[0]
                            .strip()
                            .replace("**", "")
                            .replace("-", "")
                            .replace("*", "")
                            .strip()
                        )
                        explanation = parts[1].strip()

                        # 유효성 검사
                        if (
                            term
                            and explanation
                            and len(term) > 1
                            and len(explanation) > 5
                            and not term.isdigit()
                        ):  # 숫자만인 용어 제외
                            terms_section += f"**{term}**: {explanation}\n\n"
                            terms_found += 1
                            print(f"   ✅ 용어 추가: {term}")
                except Exception as e:
                    print(f"   ⚠️ 파싱 오류: {line[:50]}...")
                    continue

        print(f"   📊 총 추출된 용어: {terms_found}개")

        # 용어가 하나도 추출되지 않았다면 기본 용어 추가
        if terms_found == 0:
            print("   🔄 기본 용어로 대체")
            terms_section += f"**{keyword}**: 이 글의 주요 주제입니다\n\n"
            terms_section += (
                f"**SEO**: 검색엔진 최적화로 웹사이트 노출을 높이는 기법\n\n"
            )
            terms_section += f"**키워드**: 검색할 때 사용하는 단어나 문구\n\n"

        duration = time.time() - start_time
        self.track_llm_call(
            "extract_terms",
            int(len(prompt.split()) * 1.3),
            int(len(response.content.split()) * 1.3),
            duration,
            f"용어 {terms_found}개 추출",
            "어려운 용어 추출 및 설명",
        )

        print(f"   📏 최종 terms_section 길이: {len(terms_section)}자")
        print(f"   📄 최종 terms_section 미리보기:")
        print(f"   {terms_section[:300]}...")

        return terms_section

    def cleanup_images_folder(self):
        """이미지 폴더 정리 (생성된 이미지들 삭제)"""
        try:
            images_dir = project_root / "data" / "images"
            if not images_dir.exists():
                return

            # .png 파일들만 삭제 (다른 파일은 보존)
            deleted_count = 0
            for image_file in images_dir.glob("*.png"):
                try:
                    image_file.unlink()
                    deleted_count += 1
                except Exception as e:
                    print(f"   ⚠️ 이미지 삭제 실패: {image_file.name} - {e}")

            if deleted_count > 0:
                print(f"   🗑️ 이미지 폴더 정리 완료: {deleted_count}개 파일 삭제")

        except Exception as e:
            print(f"   ⚠️ 이미지 폴더 정리 실패: {e}")

    async def generate_section_with_context(
        self,
        idx: int,
        total: int,
        section: Dict[str, Any],
        keyword: str,
        title: str,
        full_structure_json: Dict[str, Any],
        prev_summary: str = "",
        next_h2: str = "",
        lsi_keywords: List[str] = None,
        longtail_keywords: List[str] = None,
    ) -> Tuple[str, List[str]]:
        """섹션별 콘텐츠 생성 (컨텍스트와 티저 포함, 사용된 키워드 반환)"""
        start_time = time.time()
        structure_str = json.dumps(full_structure_json, ensure_ascii=False)
        ctx = f"이전 섹션 요약: {prev_summary}\n" if prev_summary else ""

        # 티저 문장 가이드 (명시적 표현 금지)
        teaser = (
            f"마지막 문장은 '{next_h2}'와 주제가 맞닿아 있음을 독자가 암시적으로 느끼도록, 구체적 정보 한 조각으로 마무리하세요. \n- 금지 표현: '다음', '다음 섹션', '다음 챕터', '자연스럽게 이어집니다'"
            if next_h2
            else ""
        )

        # 길이 정책: 1섹션 300자 내외, 그 외 500-800자
        length_rule = "분량: 약 300자" if idx == 1 else "분량: 500-800자"

        # LSI/롱테일 키워드를 섹션별로 매번 새로 랜덤 선택 (0-1개씩)
        import random

        section_keywords = []

        # LSI 키워드에서 0-1개 랜덤 선택 (매 섹션마다)
        if lsi_keywords and random.random() < 0.6:  # 60% 확률로 LSI 키워드 포함
            selected_lsi = random.choice(lsi_keywords)
            section_keywords.append(selected_lsi)

        # 롱테일 키워드에서 0-1개 랜덤 선택 (매 섹션마다)
        if longtail_keywords and random.random() < 0.4:  # 40% 확률로 롱테일 키워드 포함
            selected_longtail = random.choice(longtail_keywords)
            section_keywords.append(selected_longtail)

        # 키워드 정보 구성
        keywords_info = f"주요 키워드: {keyword}"
        if section_keywords:
            keywords_info += (
                f"\n섹션 관련 키워드 (자연스럽게 포함): {', '.join(section_keywords)}"
            )

        prompt = f"""
문서 제목: {title}
{keywords_info}
전체 문서 구조(JSON): {structure_str}
현재 섹션: {idx}/{total} - H2: {section.get('h2')}
{ctx}
요구사항:
1) 한국어 자연스러운 본문
2) H3 소제목 2-3개 포함 가능 (있다면 Markdown ### 사용)
3) 실용적이고 구체적인 내용
4) {length_rule}
5) {teaser}
6) 출력은 "본문만" 작성. 섹션 제목이나 H2(##)를 출력하지 말 것. '섹션 본문:' 같은 안내 문구도 금지.
7) 첫 줄에 섹션 제목을 반복하지 말 것. 필요 시 H3(###)부터 시작.
8) 표 형태로 표현하면 더 효과적인 내용이 있다면 Markdown 표 문법 사용:
   - 비교표: | 항목 | 설명 | 비고 |
   - 단계별 표: | 단계 | 내용 | 팁 |
   - 특징표: | 특징 | 장점 | 단점 |
   - 예시: | 구분 | 방법 | 효과 |
   - 도구 비교: | 도구명 | 장점 | 단점 | 가격 |
   - 단계별 가이드: | 단계 | 설명 | 주의사항 |
   - 팁 정리: | 상황 | 해결방법 | 효과 |

본문 출력 시작:
"""
        # RAG 검색 제거 - 독창적인 콘텐츠 생성을 위해
        # if self.rag and self.rag.vs:
        #     rag_context = self.rag.query(f"{keyword} {section.get('h2','')} 배경", k=2)
        #     prompt = f"{rag_context}\n\n{prompt}"

        messages = [HumanMessage(content=prompt)]
        response = self.llm.invoke(messages)
        duration = time.time() - start_time
        prompt_tokens = int(len(prompt.split()) * 1.3)
        completion_tokens = int(len(response.content.split()) * 1.3)

        self.track_llm_call(
            f"section_{idx}",
            prompt_tokens,
            completion_tokens,
            duration,
            response.content,
            f"섹션 {idx} 본문 생성",
        )

        return response.content.strip(), section_keywords

    def _sanitize_section_content(self, h2_title: str, content: str) -> str:
        """모델 응답에서 중복 H2/안내문 등을 제거하여 깔끔한 본문만 남긴다."""
        lines = [ln.rstrip() for ln in content.strip().split("\n")]
        sanitized: list[str] = []
        skip_prefixes = {
            "섹션 본문:",
            "본문:",
            "본문 출력:",
            "본문 출력 시작:",
            "내용:",
        }

        for i, ln in enumerate(lines):
            # 첫 부분에서만 강제 제거 규칙 적용
            if i < 5:
                # '섹션 본문:' 류 안내문 제거
                if any(ln.strip().startswith(p) for p in skip_prefixes):
                    continue
                # 중복 H2 제거 (## ...)
                if ln.strip().startswith("## "):
                    continue
                # 섹션 제목 반복 텍스트 제거 (제목만 단독 라인)
                if ln.strip() == h2_title.strip():
                    continue
            sanitized.append(ln)

        # 앞뒤 공백 정리 및 연속 빈 줄 축소
        out = "\n".join(sanitized).strip()
        out = re.sub(r"\n\s*\n\s*\n+", "\n\n", out)
        return out

    def create_markdown(
        self,
        title: str,
        keyword: str,
        sections_content: List[Dict[str, Any]],
        keywords: Dict[str, List[str]],
        images: Optional[Dict[str, str]] = None,
        table_of_contents: str = "",
        terms_section: str = "",
    ) -> str:
        """마크다운 형식 생성 (목차, 용어 정리, 이미지 포함)"""
        md_content = f"# {title}\n\n"
        # 1. 목차 추가 (최상단)
        if table_of_contents:
            md_content += table_of_contents + "\n"

        # 2. 메인 이미지 추가 (목차 다음)
        if images and "main" in images:
            md_content += f'![{title}]({images["main"]})\n\n'

        # 3. 용어 정리 추가 (이미지 다음)
        print(f"   🔧 create_markdown에서 terms_section 길이: {len(terms_section)}자")
        if terms_section:
            print(f"   ✅ terms_section을 마크다운에 추가")
            md_content += terms_section + "\n"
        else:
            print(f"   ❌ terms_section이 비어있음!")

        # 4. 본문 섹션들 (마크다운 헤더로 생성, HTML 변환기에서 ID 추가)
        for i, section in enumerate(sections_content):
            # 마크다운 H2 헤더로 생성
            md_content += f'## {section["h2_title"]}\n\n'

            # 섹션 이미지 추가 (20% 확률로)
            section_image_key = f"section_{i+1}"
            if images and section_image_key in images:
                md_content += (
                    f'![{section["h2_title"]}]({images[section_image_key]})\n\n'
                )

            md_content += f"{section['content']}\n\n"

        return md_content

    def create_cost_analysis_report(
        self,
        keyword: str,
        title: str,
        keywords: Dict,
        sections_content: List,
        total_duration: float,
    ) -> Dict[str, Any]:
        """상세한 비용 분석 보고서 생성"""
        # 텍스트 생성 비용
        text_cost = sum(
            step["estimated_cost_usd"] for step in self.cost_tracker["step_details"]
        )
        # 이미지 생성 비용
        image_cost = sum(img["cost_usd"] for img in self.cost_tracker["image_details"])
        total_cost = text_cost + image_cost

        total_tokens = (
            self.cost_tracker["total_tokens"]["prompt"]
            + self.cost_tracker["total_tokens"]["completion"]
        )

        report = {
            "report_info": {
                "keyword": keyword,
                "title": title,
                "generation_date": datetime.now().isoformat(),
                "report_version": "2.0 - Enhanced RAG Pipeline",
            },
            "cost_analysis": {
                "pipeline_summary": {
                    "model_used": "gpt-5-nano + gpt-image-1",
                    "total_duration_seconds": round(total_duration, 1),
                    "sections_generated": len(sections_content),
                    "images_generated": self.cost_tracker["total_images"],
                    "total_estimated_cost_usd": round(total_cost, 6),
                    "text_cost_usd": round(text_cost, 6),
                    "image_cost_usd": round(image_cost, 6),
                    "cost_per_section": (
                        round(total_cost / len(sections_content), 6)
                        if sections_content
                        else 0
                    ),
                    "estimated_total_tokens": total_tokens,
                    "status": "completed",
                },
                "llm_call_breakdown": {},
                "step_by_step_analysis": {},
                "cost_optimization_analysis": {
                    "current_efficiency": {
                        "model": "gpt-5-nano",
                        "input_cost_per_1m_tokens": "$0.05",
                        "output_cost_per_1m_tokens": "$0.40",
                        "average_cost_per_section": (
                            f"${round(total_cost / len(sections_content), 6)}"
                            if sections_content
                            else "$0"
                        ),
                        "total_sections_possible_with_1_dollar": (
                            int(1 / (total_cost / len(sections_content)))
                            if sections_content and total_cost > 0
                            else 0
                        ),
                    }
                },
            },
            "keyword_analysis": {
                "primary_keyword": keyword,
                "lsi_keywords": keywords.get("lsi_keywords", []),
                "longtail_keywords": keywords.get("longtail_keywords", []),
                "keyword_density": "자연스럽게 배치됨",
            },
            "content_analysis": {"sections": []},
            "model_configuration": {
                "primary_model": "gpt-5-nano",
                "temperature": 1.0,
                "max_tokens": "unlimited",
                "provider": "OpenAI",
                "rag_enabled": self.rag is not None and self.rag.vs is not None,
            },
            "performance_metrics": {
                "tokens_per_second": (
                    round(total_tokens / total_duration, 1) if total_duration > 0 else 0
                ),
                "cost_per_minute": (
                    f"${round(total_cost * 60 / total_duration, 6)}"
                    if total_duration > 0
                    else "$0"
                ),
                "characters_generated": sum(
                    len(section["content"]) for section in sections_content
                ),
                "cost_per_character": (
                    f"${round(total_cost / sum(len(section['content']) for section in sections_content), 8)}"
                    if sections_content
                    else "$0"
                ),
            },
        }

        # 단계별 분석 추가 (텍스트)
        for i, step in enumerate(self.cost_tracker["step_details"], 1):
            report["cost_analysis"]["step_by_step_analysis"][
                f"step_{i}_{step['step']}"
            ] = {
                "timestamp": step["timestamp"],
                "duration": f"{step['duration_seconds']:.1f}초",
                "model_calls": 1,
                "cost": f"${step['estimated_cost_usd']:.6f}",
                "output": step["output_summary"],
                "type": "text_generation",
            }

        # 이미지 생성 분석 추가
        for i, img in enumerate(self.cost_tracker["image_details"], 1):
            report["cost_analysis"]["step_by_step_analysis"][
                f"image_{i}_{img['purpose']}"
            ] = {
                "timestamp": img["timestamp"],
                "duration": f"{img['duration_seconds']:.1f}초",
                "model_calls": 1,
                "cost": f"${img['cost_usd']:.3f}",
                "output": img["prompt"],
                "type": "image_generation",
                "model": img["model"],
                "quality": img["quality"],
                "size": img["size"],
            }

        # 섹션별 분석 추가
        for i, section in enumerate(sections_content):
            report["content_analysis"]["sections"].append(
                {
                    "section_number": i + 1,
                    "h2_title": section["h2_title"],
                    "character_count": len(section["content"]),
                    "estimated_tokens": len(section["content"].split()) * 1.3,
                    "h3_count": section["content"].count("### "),
                    "keywords_used": section.get("target_keywords", []),
                }
            )

        return report

    def setup_wordpress(self) -> bool:
        """워드프레스 연결 설정 및 테스트"""
        try:
            self.wordpress_poster = create_wordpress_poster()
            return self.wordpress_poster.test_connection()
        except Exception as e:
            print(f"워드프레스 설정 실패: {e}")
            return False

    def setup_content_storage(self) -> bool:
        """콘텐츠 저장소 설정"""
        try:
            self.content_storage = create_content_storage()
            stats = self.content_storage.get_storage_stats()
            print(f"   콘텐츠 저장소: {stats['total_posts']}개 포스트 저장됨")

            # 내부링크 빌더도 함께 설정 (콘텐츠 저장소가 있을 때만)
            if self.content_storage and stats["total_posts"] > 0:
                self.internal_link_builder = create_internal_link_builder(
                    self.content_storage
                )
                print(
                    f"   내부링크 빌더: 활성화 ({stats['total_posts']}개 포스트 기반)"
                )
            else:
                print(f"   내부링크 빌더: 비활성화 (저장된 포스트 없음)")

            return True
        except Exception as e:
            print(f"콘텐츠 저장소 설정 실패: {e}")
            return False

    async def upload_to_wordpress(
        self,
        title: str,
        html_content: str,
        keyword: str,
        lsi_keywords: List[str] = None,
        longtail_keywords: List[str] = None,
        images_dir: Optional[Path] = None,
    ) -> Optional[Dict[str, Any]]:
        """워드프레스에 콘텐츠 업로드"""
        if not self.wordpress_poster:
            print("⚠️ 워드프레스가 설정되지 않음. setup_wordpress()를 먼저 호출하세요.")
            return None

        try:
            print("9. 워드프레스 업로드 중...")

            # 이미지가 있는 경우 HTML 콘텐츠 내 이미지 URL 교체
            if images_dir and images_dir.exists():
                html_content = self.wordpress_poster.process_images_in_content(
                    html_content, images_dir
                )

            # 카테고리 자동 선별
            all_keywords = [keyword]
            if lsi_keywords:
                all_keywords.extend(lsi_keywords)
            if longtail_keywords:
                all_keywords.extend(longtail_keywords)

            categories = self.wordpress_poster.select_best_categories(
                title=title, content=html_content, keywords=all_keywords
            )

            # 태그 설정
            tags = [keyword]  # 주요 키워드를 태그로

            # LSI 키워드를 태그로 추가 (처음 5개만)
            if lsi_keywords:
                tags.extend(lsi_keywords[:5])

            # 롱테일 키워드 중 짧은 것들을 태그로 추가 (처음 3개만)
            if longtail_keywords:
                short_longtails = [lt for lt in longtail_keywords[:3] if len(lt) < 20]
                tags.extend(short_longtails)

            # 중복 제거
            tags = list(set(tags))

            # 대표 이미지 설정 (메인 이미지가 있는 경우)
            featured_image_path = None
            if images_dir:
                main_image_files = list(images_dir.glob("main_*.png"))
                if main_image_files:
                    featured_image_path = main_image_files[0]

            # 워드프레스에 포스트 업로드
            result = self.wordpress_poster.post_article(
                title=title,
                html_content=html_content,
                status="publish",  # 즉시 발행
                category_names=categories,
                tag_names=tags,
                excerpt=f"{keyword}에 대한 완벽한 가이드입니다.",
                featured_image_path=featured_image_path,
            )

            if result:
                print(f"   ✅ 워드프레스 업로드 성공!")
                print(f"   📄 포스트 ID: {result['id']}")
                print(f"   🔗 URL: {result['url']}")
                return result
            else:
                print(f"   ❌ 워드프레스 업로드 실패")
                return None

        except Exception as e:
            print(f"워드프레스 업로드 중 오류: {e}")
            return None

    async def run_complete_pipeline(
        self, keyword: str, upload_to_wp: bool = False
    ) -> Dict[str, Any]:
        """완전한 RAG 파이프라인 실행"""
        start_time = time.time()

        print(f"키워드 '{keyword}'로 Enhanced RAG 파이프라인 시작")
        print("=" * 60)

        try:
            # 1. RAG 설정
            rag_enabled = self.setup_rag()
            print(f"1. RAG 시스템: {'활성화' if rag_enabled else '비활성화'}")

            # 워드프레스 설정 (업로드가 요청된 경우)
            wp_ready = False
            if upload_to_wp:
                wp_ready = self.setup_wordpress()
                print(f"   워드프레스: {'연결됨' if wp_ready else '연결 실패'}")

            # 콘텐츠 저장소 설정 (항상 활성화)
            storage_ready = self.setup_content_storage()

            # 2. 단일 호출: 제목+키워드 JSON
            print("2. 제목/키워드 단일 JSON 생성 중...")
            tk = await self.generate_title_keywords(keyword)
            print(f"   제목: {tk['title']}")

            # 저장 (STEP1)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_kw = self._safe_fragment(keyword)
            step1_file = (
                project_root / f"data/title_keywords_{safe_kw}_{timestamp}.json"
            )
            with open(step1_file, "w", encoding="utf-8") as f:
                json.dump(tk, f, ensure_ascii=False, indent=2)
            alias_step1 = project_root / f"data/OUTPUT_{safe_kw}_step1.json"
            with open(alias_step1, "w", encoding="utf-8") as f:
                json.dump(tk, f, ensure_ascii=False, indent=2)

            # 3. 구조 JSON (7-10개 H2)
            print("3. 구조(JSON) 생성 중...")
            structure = await self.generate_structure_json(
                tk["title"],
                keyword,
                tk.get("lsi_keywords", []),
                tk.get("longtail_keywords", []),
            )
            step2_file = project_root / f"data/structure_{safe_kw}_{timestamp}.json"
            with open(step2_file, "w", encoding="utf-8") as f:
                json.dump(structure, f, ensure_ascii=False, indent=2)
            alias_step2 = project_root / f"data/OUTPUT_{safe_kw}_structure.json"
            with open(alias_step2, "w", encoding="utf-8") as f:
                json.dump(structure, f, ensure_ascii=False, indent=2)

            sections = structure.get("sections", [])
            print(f"   섹션 수: {len(sections)}개")

            # 4. 섹션별 본문 생성 (연쇄 요약 사용)
            print("4. 섹션별 콘텐츠 생성 중...")
            sections_content = []
            prev_summary = ""
            all_section_keywords = []  # 섹션별 사용된 키워드 추적
            total = len(sections)

            for i, sec in enumerate(sections, 1):
                next_h2 = sections[i]["h2"] if i < total else ""
                raw, section_keywords = await self.generate_section_with_context(
                    idx=i,
                    total=total,
                    section=sec,
                    keyword=keyword,
                    title=tk["title"],
                    full_structure_json=structure,
                    prev_summary=prev_summary,
                    next_h2=next_h2,
                    lsi_keywords=tk.get("lsi_keywords", []),
                    longtail_keywords=tk.get("longtail_keywords", []),
                )

                # 섹션별 사용된 키워드 저장
                all_section_keywords.extend(section_keywords)

                # 모델 응답 후 정리: 중복 H2/안내문 제거
                content = self._sanitize_section_content(sec.get("h2", ""), raw)
                sections_content.append(
                    {
                        "h2_title": sec.get("h2", f"섹션 {i}"),
                        "content": content,
                        "target_keywords": [],
                    }
                )

                # 다음을 위한 요약 생성
                prev_summary = await self.summarize_previous(content)

            # 5. 외부링크 생성 (초기 콘텐츠용)
            print("5. 외부링크 생성 중...")
            content_count = 1  # TODO: 실제 콘텐츠 수 추적 시스템 구현 예정

            # 임시 마크다운 생성 (키워드 추출용)
            temp_md_content = self.create_markdown(
                tk["title"],
                keyword,
                sections_content,
                {
                    "lsi_keywords": tk.get("lsi_keywords", []),
                    "longtail_keywords": tk.get("longtail_keywords", []),
                },
                {},  # 이미지는 빈 딕셔너리로
                "",  # 목차는 빈 문자열 (키워드 추출용이므로 불필요)
                "",  # 용어 정리도 빈 문자열 (아직 생성되지 않았으므로)
            )

            # 섹션별로 실제 사용된 키워드 수집 (더 정확한 추적)
            all_used_keywords = []

            # 메인 키워드 (항상 포함)
            all_used_keywords.append((keyword, "메인"))

            # 섹션별 키워드 분류 및 추가
            lsi_used = set()
            longtail_used = set()

            for kw in all_section_keywords:
                if kw in tk.get("lsi_keywords", []):
                    lsi_used.add(kw)
                elif kw in tk.get("longtail_keywords", []):
                    longtail_used.add(kw)

            # 실제 사용된 키워드 추가
            for kw in lsi_used:
                all_used_keywords.append((kw, "LSI"))
            for kw in longtail_used:
                all_used_keywords.append((kw, "롱테일"))

            # 키워드 사용량 정리 (백업용으로 기존 방식도 유지)
            used_keywords = {
                "keyword": keyword,
                "lsi_keywords": list(lsi_used),
                "longtail_keywords": list(longtail_used),
            }

            print(f"   📊 실제 사용된 키워드: {len(all_used_keywords)}개")
            print(f"     - 메인: 1개")
            print(
                f"     - LSI: {len(used_keywords.get('lsi_keywords', []))}개 (전체 {len(tk.get('lsi_keywords', []))}개 중)"
            )
            print(
                f"     - 롱테일: {len(used_keywords.get('longtail_keywords', []))}개 (전체 {len(tk.get('longtail_keywords', []))}개 중)"
            )

            # 사용된 키워드 상세 표시
            if all_used_keywords:
                used_kw_list = [f"{kw}({kw_type})" for kw, kw_type in all_used_keywords]
                print(f"     - 사용된 키워드 목록: {', '.join(used_kw_list)}")

            # 5-1. 내부링크 우선 생성 (사용된 모든 키워드 대상)
            internal_links = []
            internal_keywords = []  # 실제로 내부링크에 사용된 키워드들

            if self.internal_link_builder and all_used_keywords:
                print(
                    f"   🔗 내부링크 생성 중... (사용 키워드 {len(all_used_keywords)}개 검사)"
                )

                # 임시 포스트 ID 생성
                temp_post_id = f"temp_{int(time.time())}"

                # 모든 사용된 키워드로 내부링크 생성 시도
                all_keywords_data = {
                    "lsi_keywords": [
                        kw for kw, kw_type in all_used_keywords if kw_type == "LSI"
                    ],
                    "longtail_keywords": [
                        kw for kw, kw_type in all_used_keywords if kw_type == "롱테일"
                    ],
                }
                main_keyword = next(
                    (kw for kw, kw_type in all_used_keywords if kw_type == "메인"),
                    keyword,
                )

                internal_links = self.internal_link_builder.generate_internal_links(
                    current_post_id=temp_post_id,
                    keywords_data=all_keywords_data,
                    target_keyword=main_keyword,
                    markdown_content=temp_md_content,
                    max_links=len(all_used_keywords),  # 모든 키워드 시도
                    min_similarity_score=0.3,  # 더 완화된 유사도
                )

                # 실제로 내부링크에 사용된 키워드들 수집
                internal_keywords = [
                    (link.anchor_text, "사용됨") for link in internal_links
                ]

                if internal_links:
                    internal_summary = (
                        self.internal_link_builder.get_internal_links_summary(
                            internal_links
                        )
                    )
                    print(f"   📎 생성된 내부링크: {internal_summary['총_링크_수']}개")
                    print(f"     - 평균 유사도: {internal_summary['평균_유사도']}")
                else:
                    print(f"   📎 생성된 내부링크: 0개 (유사한 포스트 없음)")
            else:
                print(f"   📎 내부링크: 건너뜀 (저장된 포스트 없음)")

            # 5-2. 외부링크 생성 (내부링크에 사용되지 않은 키워드들로)
            external_links = []
            internal_used_keywords = {link.anchor_text for link in internal_links}

            # 내부링크에 사용되지 않은 키워드들 수집
            remaining_keywords = [
                (kw, kw_type)
                for kw, kw_type in all_used_keywords
                if kw not in internal_used_keywords
            ]

            print(f"   🌐 외부링크 생성 중...")
            print(f"     - 내부링크 사용 키워드: {len(internal_used_keywords)}개")
            print(f"     - 외부링크 대상 키워드: {len(remaining_keywords)}개")

            if remaining_keywords:
                remaining_kw_list = [
                    f"{kw}({kw_type})" for kw, kw_type in remaining_keywords
                ]
                print(f"     - 외부링크 키워드: {', '.join(remaining_kw_list)}")

                # 외부링크 생성
                for kw, kw_type in remaining_keywords:
                    link = self.external_link_builder.create_external_link(kw, kw_type)
                    external_links.append(link)

            if external_links:
                link_summary = self.external_link_builder.get_links_summary(
                    external_links
                )
                print(f"   📎 생성된 외부링크: {link_summary['총_링크_수']}개")
            else:
                print(f"   📎 생성된 외부링크: 0개 (모든 키워드가 내부링크에 사용됨)")

            # 6. 이미지 생성 (제목 + 섹션별 20% 확률)
            print("6. 이미지 생성 중...")
            images = {}

            # 메인 이미지 (제목 기반, 100% 확률)
            print("   - 메인 이미지 생성...")
            main_prompt = f"Clean minimalist infographic diagram about '{keyword}', visual concept illustration, no text or letters, chart elements, flow diagram style, professional design, simple color scheme"
            main_image_b64 = await self.generate_image(main_prompt, "main_title")

            if main_image_b64:
                main_image_filename = f"main_{safe_kw}.png"
                main_image_path = project_root / f"data/images/{main_image_filename}"
                if self.save_image_from_base64(main_image_b64, main_image_path):
                    # 워드프레스 호환 URL 형태 (향후 업로드 시 교체 예정)
                    images["main"] = (
                        f"https://your-wordpress-site.com/wp-content/uploads/2024/images/{main_image_filename}"
                    )
                    print(f"     ✅ 메인 이미지 저장: {main_image_filename}")

            # 섹션별 이미지 (20% 확률)
            for i, section in enumerate(sections_content):
                if random.random() < 0.2:  # 20% 확률
                    print(f"   - 섹션 {i+1} 이미지 생성: {section['h2_title']}")
                    section_prompt = f"Simple visual diagram for '{section['h2_title']}' concept related to {keyword}, no text or words, minimalist chart design, geometric shapes, clean infographic elements, conceptual illustration"
                    section_image_b64 = await self.generate_image(
                        section_prompt, f"section_{i+1}"
                    )

                    if section_image_b64:
                        section_image_filename = f"section_{i+1}_{safe_kw}.png"
                        section_image_path = (
                            project_root / f"data/images/{section_image_filename}"
                        )
                        if self.save_image_from_base64(
                            section_image_b64, section_image_path
                        ):
                            # 워드프레스 호환 URL 형태 (향후 업로드 시 교체 예정)
                            images[f"section_{i+1}"] = (
                                f"https://your-wordpress-site.com/wp-content/uploads/2024/images/{section_image_filename}"
                            )
                            print(f"     ✅ 섹션 이미지 저장: {section_image_filename}")

            total_duration = time.time() - start_time

            # 7. 목차 및 용어 정리 생성
            print("7. 목차 및 용어 정리 생성 중...")

            # 목차 생성 (LLM 호출 없이)
            table_of_contents = self.generate_table_of_contents(sections_content)
            print("   ✅ 목차 생성 완료")

            # 전체 콘텐츠 조합 (용어 추출용)
            full_content = "\n".join([sec["content"] for sec in sections_content])

            # 용어 추출 및 설명 생성 (LLM 호출)
            terms_section = await self.extract_and_explain_terms(full_content, keyword)
            print("   ✅ 용어 정리 생성 완료")

            # 8. 파일 생성 (별칭 포함)
            print("8. 파일 생성 중...")
            timestamp2 = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_kw2 = self._safe_fragment(keyword)

            # MD (목차 + 용어 정리 + 이미지 + 외부링크 포함)
            md_content = self.create_markdown(
                tk["title"],
                keyword,
                sections_content,
                {
                    "lsi_keywords": tk.get("lsi_keywords", []),
                    "longtail_keywords": tk.get("longtail_keywords", []),
                },
                images,  # 이미지 정보 전달
                table_of_contents,  # 목차 추가
                terms_section,  # 용어 정리 추가
            )

            # 외부링크 삽입 전에 원본 링크 리스트를 백업
            original_external_links = external_links.copy()

            # 외부링크 삽입 (링크 리스트가 수정될 수 있음)
            md_content = self.external_link_builder.insert_links_into_markdown(
                md_content, external_links
            )

            # 내부링크 삽입 (외부링크 삽입 후)
            if internal_links:
                print("   🔗 내부링크 마크다운에 삽입 중...")
                md_content = (
                    self.internal_link_builder.insert_internal_links_into_markdown(
                        md_content, internal_links
                    )
                )

            # 실제 적용된 링크 수 재계산 (원본 링크 리스트 기준으로 마크다운 콘텐츠에서 확인)
            applied_links = []
            unused_links = []

            for link in original_external_links:
                # 마크다운 링크 패턴이 존재하는지 체크: [앵커텍스트](어떤URL이든)
                link_pattern = f"[{link.anchor_text}]("
                if link_pattern in md_content:
                    applied_links.append(link)
                else:
                    unused_links.append(link)
            md_file = project_root / f"data/blog_{safe_kw2}_{timestamp2}.md"
            md_file.parent.mkdir(exist_ok=True)
            with open(md_file, "w", encoding="utf-8") as f:
                f.write(md_content)
            alias_md = project_root / f"data/OUTPUT_{safe_kw2}.md"
            with open(alias_md, "w", encoding="utf-8") as f:
                f.write(md_content)

            # HTML (SimpleHTMLConverter 사용)
            from src.generators.html.simple_html_converter import SimpleHTMLConverter

            converter = SimpleHTMLConverter()
            html_content = converter.convert_markdown_to_html(md_content)
            html_file = project_root / f"data/blog_{safe_kw2}_{timestamp2}_final.html"
            with open(html_file, "w", encoding="utf-8") as f:
                f.write(html_content)
            alias_html = project_root / f"data/OUTPUT_{safe_kw2}.html"
            with open(alias_html, "w", encoding="utf-8") as f:
                f.write(html_content)

            # 비용 리포트 (외부링크 정보 포함)
            cost_report = self.create_cost_analysis_report(
                keyword,
                tk["title"],
                {
                    "lsi_keywords": tk.get("lsi_keywords", []),
                    "longtail_keywords": tk.get("longtail_keywords", []),
                },
                sections_content,
                total_duration,
            )

            # 링크 분석 정보 추가 (외부링크 + 내부링크)
            cost_report["link_analysis"] = {
                "external_links_generated": len(applied_links),
                "internal_links_generated": len(internal_links),
                "external_link_summary": {
                    "총_링크_수": len(applied_links),
                    "외부링크_수": len(
                        [l for l in applied_links if l.platform != "홈페이지"]
                    ),
                    "홈페이지_링크_수": len(
                        [l for l in applied_links if l.platform == "홈페이지"]
                    ),
                    "플랫폼별": {},
                },
                "internal_link_summary": (
                    self.internal_link_builder.get_internal_links_summary(
                        internal_links
                    )
                    if internal_links
                    else {}
                ),
                "external_link_details": [
                    {
                        "anchor_text": link.anchor_text,
                        "url": link.url,
                        "platform": link.platform,
                        "keyword_type": link.keyword_type,
                    }
                    for link in applied_links
                ],
                "internal_link_details": [
                    {
                        "anchor_text": link.anchor_text,
                        "target_url": link.target_url,
                        "target_title": link.target_title,
                        "similarity_score": link.similarity_score,
                        "keyword_type": link.keyword_type,
                    }
                    for link in internal_links
                ],
                "unused_external_links": [
                    {
                        "anchor_text": link.anchor_text,
                        "url": link.url,
                        "platform": link.platform,
                        "keyword_type": link.keyword_type,
                        "reason": "키워드를 본문에서 찾을 수 없음",
                    }
                    for link in unused_links
                ],
            }

            # 플랫폼별 통계 계산
            for link in applied_links:
                platform = link.platform
                if (
                    platform
                    not in cost_report["link_analysis"]["external_link_summary"][
                        "플랫폼별"
                    ]
                ):
                    cost_report["link_analysis"]["external_link_summary"]["플랫폼별"][
                        platform
                    ] = 0
                cost_report["link_analysis"]["external_link_summary"]["플랫폼별"][
                    platform
                ] += 1
            json_file = (
                project_root / f"data/cost_analysis_report_{safe_kw2}_{timestamp2}.json"
            )
            with open(json_file, "w", encoding="utf-8") as f:
                json.dump(cost_report, f, ensure_ascii=False, indent=2)
            alias_json = project_root / f"data/OUTPUT_{safe_kw2}.json"
            with open(alias_json, "w", encoding="utf-8") as f:
                json.dump(cost_report, f, ensure_ascii=False, indent=2)

            print(f"\n파일 생성 완료:")
            print(f"   - Step1: {step1_file.name} / 별칭: {alias_step1.name}")
            print(f"   - Step2: {step2_file.name} / 별칭: {alias_step2.name}")
            print(f"   - Markdown: {md_file.name} / 별칭: {alias_md.name}")
            print(f"   - HTML: {html_file.name} / 별칭: {alias_html.name}")
            print(f"   - Cost Report: {json_file.name} / 별칭: {alias_json.name}")

            # 워드프레스 업로드 (요청된 경우)
            wp_result = None
            if upload_to_wp and wp_ready:
                wp_result = await self.upload_to_wordpress(
                    title=tk["title"],
                    html_content=html_content,
                    keyword=keyword,
                    lsi_keywords=tk.get("lsi_keywords", []),
                    longtail_keywords=tk.get("longtail_keywords", []),
                    images_dir=project_root / "data/images",
                )

                # 워드프레스 업로드 후 처리
                if wp_result:
                    cost_report["wordpress_upload"] = {
                        "success": True,
                        "post_id": wp_result["id"],
                        "post_url": wp_result["url"],
                        "upload_date": wp_result["date"],
                    }

                    # 워드프레스 업로드 성공 시 FAISS에도 저장
                    if storage_ready and self.content_storage:
                        print("   📚 FAISS 벡터 저장소에 콘텐츠 저장 중...")

                        # 마크다운 콘텐츠에서 텍스트만 추출 (링크, 이미지 등 제거)
                        import re

                        clean_content = re.sub(
                            r"!\[.*?\]\(.*?\)", "", md_content
                        )  # 이미지 제거
                        clean_content = re.sub(
                            r"\[([^\]]+)\]\([^)]+\)", r"\1", clean_content
                        )  # 링크 텍스트만 유지
                        clean_content = re.sub(
                            r"#+\s*", "", clean_content
                        )  # 헤딩 마크업 제거
                        clean_content = re.sub(
                            r"\*\*([^*]+)\*\*", r"\1", clean_content
                        )  # 볼드 제거
                        clean_content = re.sub(
                            r"\n\s*\n", "\n\n", clean_content
                        )  # 빈 줄 정리

                        storage_success = self.content_storage.store_wordpress_post(
                            post_data=wp_result,
                            content=clean_content.strip(),
                            keyword=keyword,
                            lsi_keywords=tk.get("lsi_keywords", []),
                            longtail_keywords=tk.get("longtail_keywords", []),
                            categories=["블로그", "SEO"],
                        )

                        if storage_success:
                            print("   ✅ FAISS 벡터 저장소에 저장 완료")
                            cost_report["content_storage"] = {
                                "success": True,
                                "stored_at": datetime.now().isoformat(),
                            }
                        else:
                            print("   ❌ FAISS 벡터 저장소 저장 실패")
                            cost_report["content_storage"] = {
                                "success": False,
                                "error": "저장 중 오류 발생",
                            }

            # 워드프레스 업로드 없이도 콘텐츠 저장 (로컬 테스트용)
            elif not upload_to_wp and storage_ready and self.content_storage:
                print("9. FAISS 벡터 저장소에 콘텐츠 저장 중... (로컬)")

                # 가상의 포스트 데이터 생성 (로컬 테스트용)
                fake_post_data = {
                    "id": f"local_{int(time.time())}",
                    "title": tk["title"],
                    "url": f"local://blog/{safe_kw2}",
                    "date": datetime.now().isoformat(),
                }

                # 마크다운 콘텐츠에서 텍스트만 추출
                import re

                clean_content = re.sub(r"!\[.*?\]\(.*?\)", "", md_content)
                clean_content = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", clean_content)
                clean_content = re.sub(r"#+\s*", "", clean_content)
                clean_content = re.sub(r"\*\*([^*]+)\*\*", r"\1", clean_content)
                clean_content = re.sub(r"\n\s*\n", "\n\n", clean_content)

                storage_success = self.content_storage.store_wordpress_post(
                    post_data=fake_post_data,
                    content=clean_content.strip(),
                    keyword=keyword,
                    lsi_keywords=tk.get("lsi_keywords", []),
                    longtail_keywords=tk.get("longtail_keywords", []),
                    categories=["블로그", "SEO"],
                )

                if storage_success:
                    print("   ✅ FAISS 벡터 저장소에 저장 완료 (로컬)")
                    cost_report["content_storage"] = {
                        "success": True,
                        "stored_at": datetime.now().isoformat(),
                        "type": "local",
                    }
                else:
                    print("   ❌ FAISS 벡터 저장소 저장 실패")
                    cost_report["content_storage"] = {
                        "success": False,
                        "error": "저장 중 오류 발생",
                    }

            # 업데이트된 비용 리포트 저장
            with open(json_file, "w", encoding="utf-8") as f:
                json.dump(cost_report, f, ensure_ascii=False, indent=2)
            with open(alias_json, "w", encoding="utf-8") as f:
                json.dump(cost_report, f, ensure_ascii=False, indent=2)

            print("\n" + "=" * 60)
            print("Enhanced RAG 파이프라인 완료!")
            print("=" * 60)
            print(f"키워드: {keyword}")
            print(f"제목: {tk['title']}")
            print(f"모델: gpt-5-nano + gpt-image-1 (temperature=1.0)")
            print(f"RAG 활성화: {'예' if rag_enabled else '아니오'}")
            print(f"생성 시간: {total_duration:.1f}초")
            print(f"섹션 수: {len(sections_content)}개")
            print(f"생성된 이미지: {len(images)}개")
            print(f"생성된 외부링크: {len(applied_links)}개")
            print(f"생성된 내부링크: {len(internal_links)}개")
            if unused_links:
                print(
                    f"   ⚠️  미사용 외부링크: {len(unused_links)}개 (키워드를 본문에서 찾을 수 없음)"
                )
            print(
                f"총 콘텐츠 길이: {sum(len(s['content']) for s in sections_content):,}자"
            )
            # 이미지 비용 표시
            if len(images) > 0:
                total_image_cost = sum(
                    img["cost_usd"] for img in self.cost_tracker["image_details"]
                )
                print(f"이미지 생성 비용: ${total_image_cost:.3f}")
                print(f"생성된 이미지 파일:")
                for key, filename in images.items():
                    print(f"  - {key}: {filename}")

            # 외부링크 정보 표시
            if len(applied_links) > 0:
                print(f"실제 적용된 외부링크:")
                for link in applied_links:
                    print(f"  - {link.anchor_text} → {link.platform}")

            if len(unused_links) > 0:
                print(f"미사용 외부링크:")
                for link in unused_links:
                    print(
                        f"  - {link.anchor_text} → {link.platform} (본문에서 키워드 없음)"
                    )

            # 내부링크 정보 표시
            if len(internal_links) > 0:
                print(f"실제 적용된 내부링크:")
                for link in internal_links:
                    print(
                        f"  - {link.anchor_text} → {link.target_title} (유사도: {link.similarity_score:.3f})"
                    )

            # 워드프레스 업로드 결과 표시
            if upload_to_wp:
                if wp_result:
                    print(f"\n🚀 워드프레스 업로드 완료:")
                    print(f"   📄 포스트 ID: {wp_result['id']}")
                    print(f"   🔗 URL: {wp_result['url']}")
                elif wp_ready:
                    print(f"\n❌ 워드프레스 업로드 실패")
                else:
                    print(f"\n⚠️ 워드프레스 연결 실패로 업로드 건너뜀")

            # 이미지 폴더 정리
            print("\n10. 이미지 폴더 정리 중...")
            self.cleanup_images_folder()

            result_data = {
                "success": True,
                "files": {
                    "step1": str(alias_step1),
                    "step2": str(alias_step2),
                    "markdown": str(alias_md),
                    "html": str(alias_html),
                    "cost_report": str(alias_json),
                },
            }

            # 워드프레스 업로드 결과 추가
            if wp_result:
                result_data["wordpress"] = {
                    "post_id": wp_result["id"],
                    "post_url": wp_result["url"],
                    "upload_date": wp_result["date"],
                }

            return result_data

        except Exception as e:
            print(f"\n오류 발생: {e}")
            import traceback

            traceback.print_exc()
            return {"success": False, "error": str(e)}


async def main():
    """메인 실행 함수"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Enhanced RAG Pipeline for SEO Blog Generation"
    )
    parser.add_argument(
        "keyword", nargs="?", default="부자되는 습관", help="타겟 키워드"
    )
    parser.add_argument(
        "--wp", "--wordpress", action="store_true", help="워드프레스에 자동 업로드"
    )
    parser.add_argument(
        "--no-wp", action="store_true", help="워드프레스 업로드 건너뛰기 (기본값)"
    )

    args = parser.parse_args()

    # 워드프레스 업로드 여부 결정
    upload_to_wp = args.wp and not args.no_wp

    if upload_to_wp:
        print("🚀 워드프레스 자동 업로드 모드")
    else:
        print("📝 파일 생성만 수행 (워드프레스 업로드 안함)")

    pipeline = EnhancedRAGPipeline()
    result = await pipeline.run_complete_pipeline(
        args.keyword, upload_to_wp=upload_to_wp
    )

    if result["success"]:
        print(f"\n✅ 파이프라인 성공! 생성된 파일들을 확인하세요.")
        if "wordpress" in result:
            print(f"🌐 워드프레스 포스트: {result['wordpress']['post_url']}")
    else:
        print(f"\n❌ 파이프라인 실패: {result['error']}")


if __name__ == "__main__":
    asyncio.run(main())
