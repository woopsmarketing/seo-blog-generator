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
        """워드프레스 호환 CSS 클래스 정의"""
        return {
            # 섹션 관련
            "main_title": "blog-main-title",  # H1 제목
            "section_title": "blog-section-title",  # H2 제목
            "subsection_title": "blog-subsection",  # H3 제목
            "subsubsection_title": "blog-subsubsection",  # H4 제목
            # 콘텐츠 관련
            "content_paragraph": "blog-content",  # 일반 문단
            "content_list": "blog-list",  # 목록 컨테이너
            "content_list_item": "blog-list-item",  # 목록 항목
            # 표 관련
            "table": "blog-table",  # 표 컨테이너
            "table_header": "blog-table-header",  # 표 헤더
            "table_cell": "blog-table-cell",  # 표 셀
            # 특수 섹션
            "faq_section": "blog-faq",  # FAQ 섹션
            "intro_section": "blog-intro",  # 개요 섹션
            "conclusion_section": "blog-conclusion",  # 마무리 섹션
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

        # 5. 표 변환
        html = self._convert_tables(html)

        # 6. 목록 변환
        html = self._convert_lists(html)

        # 7. 문단 변환
        html = self._convert_paragraphs(html)

        # 7. 특수 섹션 클래스 적용
        html = self._apply_special_section_classes(html)

        # 8. 정리 작업
        html = self._cleanup_html(html)

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

        # 메타데이터 패턴 제거: **키워드:** 값
        content = re.sub(r"(\*\*[^:]+:[^\n]+\n)+\n", "", content, flags=re.MULTILINE)

        return content

    def _convert_headings(self, content: str) -> str:
        """마크다운 제목을 HTML 제목으로 변환 (H2부터 시작)"""
        # H2 변환 (## 제목)
        content = re.sub(
            r"^## (.+)$",
            f'<h2 class="{self.css_classes["section_title"]}">\\1</h2>',
            content,
            flags=re.MULTILINE,
        )

        # H3 변환 (### 제목)
        content = re.sub(
            r"^### (.+)$",
            f'<h3 class="{self.css_classes["subsection_title"]}">\\1</h3>',
            content,
            flags=re.MULTILINE,
        )

        # H4 변환 (#### 제목)
        content = re.sub(
            r"^#### (.+)$",
            f'<h4 class="{self.css_classes["subsubsection_title"]}">\\1</h4>',
            content,
            flags=re.MULTILINE,
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
        """빈 줄로 구분된 문단을 HTML <p> 태그로 변환"""
        # 연속된 빈 줄을 하나로 정리
        content = re.sub(r"\n\s*\n", "\n\n", content)

        # 문단 분할
        paragraphs = content.split("\n\n")
        html_paragraphs = []

        for paragraph in paragraphs:
            paragraph = paragraph.strip()

            if not paragraph:
                continue

            # 이미 HTML 태그로 감싸진 경우 (h2, h3, ul 등) 건너뛰기
            if paragraph.startswith("<") and paragraph.endswith(">"):
                html_paragraphs.append(paragraph)
            elif "<" in paragraph and ">" in paragraph:
                # HTML 태그가 포함된 복합 콘텐츠
                html_paragraphs.append(paragraph)
            else:
                # 일반 텍스트 문단 -> <p> 태그로 감싸기
                html_paragraphs.append(
                    f'<p class="{self.css_classes["content_paragraph"]}">{paragraph}</p>'
                )

        return "\n\n".join(html_paragraphs)

    def _apply_special_section_classes(self, content: str) -> str:
        """특정 섹션에 특별한 클래스 적용"""
        # FAQ 섹션
        content = re.sub(
            r'(<h2 class="[^"]*">FAQ</h2>)',
            f'<h2 class="{self.css_classes["faq_section"]} {self.css_classes["section_title"]}">FAQ</h2>',
            content,
        )

        # 개요 섹션
        content = re.sub(
            r'(<h2 class="[^"]*">개요</h2>)',
            f'<h2 class="{self.css_classes["intro_section"]} {self.css_classes["section_title"]}">개요</h2>',
            content,
        )

        # 마무리 섹션
        content = re.sub(
            r'(<h2 class="[^"]*">마무리</h2>)',
            f'<h2 class="{self.css_classes["conclusion_section"]} {self.css_classes["section_title"]}">마무리</h2>',
            content,
        )

        return content

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
        print(f"✅ HTML 파일 저장 완료: {output_file_path}")

    return html_content


if __name__ == "__main__":
    # 테스트용 코드
    print("단순 HTML 변환기 모듈이 로드되었습니다.")
    print("사용법: convert_blog_file_to_html('markdown_file.md', 'output.html')")
