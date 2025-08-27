# -*- coding: utf-8 -*-
"""
마크다운 파일을 HTML로 변환하는 간단한 스크립트

- LLM 사용 안함 ✅
- 하드코딩 방식 ✅
- 워드프레스 호환 CSS 클래스 ✅
"""

import re
from datetime import datetime


def convert_markdown_to_html(md_file_path, html_file_path):
    """마크다운 파일을 HTML로 변환"""

    print(f"📄 마크다운 파일 읽기: {md_file_path}")

    # 마크다운 파일 읽기
    with open(md_file_path, "r", encoding="utf-8") as f:
        md_content = f.read()

    print(f"📝 원본 길이: {len(md_content):,}자")

    # HTML 변환 시작
    html_lines = []

    # 라인별로 처리
    lines = md_content.split("\n")

    for line in lines:
        # 공백 라인
        if not line.strip():
            continue

        # HTML 주석 (디버깅 정보) - 그대로 유지
        if line.strip().startswith("<!--"):
            html_lines.append(line)
            continue

        # 메타데이터 (키워드, 생성일, SEO 점수) - 건너뛰기
        if (
            line.startswith("**키워드**:")
            or line.startswith("**생성일**:")
            or line.startswith("**SEO 점수**:")
        ):
            continue

        # 구분선 (---) - 건너뛰기
        if line.strip() == "---":
            continue

        # H1 제목 (메인 제목)
        if line.startswith("# "):
            title_text = line[2:].strip()
            html_lines.append(f'<h1 class="blog-main-title">{title_text}</h1>')
            continue

        # H2 제목 (섹션 제목)
        if line.startswith("## "):
            # "📍 섹션 1: 개요" -> "개요"로 정리
            h2_text = line[3:].strip()
            if "📍 섹션" in h2_text and ":" in h2_text:
                h2_text = h2_text.split(":", 1)[1].strip()
            elif h2_text.startswith("📊"):
                h2_text = h2_text[2:].strip()  # 이모지 제거

            html_lines.append(f'<h2 class="blog-section-title">{h2_text}</h2>')
            continue

        # H3 제목 (하위 섹션)
        if line.startswith("### "):
            h3_text = line[4:].strip()
            html_lines.append(f'<h3 class="blog-subsection-title">{h3_text}</h3>')
            continue

        # 리스트 항목 (- 또는 |)
        if line.strip().startswith("- "):
            list_text = line.strip()[2:].strip()
            html_lines.append(f'<li class="blog-list-item">{list_text}</li>')
            continue

        # 테이블 헤더
        if "|" in line and line.count("|") >= 3:
            # 테이블 구분선은 건너뛰기
            if line.strip().replace("|", "").replace("-", "").replace(" ", "") == "":
                continue

            # 테이블 헤더나 데이터 행 처리
            cells = [
                cell.strip() for cell in line.split("|")[1:-1]
            ]  # 양쪽 빈 부분 제거

            if any(cell in ["섹션", "제목", "길이"] for cell in cells):
                # 헤더 행
                html_lines.append('<table class="blog-table">')
                html_lines.append("<thead>")
                html_lines.append("<tr>")
                for cell in cells:
                    html_lines.append(f'<th class="blog-table-header">{cell}</th>')
                html_lines.append("</tr>")
                html_lines.append("</thead>")
                html_lines.append("<tbody>")
            else:
                # 데이터 행
                html_lines.append("<tr>")
                for cell in cells:
                    html_lines.append(f'<td class="blog-table-cell">{cell}</td>')
                html_lines.append("</tr>")
            continue

        # Q: A: 형식 (FAQ)
        if line.strip().startswith("Q:"):
            question = line.strip()[2:].strip()
            html_lines.append(f'<div class="blog-faq-question">Q: {question}</div>')
            continue

        if line.strip().startswith("A:"):
            answer = line.strip()[2:].strip()
            html_lines.append(f'<div class="blog-faq-answer">A: {answer}</div>')
            continue

        # 일반 텍스트 (문단)
        if line.strip():
            # 특수 문자 처리
            text = line.strip()
            html_lines.append(f'<p class="blog-content">{text}</p>')

    # 테이블이 열려있으면 닫기
    if any("</tbody>" in line for line in html_lines):
        # 마지막에 테이블 닫기 태그가 없으면 추가
        if html_lines and not html_lines[-1].endswith("</table>"):
            html_lines.append("</tbody>")
            html_lines.append("</table>")

    # 리스트가 있으면 ul 태그로 감싸기
    final_html = []
    in_list = False

    for line in html_lines:
        if '<li class="blog-list-item">' in line:
            if not in_list:
                final_html.append('<ul class="blog-list">')
                in_list = True
            final_html.append(line)
        else:
            if in_list:
                final_html.append("</ul>")
                in_list = False
            final_html.append(line)

    # 마지막에 리스트가 열려있으면 닫기
    if in_list:
        final_html.append("</ul>")

    # HTML 생성
    html_content = "\n".join(final_html)

    # HTML 파일 저장
    with open(html_file_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    print(f"✅ HTML 변환 완료!")
    print(f"📝 변환된 길이: {len(html_content):,}자")
    print(f"💾 저장 위치: {html_file_path}")

    return html_content


def main():
    """메인 실행 함수"""

    print("🔄 마크다운 → HTML 변환기")
    print("=" * 50)

    # 파일 경로
    md_file = "data/blog_도파민_20250824_211310.md"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    html_file = f"data/도파민_wordpress_{timestamp}.html"
    txt_file = f"data/도파민_wordpress_{timestamp}.txt"

    try:
        # 마크다운을 HTML로 변환
        html_content = convert_markdown_to_html(md_file, html_file)

        # 텍스트 파일로도 저장 (검토용)
        with open(txt_file, "w", encoding="utf-8") as f:
            f.write(html_content)

        print(f"\n🎉 변환 완료!")
        print(f"📄 HTML 파일: {html_file}")
        print(f"📄 텍스트 파일: {txt_file}")

        # 간단한 통계
        h2_count = html_content.count('<h2 class="blog-section-title">')
        h3_count = html_content.count('<h3 class="blog-subsection-title">')
        p_count = html_content.count('<p class="blog-content">')

        print(f"\n📊 변환 통계:")
        print(f"   H2 섹션: {h2_count}개")
        print(f"   H3 하위섹션: {h3_count}개")
        print(f"   문단: {p_count}개")

    except Exception as e:
        print(f"❌ 변환 실패: {e}")


if __name__ == "__main__":
    main()
