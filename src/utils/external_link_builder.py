#!/usr/bin/env python3
"""
외부링크 생성 시스템
- 초기 5-10개 포스팅용 외부링크 생성
- 검색엔진 기반 링크 생성
- 키워드 매칭 및 URL 인코딩
"""

import random
import urllib.parse
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass


@dataclass
class ExternalLink:
    """외부링크 정보 클래스"""

    anchor_text: str  # 앵커텍스트 (키워드)
    url: str  # 링크 URL
    platform: str  # 플랫폼 이름
    keyword_type: str  # 키워드 타입 (핵심/LSI/롱테일)


class ExternalLinkBuilder:
    """외부링크 생성 클래스"""

    def __init__(self):
        """외부링크 빌더 초기화"""
        self.platforms = {
            "나무위키": {
                "url_template": "https://namu.wiki/w/{keyword}",
                "weight": 15,  # 가중치 (높을수록 자주 선택)
                "encoding": "utf-8",
            },
            "구글검색": {
                "url_template": "https://www.google.com/search?q={keyword}",
                "weight": 20,
                "encoding": "url",
            },
            "네이버검색": {
                "url_template": "https://search.naver.com/search.naver?query={keyword}",
                "weight": 20,
                "encoding": "url",
            },
            "다음검색": {
                "url_template": "https://search.daum.net/search?q={keyword}",
                "weight": 10,
                "encoding": "url",
            },
            "유튜브": {
                "url_template": "https://www.youtube.com/results?search_query={keyword}",
                "weight": 15,
                "encoding": "url",
            },
            "위키백과": {
                "url_template": "https://ko.wikipedia.org/wiki/{keyword}",
                "weight": 12,
                "encoding": "utf-8",
            },
            "인스타그램": {
                "url_template": "https://www.instagram.com/explore/tags/{keyword}",
                "weight": 5,
                "encoding": "url",
            },
            "X": {
                "url_template": "https://twitter.com/search?q={keyword}",
                "weight": 8,
                "encoding": "url",
            },
        }

        # 홈페이지 링크 옵션
        self.homepage_links = [
            {"url": "https://your-website.com", "text": "홈페이지"},
            {"url": "https://your-website.com/about", "text": "소개"},
            {"url": "https://your-website.com/services", "text": "서비스"},
            {"url": "https://your-website.com/contact", "text": "문의하기"},
        ]

    def encode_keyword(self, keyword: str, encoding_type: str) -> str:
        """키워드를 URL에 맞게 인코딩"""
        if encoding_type == "url":
            return urllib.parse.quote(keyword)
        elif encoding_type == "utf-8":
            # 한글 키워드 그대로 사용 (나무위키, 위키백과용)
            return keyword.replace(" ", "_")
        else:
            return keyword

    def select_random_platform(self) -> str:
        """가중치 기반으로 랜덤 플랫폼 선택"""
        platforms = list(self.platforms.keys())
        weights = [self.platforms[p]["weight"] for p in platforms]

        return random.choices(platforms, weights=weights)[0]

    def create_external_link(self, keyword: str, keyword_type: str) -> ExternalLink:
        """단일 외부링크 생성"""
        platform = self.select_random_platform()
        platform_info = self.platforms[platform]

        # 키워드 인코딩
        encoded_keyword = self.encode_keyword(keyword, platform_info["encoding"])

        # URL 생성
        url = platform_info["url_template"].format(keyword=encoded_keyword)

        return ExternalLink(
            anchor_text=keyword, url=url, platform=platform, keyword_type=keyword_type
        )

    def create_homepage_link(self) -> ExternalLink:
        """홈페이지 링크 생성"""
        home_link = random.choice(self.homepage_links)

        return ExternalLink(
            anchor_text=home_link["text"],
            url=home_link["url"],
            platform="홈페이지",
            keyword_type="homepage",
        )

    def extract_keywords_from_content(
        self, content: str, keywords_data: Dict[str, List[str]]
    ) -> Dict[str, List[str]]:
        """본문 콘텐츠에서 실제로 사용된 키워드만 추출

        Args:
            content: 마크다운 콘텐츠 (본문 부분만)
            keywords_data: 원본 키워드 데이터

        Returns:
            실제 본문에 존재하는 키워드들만 필터링된 딕셔너리
        """
        # H2 태그 이후의 본문만 추출
        lines = content.split("\n")
        main_content = []
        main_content_started = False

        for line in lines:
            if line.startswith("## ") and not main_content_started:
                main_content_started = True
                continue
            if main_content_started:
                main_content.append(line)

        # 실제 본문 텍스트
        main_text = "\n".join(main_content)

        # 실제 본문에 존재하는 키워드만 필터링
        used_keywords = {"lsi_keywords": [], "longtail_keywords": []}

        # LSI 키워드 확인
        for keyword in keywords_data.get("lsi_keywords", []):
            if keyword in main_text:
                used_keywords["lsi_keywords"].append(keyword)
                print(f"   ✅ LSI 키워드 발견: '{keyword}'")

        # 롱테일 키워드 확인
        for keyword in keywords_data.get("longtail_keywords", []):
            if keyword in main_text:
                used_keywords["longtail_keywords"].append(keyword)
                print(f"   ✅ 롱테일 키워드 발견: '{keyword}'")

        return used_keywords

    def generate_external_links(
        self,
        keywords_data: Dict[str, List[str]],
        target_keyword: str,
        content_count: int = 1,
        markdown_content: str = None,
    ) -> List[ExternalLink]:
        """외부링크 세트 생성

        Args:
            keywords_data: {"lsi_keywords": [...], "longtail_keywords": [...]}
            target_keyword: 핵심 키워드
            content_count: 현재 콘텐츠 수 (전략 결정용)
            markdown_content: 마크다운 콘텐츠 (실제 사용된 키워드 추출용)

        Returns:
            생성된 외부링크 리스트
        """
        # 0. 실제 본문에 사용된 키워드만 필터링 (markdown_content가 제공된 경우)
        if markdown_content:
            print("   🔍 본문에서 실제 사용된 키워드 검색 중...")
            used_keywords = self.extract_keywords_from_content(
                markdown_content, keywords_data
            )
            # 필터링된 키워드로 교체
            keywords_data = used_keywords

            total_used = len(used_keywords["lsi_keywords"]) + len(
                used_keywords["longtail_keywords"]
            )
            print(f"   📊 사용 가능한 키워드: {total_used}개")

        # 1. 링크 수 결정 (1-4개 랜덤, 단 사용 가능한 키워드 수 고려)
        available_keywords_count = len(keywords_data.get("lsi_keywords", [])) + len(
            keywords_data.get("longtail_keywords", [])
        )
        max_links = min(4, available_keywords_count + 1)  # +1은 핵심 키워드
        num_links = random.randint(1, max_links) if max_links > 0 else 1

        # 2. 키워드 풀 생성 (실제 사용된 키워드만)
        all_keywords = []

        # 핵심 키워드는 항상 추가 (본문에 있을 가능성이 높음)
        all_keywords.append((target_keyword, "핵심"))

        # LSI 키워드 추가 (실제 본문에 존재하는 것만)
        for kw in keywords_data.get("lsi_keywords", []):
            all_keywords.append((kw, "LSI"))

        # 롱테일 키워드 추가 (실제 본문에 존재하는 것만)
        for kw in keywords_data.get("longtail_keywords", []):
            all_keywords.append((kw, "롱테일"))

        # 3. 초기 콘텐츠 전략 (5개 미만)
        if content_count < 5:
            external_ratio = 0.7  # 70% 외부링크
            homepage_ratio = 0.3  # 30% 홈페이지
        elif content_count < 15:
            external_ratio = 0.5  # 50% 외부링크
            homepage_ratio = 0.5  # 50% 홈페이지
        else:
            # 15개 이상부터는 내부링크 시스템 사용
            external_ratio = 0.2
            homepage_ratio = 0.8

        # 4. 링크 생성
        links = []
        selected_keywords = random.sample(
            all_keywords, min(num_links, len(all_keywords))
        )

        for keyword, keyword_type in selected_keywords:
            if random.random() < external_ratio:
                # 외부링크 생성
                link = self.create_external_link(keyword, keyword_type)
                links.append(link)
            else:
                # 홈페이지 링크 생성
                link = self.create_homepage_link()
                links.append(link)

        return links

    def insert_links_into_markdown(
        self, markdown_content: str, links: List[ExternalLink]
    ) -> str:
        """마크다운 콘텐츠에 링크 삽입

        Args:
            markdown_content: 원본 마크다운 콘텐츠
            links: 삽입할 링크 리스트

        Returns:
            링크가 삽입된 마크다운 콘텐츠
        """
        # H2 태그 이후의 본문 콘텐츠에만 링크 삽입
        lines = markdown_content.split("\n")
        main_content_started = False

        for i, line in enumerate(lines):
            # 첫 번째 H2 태그부터 본문 시작으로 판단
            if line.startswith("## ") and not main_content_started:
                main_content_started = True
                continue

            # 본문 영역에서 링크 삽입
            if main_content_started and links:
                # 복사본을 만들어서 안전하게 순회
                links_copy = links.copy()
                for link in links_copy:
                    # 앵커텍스트가 현재 줄에 있는지 확인
                    if (
                        link.anchor_text in line and "[" not in line
                    ):  # 이미 링크가 아닌 경우만
                        # 마크다운 링크 형식으로 변환
                        markdown_link = f"[{link.anchor_text}]({link.url})"

                        # 첫 번째 발견된 키워드만 링크로 변환
                        lines[i] = line.replace(link.anchor_text, markdown_link, 1)

                        print(
                            f"   🔗 외부링크 추가: {link.anchor_text} → {link.platform}"
                        )

                        # 사용된 링크는 제거하여 중복 적용 방지
                        links.remove(link)
                        break

        return "\n".join(lines)

    def get_links_summary(self, links: List[ExternalLink]) -> Dict[str, int]:
        """생성된 링크들의 요약 정보"""
        summary = {
            "총_링크_수": len(links),
            "외부링크_수": len([l for l in links if l.platform != "홈페이지"]),
            "홈페이지_링크_수": len([l for l in links if l.platform == "홈페이지"]),
            "플랫폼별": {},
        }

        for link in links:
            platform = link.platform
            if platform not in summary["플랫폼별"]:
                summary["플랫폼별"][platform] = 0
            summary["플랫폼별"][platform] += 1

        return summary


# 편의 함수
def generate_external_links_for_content(
    target_keyword: str, keywords_data: Dict[str, List[str]], content_count: int = 1
) -> Tuple[List[ExternalLink], Dict[str, int]]:
    """콘텐츠용 외부링크 생성 (간편 함수)

    Returns:
        (생성된 링크 리스트, 요약 정보)
    """
    builder = ExternalLinkBuilder()
    links = builder.generate_external_links(
        keywords_data, target_keyword, content_count
    )
    summary = builder.get_links_summary(links)

    return links, summary


if __name__ == "__main__":
    # 테스트 코드
    test_keywords = {
        "lsi_keywords": ["PC 자동화 도구", "매크로 자동화", "생산성 향상"],
        "longtail_keywords": [
            "PC 자동화로 업무 시간 단축하는 방법",
            "초보자를 위한 PC 자동화 도구 가이드",
        ],
    }

    builder = ExternalLinkBuilder()
    links = builder.generate_external_links(
        test_keywords, "PC 자동화 장점", content_count=3
    )

    print("생성된 외부링크:")
    for link in links:
        print(f"- {link.anchor_text} → {link.url} ({link.platform})")

    summary = builder.get_links_summary(links)
    print(f"\n요약: {summary}")
