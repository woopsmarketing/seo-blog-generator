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
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Tuple
import re

# 프로젝트 루트 디렉토리를 Python 경로에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.utils.config import load_config
from src.utils.llm_factory import create_gpt5_nano, LLMFactory, LLMConfig
from src.utils.rag import SimpleRAG
from langchain_core.messages import HumanMessage


class EnhancedRAGPipeline:
    """Enhanced RAG Pipeline with detailed analytics"""

    def __init__(self):
        self.config = load_config()
        self.llm = create_gpt5_nano()
        self.rag = None
        self.cost_tracker = {
            "total_calls": 0,
            "total_tokens": {"prompt": 0, "completion": 0},
            "total_duration": 0,
            "step_details": [],
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
        prompt = f"""
키워드: {keyword}

하나의 JSON으로 아래 4가지를 모두 구조화하여 반환하세요. 한국어로 작성합니다.
1) title: SEO 최적화 블로그 제목 (키워드 포함, 60자 이내)
2) lsi_keywords: 의미적으로 연관된 LSI 키워드 10개 배열
3) longtail_keywords: 구체적인 롱테일 키워드 8개 배열
4) notes: 간단한 생성 의도 설명 1-2문장

반드시 아래 형식의 단일 JSON만 출력하세요:
{{
  "title": "...",
  "lsi_keywords": ["..."],
  "longtail_keywords": ["..."],
  "notes": "..."
}}
"""
        if self.rag and self.rag.vs:
            rag_context = self.rag.query(f"{keyword} 관련 배경 정보", k=2)
            prompt = f"{rag_context}\n\n{prompt}"

        messages = [HumanMessage(content=prompt)]
        response = self.llm.invoke(messages)
        duration = time.time() - start_time
        prompt_tokens = int(len(prompt.split()) * 1.3)
        completion_tokens = int(len(response.content.split()) * 1.3)

        self.track_llm_call(
            "generate_title_keywords",
            prompt_tokens,
            completion_tokens,
            duration,
            response.content,
            "키워드→제목/LSI/롱테일 단일 JSON 생성",
        )

        try:
            import re, json as _json

            m = re.search(r"\{[\s\S]*\}$", response.content.strip())
            data = _json.loads(m.group(0)) if m else _json.loads(response.content)
            # 보정
            data.setdefault("lsi_keywords", [])
            data.setdefault("longtail_keywords", [])
            data.setdefault("notes", "")
            return data
        except Exception:
            return {
                "title": f"{keyword} 완벽 가이드",
                "lsi_keywords": [f"{keyword} 팁", f"{keyword} 방법"],
                "longtail_keywords": [f"{keyword} 초보 가이드"],
                "notes": "기본 폴백 결과",
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
        if self.rag and self.rag.vs:
            rag_context = self.rag.query(f"{keyword} 전체 구조 설계 참고", k=3)
            prompt = f"{rag_context}\n\n{prompt}"

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
    ) -> str:
        """섹션별 콘텐츠 생성 (컨텍스트와 티저 포함)"""
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

        prompt = f"""
문서 제목: {title}
주요 키워드: {keyword}
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

본문 출력 시작:
"""
        if self.rag and self.rag.vs:
            rag_context = self.rag.query(f"{keyword} {section.get('h2','')} 배경", k=2)
            prompt = f"{rag_context}\n\n{prompt}"

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

        return response.content.strip()

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
    ) -> str:
        """마크다운 형식 생성"""
        md_content = f"""# {title}

**타겟 키워드:** {keyword}
**예상 길이:** {sum(len(section['content']) for section in sections_content):,}자
**SEO 전략:** 핵심 키워드와 LSI 키워드를 자연스럽게 제목 및 본문에 배치하여 SEO 효과 극대화

**LSI 키워드:** {', '.join(keywords['lsi_keywords'])}
**롱테일 키워드:** {', '.join(keywords['longtail_keywords'])}

"""

        for section in sections_content:
            md_content += f"## {section['h2_title']}\n\n"
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
        total_cost = sum(
            step["estimated_cost_usd"] for step in self.cost_tracker["step_details"]
        )
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
                    "model_used": "gpt-5-nano",
                    "total_duration_seconds": round(total_duration, 1),
                    "sections_generated": len(sections_content),
                    "total_estimated_cost_usd": round(total_cost, 6),
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

        # 단계별 분석 추가
        for i, step in enumerate(self.cost_tracker["step_details"], 1):
            report["cost_analysis"]["step_by_step_analysis"][
                f"step_{i}_{step['step']}"
            ] = {
                "timestamp": step["timestamp"],
                "duration": f"{step['duration_seconds']:.1f}초",
                "model_calls": 1,
                "cost": f"${step['estimated_cost_usd']:.6f}",
                "output": step["output_summary"],
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

    async def run_complete_pipeline(self, keyword: str) -> Dict[str, Any]:
        """완전한 RAG 파이프라인 실행"""
        start_time = time.time()

        print(f"키워드 '{keyword}'로 Enhanced RAG 파이프라인 시작")
        print("=" * 60)

        try:
            # 1. RAG 설정
            rag_enabled = self.setup_rag()
            print(f"1. RAG 시스템: {'활성화' if rag_enabled else '비활성화'}")

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
            total = len(sections)

            for i, sec in enumerate(sections, 1):
                next_h2 = sections[i]["h2"] if i < total else ""
                raw = await self.generate_section_with_context(
                    idx=i,
                    total=total,
                    section=sec,
                    keyword=keyword,
                    title=tk["title"],
                    full_structure_json=structure,
                    prev_summary=prev_summary,
                    next_h2=next_h2,
                )

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

            total_duration = time.time() - start_time

            # 5. 파일 생성 (별칭 포함)
            print("5. 파일 생성 중...")
            timestamp2 = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_kw2 = self._safe_fragment(keyword)

            # MD
            md_content = self.create_markdown(
                tk["title"],
                keyword,
                sections_content,
                {
                    "lsi_keywords": tk.get("lsi_keywords", []),
                    "longtail_keywords": tk.get("longtail_keywords", []),
                },
            )
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

            # 비용 리포트
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

            print("\n" + "=" * 60)
            print("Enhanced RAG 파이프라인 완료!")
            print("=" * 60)
            print(f"키워드: {keyword}")
            print(f"제목: {tk['title']}")
            print(f"모델: gpt-5-nano (temperature=1.0)")
            print(f"RAG 활성화: {'예' if rag_enabled else '아니오'}")
            print(f"생성 시간: {total_duration:.1f}초")
            print(f"섹션 수: {len(sections_content)}개")
            print(
                f"총 콘텐츠 길이: {sum(len(s['content']) for s in sections_content):,}자"
            )

            return {
                "success": True,
                "files": {
                    "step1": str(alias_step1),
                    "step2": str(alias_step2),
                    "markdown": str(alias_md),
                    "html": str(alias_html),
                    "cost_report": str(alias_json),
                },
            }

        except Exception as e:
            print(f"\n오류 발생: {e}")
            import traceback

            traceback.print_exc()
            return {"success": False, "error": str(e)}


async def main():
    """메인 실행 함수"""
    keyword = sys.argv[1] if len(sys.argv) > 1 else "부자되는 습관"

    pipeline = EnhancedRAGPipeline()
    result = await pipeline.run_complete_pipeline(keyword)

    if result["success"]:
        print(f"\n✅ 파이프라인 성공! 생성된 파일들을 확인하세요.")
    else:
        print(f"\n❌ 파이프라인 실패: {result['error']}")


if __name__ == "__main__":
    asyncio.run(main())
