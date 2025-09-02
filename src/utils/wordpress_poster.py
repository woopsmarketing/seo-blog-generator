#!/usr/bin/env python3
"""
WordPress 포스팅 및 이미지 업로드 유틸리티
- REST API를 통한 자동 포스팅
- 이미지 업로드 및 미디어 라이브러리 관리
- 카테고리 및 태그 자동 설정
"""

import os
import requests
import logging
from typing import Optional, Dict, List, Any
from pathlib import Path
import mimetypes
from datetime import datetime
import json

# XML-RPC 백업용 (설치되지 않은 경우 None으로 설정)
try:
    import xmlrpc.client
    from wordpress_xmlrpc import Client
    from wordpress_xmlrpc.methods import media

    XMLRPC_AVAILABLE = True
except ImportError:
    XMLRPC_AVAILABLE = False
    print("⚠️ XML-RPC 라이브러리가 설치되지 않음. REST API만 사용됩니다.")

# 로거 설정
logger = logging.getLogger(__name__)


class WordPressPoster:
    """워드프레스 자동 포스팅 클래스"""

    # 사전 정의된 카테고리 목록
    ALLOWED_CATEGORIES = [
        "SEO",
        "블로그",
        "IT",
        "PYTHON",
        "자동화",
        "AI",
        "분석도구",
        "백링크",
        "내부최적화",
        "구글",
        "마케팅",
    ]

    def __init__(self, domain: str, username: str, application_password: str):
        """
        워드프레스 포스터 초기화

        Args:
            domain: 워드프레스 사이트 도메인 (예: https://followsales.com)
            username: 관리자 아이디
            application_password: 앱 패스워드 (공백 포함 가능)
        """
        self.domain = domain.rstrip("/")
        self.username = username
        # 앱 패스워드에서 공백 제거
        self.app_password = application_password.replace(" ", "")

        # API 엔드포인트 설정
        self.posts_endpoint = f"{self.domain}/wp-json/wp/v2/posts"
        self.media_endpoint = f"{self.domain}/wp-json/wp/v2/media"
        self.categories_endpoint = f"{self.domain}/wp-json/wp/v2/categories"
        self.tags_endpoint = f"{self.domain}/wp-json/wp/v2/tags"

        logger.info(f"WordPress Poster 초기화 완료: {self.domain}")

    def test_connection(self) -> bool:
        """워드프레스 연결 테스트"""
        try:
            # 기본 API 엔드포인트 테스트
            response = requests.get(
                f"{self.domain}/wp-json/wp/v2/posts?per_page=1",
                auth=(self.username, self.app_password),
                timeout=10,
            )
            response.raise_for_status()
            logger.info("✅ 워드프레스 연결 테스트 성공")
            return True
        except Exception as e:
            logger.error(f"❌ 워드프레스 연결 실패: {e}")
            return False

    def upload_image(
        self, image_path: Path, alt_text: str = ""
    ) -> Optional[Dict[str, Any]]:
        """
        이미지를 워드프레스 미디어 라이브러리에 업로드
        REST API 우선, 실패 시 XML-RPC 백업 사용

        Args:
            image_path: 업로드할 이미지 파일 경로
            alt_text: 이미지 대체 텍스트

        Returns:
            업로드된 이미지 정보 (URL, ID 등) 또는 None
        """
        if not image_path.exists():
            logger.error(f"이미지 파일이 존재하지 않음: {image_path}")
            return None

        # MIME 타입 자동 감지
        mime_type, _ = mimetypes.guess_type(str(image_path))
        if not mime_type or not mime_type.startswith("image/"):
            logger.error(f"지원되지 않는 이미지 형식: {image_path}")
            return None

        # 파일명 안전화 (한글 및 특수문자를 언더스코어로 변환)
        import re

        safe_filename = re.sub(r"[^\w\-_\.]", "_", image_path.name)
        safe_filename = re.sub(r"_+", "_", safe_filename)  # 연속 언더스코어 제거

        # XML-RPC 업로드 (REST API 완전 제거)
        if XMLRPC_AVAILABLE:
            result = self._upload_image_xmlrpc(image_path, safe_filename, alt_text)
            if result:
                return result

        logger.error(f"모든 방법으로 이미지 업로드 실패: {image_path.name}")
        return None

    def _upload_image_xmlrpc(
        self, image_path: Path, safe_filename: str, alt_text: str
    ) -> Optional[Dict[str, Any]]:
        """XML-RPC를 통한 이미지 업로드 (백업)"""
        try:
            xmlrpc_url = f"{self.domain}/xmlrpc.php"
            wp_client = Client(
                xmlrpc_url, self.username, self.app_password.replace(" ", "")
            )

            with open(image_path, "rb") as image_file:
                data = {
                    "name": safe_filename,
                    "type": mimetypes.guess_type(str(image_path))[0],
                    "bits": xmlrpc.client.Binary(image_file.read()),
                    "overwrite": True,
                }

                response = wp_client.call(media.UploadFile(data))

                logger.info(
                    f"✅ XML-RPC 이미지 업로드 성공: {image_path.name} → {response['url']}"
                )

                return {
                    "id": response["id"],
                    "url": response["url"],
                    "title": safe_filename,
                    "alt_text": alt_text,
                    "filename": image_path.name,
                    "method": "XML-RPC",
                }

        except Exception as e:
            logger.error(f"XML-RPC 이미지 업로드 실패 ({image_path.name}): {e}")
            return None

    def _update_media_alt_text(self, media_id: int, alt_text: str):
        """미디어의 Alt 텍스트 업데이트"""
        try:
            update_data = {"alt_text": alt_text}

            response = requests.post(
                f"{self.media_endpoint}/{media_id}",
                json=update_data,
                auth=(self.username, self.app_password),
                timeout=10,
            )
            response.raise_for_status()

        except Exception as e:
            logger.warning(f"Alt 텍스트 설정 실패 (Media ID: {media_id}): {e}")

    def get_or_create_category(self, category_name: str) -> Optional[int]:
        """카테고리 가져오기 또는 생성"""
        try:
            # 기존 카테고리 검색
            response = requests.get(
                f"{self.categories_endpoint}?search={category_name}",
                auth=(self.username, self.app_password),
                timeout=10,
            )
            response.raise_for_status()
            categories = response.json()

            # 기존 카테고리가 있으면 ID 반환
            for category in categories:
                if category["name"].lower() == category_name.lower():
                    return category["id"]

            # 없으면 새로 생성
            create_data = {
                "name": category_name,
                "slug": category_name.lower().replace(" ", "-"),
            }

            response = requests.post(
                self.categories_endpoint,
                json=create_data,
                auth=(self.username, self.app_password),
                timeout=10,
            )
            response.raise_for_status()

            new_category = response.json()
            logger.info(
                f"✅ 새 카테고리 생성: {category_name} (ID: {new_category['id']})"
            )
            return new_category["id"]

        except Exception as e:
            logger.error(f"카테고리 처리 실패 ({category_name}): {e}")
            return None

    def get_or_create_tag(self, tag_name: str) -> Optional[int]:
        """태그 가져오기 또는 생성"""
        try:
            # 기존 태그 검색
            response = requests.get(
                f"{self.tags_endpoint}?search={tag_name}",
                auth=(self.username, self.app_password),
                timeout=10,
            )
            response.raise_for_status()
            tags = response.json()

            # 기존 태그가 있으면 ID 반환
            for tag in tags:
                if tag["name"].lower() == tag_name.lower():
                    return tag["id"]

            # 없으면 새로 생성
            create_data = {"name": tag_name, "slug": tag_name.lower().replace(" ", "-")}

            response = requests.post(
                self.tags_endpoint,
                json=create_data,
                auth=(self.username, self.app_password),
                timeout=10,
            )
            response.raise_for_status()

            new_tag = response.json()
            logger.info(f"✅ 새 태그 생성: {tag_name} (ID: {new_tag['id']})")
            return new_tag["id"]

        except Exception as e:
            logger.error(f"태그 처리 실패 ({tag_name}): {e}")
            return None

    def post_article(
        self,
        title: str,
        html_content: str,
        status: str = "publish",
        category_names: Optional[List[str]] = None,
        tag_names: Optional[List[str]] = None,
        excerpt: str = "",
        featured_image_path: Optional[Path] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        블로그 글 발행

        Args:
            title: 글 제목
            html_content: HTML 형식의 본문 내용
            status: 발행 상태 ('publish', 'draft', 'private')
            category_names: 카테고리 이름 리스트
            tag_names: 태그 이름 리스트
            excerpt: 글 요약
            featured_image_path: 대표 이미지 파일 경로

        Returns:
            발행된 글 정보 (URL, ID 등) 또는 None
        """
        try:
            # 포스트 데이터 준비
            post_data: Dict[str, Any] = {
                "title": title,
                "content": html_content,
                "status": status,
                "excerpt": excerpt,
                "date": datetime.now().isoformat(),
            }

            # 카테고리 처리
            if category_names:
                category_ids = []
                for cat_name in category_names:
                    cat_id = self.get_or_create_category(cat_name)
                    if cat_id:
                        category_ids.append(cat_id)
                if category_ids:
                    post_data["categories"] = category_ids

            # 태그 처리
            if tag_names:
                tag_ids = []
                for tag_name in tag_names:
                    tag_id = self.get_or_create_tag(tag_name)
                    if tag_id:
                        tag_ids.append(tag_id)
                if tag_ids:
                    post_data["tags"] = tag_ids

            # 대표 이미지 업로드 및 설정
            if featured_image_path and featured_image_path.exists():
                featured_image = self.upload_image(
                    featured_image_path, f"{title} 대표 이미지"
                )
                if featured_image:
                    post_data["featured_media"] = featured_image["id"]

            # 포스트 발행
            logger.info(f"워드프레스에 포스팅 중: {title}")
            response = requests.post(
                self.posts_endpoint,
                json=post_data,
                auth=(self.username, self.app_password),
                timeout=60,  # 긴 콘텐츠 업로드를 위해 타임아웃 증가
            )
            response.raise_for_status()

            post_json = response.json()

            result = {
                "id": post_json["id"],
                "title": post_json["title"]["rendered"],
                "url": post_json["link"],
                "status": post_json["status"],
                "date": post_json["date"],
                "excerpt": post_json["excerpt"]["rendered"],
            }

            logger.info(f"✅ 포스팅 성공: {title}")
            logger.info(f"   📄 포스트 ID: {result['id']}")
            logger.info(f"   🔗 URL: {result['url']}")

            return result

        except Exception as e:
            logger.error(f"❌ 포스팅 실패 ({title}): {e}")
            if hasattr(e, "response") and e.response is not None:
                try:
                    error_detail = e.response.json()
                    logger.error(f"   상세 오류: {error_detail}")
                except:
                    logger.error(f"   HTTP 상태 코드: {e.response.status_code}")
            return None

    def process_images_in_content(self, html_content: str, images_dir: Path) -> str:
        """
        HTML 콘텐츠 내의 로컬 이미지를 워드프레스에 업로드하고 URL 교체

        Args:
            html_content: HTML 형식의 콘텐츠
            images_dir: 로컬 이미지 디렉토리 경로

        Returns:
            이미지 URL이 교체된 HTML 콘텐츠
        """
        import re

        # 다양한 로컬 이미지 URL 패턴 찾기
        image_patterns = [
            r'src="([^"]*\/images\/[^"]*)"',  # /images/ 경로
            r'src="([^"]*@images\/[^"]*)"',  # @images/ 경로
            r'src="(images\/[^"]*)"',  # images/ 시작
            r'src="(@images\/[^"]*)"',  # @images/ 시작
        ]

        processed_files = set()  # 중복 처리 방지

        for pattern in image_patterns:
            matches = re.findall(pattern, html_content)

            for local_url in matches:
                # 파일명 추출
                filename = local_url.split("/")[-1]

                # 이미 처리된 파일은 건너뛰기
                if filename in processed_files:
                    continue

                local_image_path = images_dir / filename

                if local_image_path.exists():
                    # 워드프레스에 이미지 업로드
                    uploaded_image = self.upload_image(
                        local_image_path, f"블로그 이미지: {filename}"
                    )

                    if uploaded_image:
                        # HTML 콘텐츠에서 모든 해당 URL 교체
                        html_content = html_content.replace(
                            local_url, uploaded_image["url"]
                        )
                        logger.info(
                            f"🖼️ 이미지 URL 교체: {filename} → {uploaded_image['url']}"
                        )
                        processed_files.add(filename)
                    else:
                        logger.warning(f"⚠️ 이미지 업로드 실패: {filename}")
                else:
                    logger.warning(f"⚠️ 로컬 이미지 파일 없음: {local_image_path}")

        if processed_files:
            logger.info(f"✅ 총 {len(processed_files)}개 이미지 처리 완료")
        else:
            logger.info("ℹ️ 처리할 로컬 이미지가 없습니다.")

        return html_content

    def select_best_categories(
        self, title: str, content: str, keywords: List[str] = None
    ) -> List[str]:
        """
        콘텐츠 분석을 통한 최적 카테고리 자동 선별

        Args:
            title: 글 제목
            content: 글 본문 (HTML 또는 마크다운)
            keywords: 키워드 리스트 (선택사항)

        Returns:
            선별된 카테고리 이름 리스트 (최대 3개)
        """
        try:
            # 텍스트 전처리 (HTML 태그 제거)
            import re

            clean_content = re.sub(r"<[^>]+>", " ", content)
            clean_title = re.sub(r"<[^>]+>", " ", title)

            # 분석할 전체 텍스트 조합
            full_text = f"{clean_title} {clean_content}"
            if keywords:
                full_text += " " + " ".join(keywords)

            full_text = full_text.lower()

            # 카테고리별 점수 계산
            category_scores = {}

            # 카테고리별 키워드 매핑
            category_keywords = {
                "SEO": [
                    "seo",
                    "검색엔진최적화",
                    "검색엔진",
                    "구글",
                    "네이버",
                    "검색",
                    "순위",
                    "키워드",
                    "메타태그",
                    "백링크",
                    "링크빌딩",
                    "도메인",
                    "페이지랭크",
                    "색인",
                    "크롤링",
                    "검색결과",
                    "serp",
                    "온페이지",
                    "오프페이지",
                    "최적화",
                    "랭킹",
                    "트래픽",
                ],
                "블로그": [
                    "블로그",
                    "포스팅",
                    "콘텐츠",
                    "글쓰기",
                    "워드프레스",
                    "티스토리",
                    "네이버블로그",
                    "블로거",
                    "포스트",
                    "아티클",
                    "글",
                    "작성",
                    "발행",
                    "게시",
                    "콘텐츠마케팅",
                ],
                "IT": [
                    "it",
                    "정보기술",
                    "소프트웨어",
                    "하드웨어",
                    "프로그래밍",
                    "개발",
                    "코딩",
                    "시스템",
                    "네트워크",
                    "데이터베이스",
                    "서버",
                    "클라우드",
                    "보안",
                    "기술",
                ],
                "PYTHON": [
                    "python",
                    "파이썬",
                    "django",
                    "flask",
                    "pandas",
                    "numpy",
                    "matplotlib",
                    "jupyter",
                    "anaconda",
                    "pip",
                    "라이브러리",
                    "프레임워크",
                    "스크립트",
                ],
                "자동화": [
                    "자동화",
                    "automation",
                    "봇",
                    "스크립트",
                    "매크로",
                    "크롤링",
                    "스크래핑",
                    "rpa",
                    "워크플로우",
                    "프로세스",
                    "효율화",
                    "자동",
                    "배치",
                    "스케줄링",
                ],
                "AI": [
                    "ai",
                    "인공지능",
                    "머신러닝",
                    "딥러닝",
                    "neural",
                    "gpt",
                    "chatgpt",
                    "llm",
                    "자연어처리",
                    "컴퓨터비전",
                    "알고리즘",
                    "모델",
                    "학습",
                    "예측",
                    "분류",
                ],
                "분석도구": [
                    "분석",
                    "analytics",
                    "구글애널리틱스",
                    "ga4",
                    "데이터",
                    "통계",
                    "지표",
                    "측정",
                    "추적",
                    "모니터링",
                    "리포트",
                    "대시보드",
                    "시각화",
                    "차트",
                ],
                "백링크": [
                    "백링크",
                    "backlink",
                    "링크빌딩",
                    "외부링크",
                    "도메인권한",
                    "da",
                    "pa",
                    "링크",
                    "참조",
                    "인용",
                    "연결",
                    "링크프로필",
                    "앵커텍스트",
                ],
                "내부최적화": [
                    "내부최적화",
                    "온페이지",
                    "메타태그",
                    "title",
                    "description",
                    "h1",
                    "h2",
                    "내부링크",
                    "사이트구조",
                    "url구조",
                    "속도최적화",
                    "모바일최적화",
                ],
                "구글": [
                    "구글",
                    "google",
                    "서치콘솔",
                    "애드워즈",
                    "애드센스",
                    "구글봇",
                    "구글알고리즘",
                    "페이지스피드",
                    "구글마이비즈니스",
                ],
                "마케팅": [
                    "마케팅",
                    "marketing",
                    "디지털마케팅",
                    "온라인마케팅",
                    "광고",
                    "홍보",
                    "브랜딩",
                    "고객",
                    "타겟",
                    "전환",
                    "roi",
                    "ctr",
                    "cpc",
                    "캠페인",
                ],
            }

            # 각 카테고리별 점수 계산
            for category in self.ALLOWED_CATEGORIES:
                score = 0
                if category in category_keywords:
                    keywords_list = category_keywords[category]
                    for keyword in keywords_list:
                        # 키워드 출현 빈도 계산
                        count = full_text.count(keyword)
                        if count > 0:
                            # 제목에서 발견되면 가중치 2배
                            title_count = clean_title.lower().count(keyword)
                            score += count + (title_count * 2)

                category_scores[category] = score

            # 점수 순으로 정렬하여 상위 카테고리 선택
            sorted_categories = sorted(
                category_scores.items(), key=lambda x: x[1], reverse=True
            )

            # 점수가 0보다 큰 카테고리만 선택 (최대 3개)
            selected_categories = []
            for category, score in sorted_categories:
                if score > 0 and len(selected_categories) < 3:
                    selected_categories.append(category)

            # 카테고리가 하나도 선택되지 않은 경우 기본값 설정
            if not selected_categories:
                selected_categories = ["블로그"]  # 기본 카테고리

            logger.info(f"🏷️ 선별된 카테고리: {selected_categories}")
            logger.info(f"   점수 분포: {dict(sorted_categories[:5])}")

            return selected_categories

        except Exception as e:
            logger.error(f"카테고리 선별 중 오류 발생: {e}")
            return ["블로그"]  # 오류 시 기본 카테고리 반환


# 편의를 위한 팩토리 함수
def create_wordpress_poster() -> WordPressPoster:
    """환경변수 또는 설정에서 워드프레스 포스터 생성"""
    domain = os.getenv("WORDPRESS_DOMAIN", "https://followsales.com")
    username = os.getenv("WORDPRESS_USERNAME", "followsales")
    app_password = os.getenv("WORDPRESS_APP_PASSWORD", "otFv tHVG aAQc gYvi 518v Ah4o")

    return WordPressPoster(domain, username, app_password)


if __name__ == "__main__":
    # 테스트 코드
    poster = create_wordpress_poster()

    # 연결 테스트
    if poster.test_connection():
        print("✅ 워드프레스 연결 성공!")
    else:
        print("❌ 워드프레스 연결 실패!")
