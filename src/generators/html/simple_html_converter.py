# -*- coding: utf-8 -*-
"""
단순 HTML 변환기 (Simple HTML Converter)

마크다운 블로그 콘텐츠를 워드프레스 REST API용 HTML로 변환
- HEAD 섹션 없음 (워드프레스가 자동 생성)
- CSS 없음 (사용자 정의 CSS로 따로 적용)
- 순수 콘텐츠만 HTML 태그로 변환
- 워드프레스 호환 클래스명 사용
"""

import re
from typing import Dict, List


class SimpleHTMLConverter:
    """
    워드프레스용 단순 HTML 변환기

    마크다운 콘텐츠를 워드프레스 REST API에 업로드할 수 있는
    순수 HTML 콘텐츠로 변환합니다.
    """

    def __init__(self):
        """HTML 변환기 초기화"""
        self.css_classes = self._init_wordpress_classes()

    def _init_wordpress_classes(self) -> Dict[str, str]:
        """워드프레스 호환 CSS 클래스 정의 (fs- prefix)"""
        return {
            # 전체 래퍼
            "article_wrapper": "fs-article",  # 전체 래퍼
            "section_wrapper": "fs-section",  # H2 기준 섹션 래퍼 (section 태그)
            # 섹션 관련
            "main_title": "fs-h1",  # H1 제목
            "section_title": "fs-h2",  # H2 제목
            "subsection_title": "fs-h3",  # H3 제목
            "subsubsection_title": "fs-h4",  # H4 제목
            # 목차 관련
            "toc_section": "fs-toc",  # 목차 섹션 (nav 태그)
            "toc_list": "fs-toc-list",  # 목차 리스트 (ol 태그)
            # 이미지 관련
            "figure": "fs-figure",  # 이미지 컨테이너 (figure 태그)
            # 핵심 용어 관련
            "terms_definition": "fs-terms",  # 용어 정의 목록 컨테이너 (dl 태그)
            "term_name": "fs-term-name",  # 용어명 (dt 태그)
            "term_description": "fs-term-description",  # 용어 설명 (dd 태그)
            "term_item": "fs-term",  # 개별 용어 항목 (legacy support)
            # 콘텐츠 관련 (fs-paragraph 제거)
            "content_list": "fs-list",  # 목록 컨테이너
            "content_list_item": "fs-list-item",  # 목록 항목
            # 표 관련
            "table": "fs-table",  # 표 컨테이너
            "table_header": "fs-table-header",  # 표 헤더
            "table_cell": "fs-table-cell",  # 표 셀
            # 알림/주의 박스
            "note_box": "fs-note",  # 알림/주의 박스
            # FAQ 관련
            "faq_section": "fs-faq",  # FAQ 섹션
            "faq_item": "fs-faq-item",  # FAQ 개별 항목
            # 특수 섹션
            "intro_section": "fs-intro",  # 개요 섹션
            "conclusion_section": "fs-conclusion",  # 마무리 섹션
        }

    def convert_markdown_to_html(self, markdown_content: str) -> str:
        """
        마크다운 콘텐츠를 워드프레스용 HTML로 변환

        Args:
            markdown_content: 마크다운 형태의 블로그 콘텐츠

        Returns:
            워드프레스 REST API용 HTML 콘텐츠
        """
        # 1. 디버깅 정보 제거
        html = self._remove_debug_info(markdown_content)

        # 2. 메타데이터 섹션 제거
        html = self._remove_metadata_section(html)

        # 3. 제목 변환 (H1, H2, H3, H4)
        html = self._convert_headings(html)

        # 4. 텍스트 스타일 변환 (볼드, 이탤릭)
        html = self._convert_text_styles(html)

        # 5. 용어 정리 섹션 변환 (볼드 변환 후)
        html = self._convert_terms_section(html)

        # 6. 이미지 변환 (링크보다 먼저 처리해야 함)
        html = self._convert_images(html)

        # 7. 표 변환
        html = self._convert_tables(html)

        # 8. 목록 변환
        html = self._convert_lists(html)

        # 9. 문단 변환
        html = self._convert_paragraphs(html)

        # 10. 마크다운 링크 변환 (제목 변환 후에 실행하여 앵커 ID 오염 방지)
        html = self._convert_links(html)

        # 11. 특수 섹션 클래스 적용
        html = self._apply_special_section_classes(html)

        # 12. 목차(TOC) 구조 개선
        html = self._convert_toc_structure(html)

        # 13. 정리 작업
        html = self._cleanup_html(html)

        # 14. H2 기준 섹션 래퍼 추가
        html = self._wrap_sections(html)

        # 15. 전체 article 래퍼로 감싸기
        html = self._wrap_with_article(html)

        return html.strip()

    def _remove_debug_info(self, content: str) -> str:
        """디버깅 정보 주석 제거"""
        # <!-- 🔍 디버깅 정보: ... --> 패턴 제거
        debug_pattern = r"<!-- 🔍 디버깅 정보:.*?-->"
        content = re.sub(debug_pattern, "", content, flags=re.MULTILINE | re.DOTALL)

        # <!-- 길이: ... --> 패턴 제거
        length_pattern = r"<!-- 길이:.*?-->"
        content = re.sub(length_pattern, "", content, flags=re.MULTILINE | re.DOTALL)

        # <!-- 추출된 사실: ... --> 패턴 제거
        fact_pattern = r"<!-- 추출된 사실:.*?-->"
        content = re.sub(fact_pattern, "", content, flags=re.MULTILINE | re.DOTALL)

        # --- 구분선 제거
        content = re.sub(r"^---\s*$", "", content, flags=re.MULTILINE)

        # 📍 이모지 제거 (섹션 제목에서)
        content = re.sub(r"📍 섹션 \d+: ", "", content)
        content = re.sub(r"📊 ", "", content)

        return content

    def _remove_metadata_section(self, content: str) -> str:
        """마크다운 시작 부분의 H1 제목과 메타데이터 섹션 제거 (워드프레스에서 별도 처리)"""
        # H1 제목 제거 (워드프레스에서 title로 사용)
        content = re.sub(r"^# .+?\n\n", "", content, flags=re.MULTILINE)

        # 메타데이터 패턴 제거: 특정 메타데이터만 제거
        # **타겟 키워드:**, **예상 길이:**, **SEO 전략:**, **LSI 키워드:**, **롱테일 키워드:** 만 제거
        meta_patterns = [
            r"\*\*타겟 키워드:\*\*[^\n]+\n",
            r"\*\*예상 길이:\*\*[^\n]+\n",
            r"\*\*SEO 전략:\*\*[^\n]+\n",
            r"\*\*LSI 키워드:\*\*[^\n]+\n",
            r"\*\*롱테일 키워드:\*\*[^\n]+\n",
        ]
        for pattern in meta_patterns:
            content = re.sub(pattern, "", content, flags=re.MULTILINE)

        return content

    def _convert_headings(self, content: str) -> str:
        """마크다운 제목을 HTML 제목으로 변환 (앵커 ID 포함)"""

        def generate_anchor_id(title: str) -> str:
            """제목에서 앵커 ID 생성 (마크다운 링크 및 HTML 태그 제거 후 처리)"""
            # 1. 먼저 마크다운 링크 패턴 제거 [텍스트](링크) -> 텍스트
            clean_title = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", title)

            # 2. HTML 태그 제거 (링크 태그 등)
            clean_title = re.sub(r"<[^>]+>", "", clean_title)

            # 3. 특수문자 제거하고 공백을 하이픈으로 변환
            anchor_id = (
                clean_title.replace(" ", "-")
                .replace(":", "")
                .replace("?", "")
                .replace("!", "")
                .replace(",", "")
                .replace(".", "")
                .replace("(", "")
                .replace(")", "")
            )
            return anchor_id

        # 제목 변환 - 긴 패턴부터 먼저 처리 (H4 -> H3 -> H2 순서)

        # H4 변환 (#### 제목) - 공백 선택적으로 매칭
        content = re.sub(
            r"^####\s*(.+)$",
            f'<h4 class="{self.css_classes["subsubsection_title"]}">\\1</h4>',
            content,
            flags=re.MULTILINE,
        )

        # H3 변환 (### 제목) - 공백 선택적으로 매칭
        content = re.sub(
            r"^###\s*(.+)$",
            f'<h3 class="{self.css_classes["subsection_title"]}">\\1</h3>',
            content,
            flags=re.MULTILINE,
        )

        # H2 변환 (## 제목) - 앵커 ID 추가
        def replace_h2(match):
            title = match.group(1)
            anchor_id = generate_anchor_id(title)

            # 특별한 섹션들에 대한 고정 ID
            if "📖 핵심 용어 정리" in title:
                anchor_id = "핵심-용어-정리"
            elif "📚 목차" in title:
                anchor_id = "toc-section"

            return f'<h2 id="{anchor_id}" class="{self.css_classes["section_title"]}">{title}</h2>'

        # ## 뒤에 공백이 있거나 없는 경우 모두 매칭 (공백은 선택적)
        # 단, ###이나 ####는 이미 처리되었으므로 정확히 ##만 매칭
        content = re.sub(r"^##(?!#)\s*(.+)$", replace_h2, content, flags=re.MULTILINE)

        # 이미 HTML로 변환된 핵심 용어 정리 섹션의 ID 수정
        content = re.sub(
            r'<h2 id="terms-section">(📖\s*핵심\s*용어\s*정리)</h2>',
            r'<h2 id="핵심-용어-정리" class="'
            + self.css_classes["section_title"]
            + r'">\1</h2>',
            content,
        )

        return content

    def _convert_terms_section(self, content: str) -> str:
        """핵심 용어 정리 섹션의 **용어**: 설명 형태를 구조화된 HTML로 변환"""
        # 핵심 용어 정리 섹션 찾기 (HTML 변환 후 상태)
        terms_section_pattern = (
            r"(<h2[^>]*>📖 핵심 용어 정리</h2>.*?)(?=<h[12][^>]*>|$)"
        )

        def convert_terms_content(match):
            """용어 정리 섹션 내용을 구조화된 HTML로 변환"""
            section_content = match.group(1)

            # 제목 부분과 내용 부분 분리
            lines = section_content.split("\n")
            header_line = lines[0]  # <h2>...</h2>

            # **용어**: 설명 패턴을 찾아서 변환 (볼드 변환 후에는 <strong> 태그로 변경됨)
            term_pattern = r"<strong>([^<]+)</strong>:\s*([^\n]+)"
            terms_html = []
            intro_text = ""

            # 설명 문구와 용어들을 찾기
            for line in lines[1:]:
                line = line.strip()
                if not line:  # 빈 줄 건너뛰기
                    continue

                term_match = re.match(term_pattern, line)
                if term_match:
                    term_name = term_match.group(1).strip()
                    term_explanation = term_match.group(2).strip()
                    # dl > dt, dd 구조로 용어 정의 생성 (시맨틱한 용어 정의)
                    terms_html.append(
                        f'  <dt class="{self.css_classes["term_name"]}">{term_name}</dt>'
                    )
                    terms_html.append(
                        f'  <dd class="{self.css_classes["term_description"]}">{term_explanation}</dd>'
                    )
                elif (
                    not intro_text and not term_match
                ):  # 첫 번째 비-용어 줄을 설명으로 사용
                    intro_text = line

            # 구조화된 HTML 생성 (dl 태그 사용)
            if terms_html:
                terms_container = (
                    f'<dl class="{self.css_classes["terms_definition"]}">'
                    + "\n"
                    + "\n".join(terms_html)
                    + "\n</dl>"
                )

                if not intro_text:
                    intro_text = "본문을 읽기 전에 알아두면 좋은 용어들입니다."

                return (
                    header_line + "\n\n<p>" + intro_text + "</p>\n\n" + terms_container
                )
            else:
                return section_content

        # 핵심 용어 정리 섹션 변환
        content = re.sub(
            terms_section_pattern, convert_terms_content, content, flags=re.DOTALL
        )

        return content

    def _convert_text_styles(self, content: str) -> str:
        """볼드 및 이탤릭 텍스트 변환"""
        # 볼드 텍스트 변환 (**text** -> <strong>text</strong>)
        content = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", content)

        # 이탤릭 텍스트 변환 (*text* -> <em>text</em>)
        # 단, 이미 <strong> 태그 안에 있지 않은 경우에만
        content = re.sub(r"(?<!\*)\*([^*]+?)\*(?!\*)", r"<em>\1</em>", content)

        return content

    def _convert_images(self, content: str) -> str:
        """마크다운 이미지를 시맨틱 HTML figure 구조로 변환

        마크다운 형식: ![alt텍스트](이미지URL)
        HTML 형식: <figure class="fs-figure"><img src="이미지URL" alt="alt텍스트" loading="lazy"></figure>
        """
        # 마크다운 이미지 패턴: ![alt텍스트](이미지URL)
        image_pattern = r"!\[([^\]]*)\]\(([^)]+)\)"

        def replace_image(match):
            """이미지를 figure 구조로 변환하는 함수"""
            alt_text = match.group(1)  # alt 텍스트
            image_url = match.group(2)  # 이미지 URL

            # figure 태그로 감싸진 img 태그 생성
            return (
                f'<figure class="{self.css_classes["figure"]}">'
                + f'<img src="{image_url}" alt="{alt_text}" loading="lazy">'
                + f"</figure>"
            )

        # 모든 마크다운 이미지를 figure 구조로 변환
        content = re.sub(image_pattern, replace_image, content)

        return content

    def _convert_links(self, content: str) -> str:
        """마크다운 링크를 HTML <a> 태그로 변환

        마크다운 형식: [텍스트](URL)
        HTML 형식: <a href="URL" target="_blank" rel="noopener">텍스트</a>

        주의: 이미지(![...](...)는 제외하고 일반 링크만 변환
        """
        # 마크다운 링크 패턴: [텍스트](URL) - 단, 앞에 !가 없는 경우만
        link_pattern = r"(?<!!)\[([^\]]+)\]\(([^)]+)\)"

        def replace_link(match):
            """링크 변환 함수"""
            text = match.group(1)  # 앵커 텍스트
            url = match.group(2)  # URL

            # 외부링크의 경우 target="_blank" 속성 추가
            if url.startswith("http://") or url.startswith("https://"):
                return f'<a href="{url}" target="_blank" rel="noopener">{text}</a>'
            else:
                # 내부링크의 경우 (상대 경로 등)
                return f'<a href="{url}">{text}</a>'

        # 모든 마크다운 링크를 HTML 링크로 변환
        content = re.sub(link_pattern, replace_link, content)

        return content

    def _convert_tables(self, content: str) -> str:
        """마크다운 표를 HTML 표로 변환"""
        lines = content.split("\n")
        result_lines = []
        in_table = False
        table_lines = []
        header_processed = False

        for line in lines:
            # 표 시작/종료 체크 (| 로 시작하고 끝나는 라인)
            if re.match(r"^\|.*\|$", line.strip()):
                if not in_table:
                    # 표 시작
                    in_table = True
                    table_lines = []
                    header_processed = False

                table_lines.append(line)
            else:
                if in_table:
                    # 표 종료 - HTML로 변환
                    html_table = self._process_table_lines(table_lines)
                    result_lines.append(html_table)
                    in_table = False
                    table_lines = []

                # 일반 라인 추가
                result_lines.append(line)

        # 마지막에 표가 열려있다면 닫기
        if in_table:
            html_table = self._process_table_lines(table_lines)
            result_lines.append(html_table)

        return "\n".join(result_lines)

    def _process_table_lines(self, table_lines: List[str]) -> str:
        """표 라인들을 HTML 표로 변환"""
        if not table_lines:
            return ""

        html_parts = [f'<table class="{self.css_classes["table"]}">']

        for i, line in enumerate(table_lines):
            # | 제거하고 셀 분할
            cells = [cell.strip() for cell in line.strip().split("|")[1:-1]]

            if i == 0:
                # 헤더 행
                html_parts.append("  <thead>")
                html_parts.append("    <tr>")
                for cell in cells:
                    html_parts.append(
                        f'      <th class="{self.css_classes["table_header"]}">{cell}</th>'
                    )
                html_parts.append("    </tr>")
                html_parts.append("  </thead>")
                html_parts.append("  <tbody>")
            elif i == 1 and "---" in line:
                # 구분선 무시
                continue
            else:
                # 데이터 행
                html_parts.append("    <tr>")
                for cell in cells:
                    html_parts.append(
                        f'      <td class="{self.css_classes["table_cell"]}">{cell}</td>'
                    )
                html_parts.append("    </tr>")

        html_parts.append("  </tbody>")
        html_parts.append("</table>")

        return "\n".join(html_parts)

    def _convert_lists(self, content: str) -> str:
        """마크다운 목록을 HTML 목록으로 변환"""
        lines = content.split("\n")
        result_lines = []
        in_list = False

        for line in lines:
            # 목록 항목 체크 (- 로 시작)
            list_match = re.match(r"^- (.+)$", line)

            if list_match:
                if not in_list:
                    # 목록 시작
                    result_lines.append(
                        f'<ul class="{self.css_classes["content_list"]}">'
                    )
                    in_list = True

                # 목록 항목 추가
                item_text = list_match.group(1)
                result_lines.append(
                    f'  <li class="{self.css_classes["content_list_item"]}">{item_text}</li>'
                )
            else:
                if in_list:
                    # 목록 종료
                    result_lines.append("</ul>")
                    in_list = False

                # 일반 라인 추가
                result_lines.append(line)

        # 마지막에 목록이 열려있다면 닫기
        if in_list:
            result_lines.append("</ul>")

        return "\n".join(result_lines)

    def _convert_paragraphs(self, content: str) -> str:
        """빈 줄로 구분된 문단을 간결한 HTML <p> 태그로 변환 (클래스 제거)"""
        # 연속된 빈 줄을 하나로 정리
        content = re.sub(r"\n\s*\n", "\n\n", content)

        # 문단 분할
        paragraphs = content.split("\n\n")
        html_paragraphs = []

        for paragraph in paragraphs:
            paragraph = paragraph.strip()

            if not paragraph:
                continue

            # 이미 HTML 태그로 감싸진 경우 (h2, h3, ul, figure 등) 건너뛰기
            if paragraph.startswith("<") and paragraph.endswith(">"):
                html_paragraphs.append(paragraph)
            elif "<" in paragraph and ">" in paragraph:
                # HTML 태그가 포함된 복합 콘텐츠
                html_paragraphs.append(paragraph)
            else:
                # 일반 텍스트 문단 -> 간결한 <p> 태그로 감싸기 (클래스 없음)
                html_paragraphs.append(f"<p>{paragraph}</p>")

        return "\n\n".join(html_paragraphs)

    def _apply_special_section_classes(self, content: str) -> str:
        """특정 섹션에 특별한 클래스 적용 - 섹션 래퍼와 호환되도록 비활성화"""
        # 섹션 래퍼 기능과 충돌하므로 비활성화
        # 대신 _wrap_sections에서 처리하도록 변경
        return content

    def _convert_toc_structure(self, content: str) -> str:
        """목차 구조를 시맨틱 nav > ol 구조로 변환"""
        # 목차 섹션 패턴: H2 제목 + 바로 다음 p 태그 (간단한 매칭)
        toc_pattern = r"(<h2[^>]*>.*?📚.*?목차.*?</h2>)\s*\n\s*(<p>.*?</p>)"

        def convert_toc_content(match):
            """목차 내용을 nav > ol 구조로 변환 (목차만 감싸기)"""
            header = match.group(1)  # h2 제목
            toc_paragraph = match.group(2)  # <p>내용</p>

            # p 태그 제거하고 내용만 추출
            toc_content = re.sub(r"</?p>", "", toc_paragraph)

            # 줄바꿈 또는 <br> 태그로 분리된 목차 항목들을 추출
            toc_items = re.split(r"\n|<br\s*/?>", toc_content)

            # ol 태그로 목차 리스트 생성 (숫자 자동 표시)
            toc_list_items = []
            item_number = 1
            for item in toc_items:
                item = item.strip()
                if item and not item.isspace():
                    # 기존 숫자. 제거 (예: "1. " 제거)
                    item = re.sub(r"^\d+\.\s*", "", item)
                    if item:  # 비어있지 않은 항목만 추가
                        # 링크의 href 속성에서 괄호 문제 수정
                        def fix_anchor_href(match):
                            href = match.group(1)
                            text = match.group(2)
                            # href에서 괄호 제거 (앵커 ID 생성 규칙과 동일하게)
                            clean_href = href.replace("(", "").replace(")", "")
                            return f'<a href="{clean_href}">{text}</a>'

                        # 앵커 링크 수정
                        item = re.sub(
                            r'<a href="([^"]*)"[^>]*>([^<]*)</a>', fix_anchor_href, item
                        )

                        # 링크 밖의 닫는 괄호도 제거 (예: </a>) 패턴)
                        item = re.sub(r"</a>\)", "</a>", item)

                        # ol 태그의 자동 번호 매김 사용 (CSS로 제어 가능)
                        toc_list_items.append(f"    <li>{item}</li>")
                        item_number += 1

            if toc_list_items:
                # nav 태그로 목차만 감싸기
                toc_html = (
                    f'<nav class="{self.css_classes["toc_section"]}">'
                    + "\n"
                    + header
                    + "\n"
                    + f'  <ol class="{self.css_classes["toc_list"]}">'
                    + "\n"
                    + "\n".join(toc_list_items)
                    + "\n"
                    + "  </ol>"
                    + "\n"
                    + "</nav>"
                )
                return toc_html
            else:
                # 목차 항목이 없으면 원래대로 반환
                return header + "\n" + toc_paragraph

        # 목차 구조 변환 적용
        content = re.sub(
            toc_pattern, convert_toc_content, content, flags=re.MULTILINE | re.DOTALL
        )

        return content

    def _wrap_sections(self, content: str) -> str:
        """H2 태그를 기준으로 섹션을 나누어 section 태그로 감싸기"""
        # 먼저 nav 태그(목차)를 별도로 추출
        nav_pattern = r'(<nav class="[^"]*">.*?</nav>)'
        nav_match = re.search(nav_pattern, content, re.DOTALL)
        nav_content = ""

        if nav_match:
            nav_content = nav_match.group(1)
            # nav 태그를 임시로 제거
            content = re.sub(
                nav_pattern, "<!-- NAV_PLACEHOLDER -->", content, flags=re.DOTALL
            )

        # H2 태그로 콘텐츠를 분할
        h2_pattern = r"(<h2[^>]*>.*?</h2>)"

        # H2 태그를 기준으로 분할
        parts = re.split(h2_pattern, content)

        result = []
        current_section = ""

        for i, part in enumerate(parts):
            part = part.strip()
            if not part or part == "<!-- NAV_PLACEHOLDER -->":
                continue

            # H2 태그인지 확인
            if re.match(r"<h2[^>]*>", part):
                # 이전 섹션이 있으면 섹션으로 감싸기
                if current_section:
                    # 특수 섹션 클래스 확인
                    section_classes = [self.css_classes["section_wrapper"]]

                    # FAQ 섹션 확인
                    if re.search(r"FAQ", current_section, re.IGNORECASE):
                        section_classes.append(self.css_classes["faq_section"])
                    # 개요 섹션 확인
                    elif re.search(r"개요", current_section, re.IGNORECASE):
                        section_classes.append(self.css_classes["intro_section"])
                    # 마무리 섹션 확인
                    elif re.search(r"마무리|결론", current_section, re.IGNORECASE):
                        section_classes.append(self.css_classes["conclusion_section"])

                    class_attr = " ".join(section_classes)
                    wrapped_section = (
                        f'<section class="{class_attr}">\n{current_section}\n</section>'
                    )
                    result.append(wrapped_section)

                # 새 섹션 시작
                current_section = part
            else:
                # H2가 아닌 콘텐츠는 현재 섹션에 추가
                if current_section:  # H2가 있는 경우에만
                    current_section += "\n\n" + part
                else:
                    # H2 없이 시작하는 콘텐츠는 그대로 유지
                    result.append(part)

        # 마지막 섹션 처리
        if current_section:
            # 특수 섹션 클래스 확인
            section_classes = [self.css_classes["section_wrapper"]]

            # FAQ 섹션 확인
            if re.search(r"FAQ", current_section, re.IGNORECASE):
                section_classes.append(self.css_classes["faq_section"])
            # 개요 섹션 확인
            elif re.search(r"개요", current_section, re.IGNORECASE):
                section_classes.append(self.css_classes["intro_section"])
            # 마무리 섹션 확인
            elif re.search(r"마무리|결론", current_section, re.IGNORECASE):
                section_classes.append(self.css_classes["conclusion_section"])

            class_attr = " ".join(section_classes)
            wrapped_section = (
                f'<section class="{class_attr}">\n{current_section}\n</section>'
            )
            result.append(wrapped_section)

        # nav 태그를 맨 앞에 추가 (섹션 밖에)
        final_content = "\n\n".join(result)
        if nav_content:
            final_content = nav_content + "\n\n" + final_content

        return final_content

    def _wrap_with_article(self, content: str) -> str:
        """전체 콘텐츠를 article 태그로 감싸기"""
        return (
            f'<article class="{self.css_classes["article_wrapper"]}">'
            + "\n"
            + content
            + "\n"
            + "</article>"
        )

    def _cleanup_html(self, content: str) -> str:
        """HTML 정리 작업"""
        # 연속된 빈 줄 제거
        content = re.sub(r"\n\s*\n\s*\n", "\n\n", content)

        # 시작과 끝 공백 제거
        content = content.strip()

        # 문서 생성 정보 섹션 제거 (통계 정보)
        stats_pattern = r"<h2[^>]*>문서 생성 정보</h2>.*$"
        content = re.sub(stats_pattern, "", content, flags=re.DOTALL)

        return content


def convert_blog_file_to_html(
    markdown_file_path: str, output_file_path: str = None
) -> str:
    """
    블로그 마크다운 파일을 워드프레스용 HTML로 변환

    Args:
        markdown_file_path: 입력 마크다운 파일 경로
        output_file_path: 출력 HTML 파일 경로 (선택적)

    Returns:
        변환된 HTML 콘텐츠
    """
    # 마크다운 파일 읽기
    with open(markdown_file_path, "r", encoding="utf-8") as f:
        markdown_content = f.read()

    # HTML 변환
    converter = SimpleHTMLConverter()
    html_content = converter.convert_markdown_to_html(markdown_content)

    # 파일 저장 (선택적)
    if output_file_path:
        with open(output_file_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        print(f"[SUCCESS] HTML 파일 저장 완료: {output_file_path}")

    return html_content


if __name__ == "__main__":
    # 테스트용 코드
    print("단순 HTML 변환기 모듈이 로드되었습니다.")
    print("사용법: convert_blog_file_to_html('markdown_file.md', 'output.html')")
