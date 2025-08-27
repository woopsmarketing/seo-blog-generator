# -*- coding: utf-8 -*-
"""
워드프레스용 최종 HTML 변환 스크립트 (H1 제거 버전)
H1 태그는 제거하고 H2부터 시작하는 워드프레스 업로드용 HTML 생성
"""

import sys
from pathlib import Path
from datetime import datetime

# 현재 디렉토리를 Python 경로에 추가
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

from src.generators.html.simple_html_converter import convert_blog_file_to_html

def convert_for_wordpress():
    """워드프레스용 최종 HTML 변환 (H1 제거)"""
    
    # 한글 출력 인코딩 설정
    if sys.platform.startswith('win'):
        import codecs
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.detach())
    
    print("🔄 워드프레스용 최종 HTML 변환 (H1 제거)")
    print("=" * 60)
    
    # 파일 경로 설정
    data_dir = Path("data")
    md_file = data_dir / "blog_클로드코드_20250826_212133.md"
    html_file = data_dir / "blog_클로드코드_wordpress.html"
    
    try:
        # 마크다운 파일 존재 확인
        if not md_file.exists():
            print(f"❌ 마크다운 파일이 존재하지 않습니다: {md_file}")
            return False
        
        print(f"📝 입력 파일: {md_file}")
        print(f"🌐 출력 파일: {html_file}")
        
        # HTML 변환 실행 (수정된 변환기 사용)
        print("\n🔄 마크다운 → HTML 변환 중... (H1 제거, H2부터 시작)")
        html_content = convert_blog_file_to_html(str(md_file), str(html_file))
        
        # 변환 결과 분석
        print("\n✅ 변환 완료!")
        print(f"📊 변환 결과:")
        print(f"  • HTML 길이: {len(html_content):,} 문자")
        print(f"  • HTML 라인 수: {len(html_content.splitlines())} 줄")
        
        # HTML 구조 분석
        h1_count = html_content.count('<h1')
        h2_count = html_content.count('<h2')
        h3_count = html_content.count('<h3') 
        p_count = html_content.count('<p')
        
        print(f"  • H1 헤딩: {h1_count}개 (워드프레스용: 0개여야 함)")
        print(f"  • H2 헤딩: {h2_count}개")
        print(f"  • H3 헤딩: {h3_count}개") 
        print(f"  • 문단: {p_count}개")
        
        # H1 제거 확인
        if h1_count == 0:
            print("✅ H1 태그 제거 성공! 워드프레스 업로드 준비 완료")
        else:
            print("⚠️ H1 태그가 여전히 존재합니다.")
        
        # HTML 미리보기 (처음 30줄)
        print(f"\n🔍 HTML 미리보기 (처음 30줄):")
        print("-" * 60)
        
        html_lines = html_content.splitlines()
        for i, line in enumerate(html_lines[:30], 1):
            print(f"{i:2d}: {line}")
            
        if len(html_lines) > 30:
            print(f"... ({len(html_lines) - 30}줄 더)")
        
        return True
        
    except Exception as e:
        print(f"❌ 변환 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

def show_wordpress_instructions():
    """워드프레스 업로드 안내"""
    print(f"\n📋 워드프레스 업로드 안내")
    print("=" * 40)
    print("1. 워드프레스 관리자 로그인")
    print("2. 글쓰기 > 새 글 추가")
    print("3. 제목: 클로드코드 완벽 가이드: 올바른 활용법과 팁")
    print("4. 본문: blog_클로드코드_wordpress.html 파일 내용 복사")
    print("5. SEO 플러그인이 메타 디스크립션 자동 생성")
    print("6. 발행!")
    
    print(f"\n💡 REST API 자동화 업로드:")
    print("- POST /wp/v2/posts")
    print("- title: '클로드코드 완벽 가이드: 올바른 활용법과 팁'")
    print("- content: HTML 파일 내용")
    print("- status: 'publish'")

def main():
    """메인 실행 함수"""
    success = convert_for_wordpress()
    
    if success:
        show_wordpress_instructions()
        
        print(f"\n✅ 모든 작업 완료!")
        print(f"📁 파일:")
        print(f"  • 마크다운: data/blog_클로드코드_20250826_212133.md")
        print(f"  • 워드프레스용 HTML: data/blog_클로드코드_wordpress.html")
        print(f"  • 상세 리포트: data/detailed_report_클로드코드_20250826_215704.json")
        
    else:
        print(f"\n❌ 변환 실패")

if __name__ == "__main__":
    main()