# -*- coding: utf-8 -*-
"""
워드프레스 HTML 변환 테스트 스크립트
생성된 마크다운을 워드프레스 REST API용 HTML로 변환하고 두 파일 모두 확인
"""

import sys
from pathlib import Path
from datetime import datetime

# 현재 디렉토리를 Python 경로에 추가
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

from src.generators.html.simple_html_converter import SimpleHTMLConverter, convert_blog_file_to_html

def convert_claude_code_blog():
    """클로드코드 블로그를 HTML로 변환"""
    
    # 파일 경로 설정
    data_dir = Path("data")
    md_file = data_dir / "blog_클로드코드_20250826_212133.md"
    html_file = data_dir / "blog_클로드코드_20250826_212133.html"
    
    print("🔄 워드프레스용 HTML 변환 시작...")
    print(f"입력 파일: {md_file}")
    print(f"출력 파일: {html_file}")
    
    try:
        # 마크다운 파일 존재 확인
        if not md_file.exists():
            print(f"❌ 마크다운 파일이 존재하지 않습니다: {md_file}")
            return False
        
        # HTML 변환 실행
        print("\n📝 마크다운 → HTML 변환 중...")
        html_content = convert_blog_file_to_html(str(md_file), str(html_file))
        
        # 변환 결과 통계
        with open(md_file, 'r', encoding='utf-8') as f:
            md_content = f.read()
            
        print("\n✅ 변환 완료!")
        print(f"📊 변환 통계:")
        print(f"  • 마크다운 길이: {len(md_content):,} 문자")
        print(f"  • HTML 길이: {len(html_content):,} 문자")
        print(f"  • HTML 라인 수: {len(html_content.splitlines())} 줄")
        
        # HTML 구조 분석
        h2_count = html_content.count('<h2')
        h3_count = html_content.count('<h3') 
        p_count = html_content.count('<p')
        
        print(f"  • H2 헤딩: {h2_count}개")
        print(f"  • H3 헤딩: {h3_count}개") 
        print(f"  • 문단: {p_count}개")
        
        return True
        
    except Exception as e:
        print(f"❌ 변환 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

def display_file_previews():
    """MD와 HTML 파일 미리보기"""
    
    data_dir = Path("data")
    md_file = data_dir / "blog_클로드코드_20250826_212133.md"
    html_file = data_dir / "blog_클로드코드_20250826_212133.html"
    
    print("\n" + "="*80)
    print("📋 파일 미리보기")
    print("="*80)
    
    # 마크다운 미리보기
    if md_file.exists():
        print(f"\n📝 마크다운 파일 미리보기: {md_file.name}")
        print("-" * 50)
        
        with open(md_file, 'r', encoding='utf-8') as f:
            md_lines = f.readlines()
            
        # 처음 20줄만 출력
        for i, line in enumerate(md_lines[:20], 1):
            print(f"{i:2d}: {line.rstrip()}")
            
        if len(md_lines) > 20:
            print(f"... ({len(md_lines) - 20}줄 더)")
    
    # HTML 미리보기
    if html_file.exists():
        print(f"\n🌐 HTML 파일 미리보기: {html_file.name}")
        print("-" * 50)
        
        with open(html_file, 'r', encoding='utf-8') as f:
            html_lines = f.readlines()
            
        # 처음 25줄만 출력 (HTML은 태그 때문에 더 길 수 있음)
        for i, line in enumerate(html_lines[:25], 1):
            print(f"{i:2d}: {line.rstrip()}")
            
        if len(html_lines) > 25:
            print(f"... ({len(html_lines) - 25}줄 더)")

def show_html_structure():
    """HTML 구조 분석 및 표시"""
    
    data_dir = Path("data")
    html_file = data_dir / "blog_클로드코드_20250826_212133.html"
    
    if not html_file.exists():
        print("❌ HTML 파일이 존재하지 않습니다.")
        return
        
    print(f"\n🔍 HTML 구조 분석: {html_file.name}")
    print("-" * 60)
    
    with open(html_file, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    # 헤딩 구조 추출
    import re
    
    h2_matches = re.findall(r'<h2[^>]*>(.*?)</h2>', html_content)
    h3_matches = re.findall(r'<h3[^>]*>(.*?)</h3>', html_content)
    
    print("📋 헤딩 구조:")
    for i, h2 in enumerate(h2_matches, 1):
        print(f"  {i}. H2: {h2}")
        
        # 해당 H2 다음에 오는 H3들 찾기 (간단한 로직)
        h2_index = html_content.find(f'<h2')
        if i < len(h2_matches):
            next_h2_index = html_content.find(f'<h2', h2_index + 1)
        else:
            next_h2_index = len(html_content)
            
        section_content = html_content[h2_index:next_h2_index]
        section_h3s = re.findall(r'<h3[^>]*>(.*?)</h3>', section_content)
        
        for j, h3 in enumerate(section_h3s, 1):
            print(f"    {i}.{j} H3: {h3}")
    
    # CSS 클래스 사용 현황
    print(f"\n🎨 CSS 클래스 사용 현황:")
    classes = [
        "blog-section-title",
        "blog-subsection", 
        "blog-content",
        "blog-faq",
        "blog-intro",
        "blog-conclusion"
    ]
    
    for css_class in classes:
        count = html_content.count(f'class="{css_class}')
        if count > 0:
            print(f"  • {css_class}: {count}회 사용")

def main():
    """메인 실행 함수"""
    # 한글 출력 인코딩 설정
    if sys.platform.startswith('win'):
        import codecs
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.detach())
    
    print("🚀 워드프레스 HTML 변환 및 미리보기 도구")
    print("=" * 60)
    
    # HTML 변환 실행
    success = convert_claude_code_blog()
    
    if success:
        # 파일 미리보기
        display_file_previews()
        
        # HTML 구조 분석
        show_html_structure()
        
        print(f"\n✅ 모든 작업 완료!")
        print(f"📁 파일 위치:")
        print(f"  • 마크다운: data/blog_클로드코드_20250826_212133.md")
        print(f"  • HTML: data/blog_클로드코드_20250826_212133.html")
        print(f"\n💡 이제 두 파일을 직접 열어서 확인하세요!")
        
    else:
        print(f"\n❌ 변환 실패 - 위의 오류를 확인하세요.")

if __name__ == "__main__":
    main()