#!/usr/bin/env python3
"""
내부링크 자동 생성 유틸리티
- FAISS 벡터 저장소 기반 유사도 검색
- 콘텐츠 간 자동 내부링크 생성
- 앵커 텍스트 최적화
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import re
import random

from .content_storage import ContentStorage

# 로거 설정
logger = logging.getLogger(__name__)


@dataclass
class InternalLink:
    """내부링크 데이터 클래스"""

    anchor_text: str
    target_url: str
    target_title: str
    target_post_id: str
    similarity_score: float
    keyword_type: str  # 'keyword', 'lsi', 'longtail'


class InternalLinkBuilder:
    """내부링크 자동 생성 클래스"""

    def __init__(self, content_storage: ContentStorage):
        """
        내부링크 빌더 초기화

        Args:
            content_storage: 콘텐츠 저장소 인스턴스
        """
        self.content_storage = content_storage
        logger.info("InternalLinkBuilder 초기화 완료")

    def generate_internal_links(
        self,
        current_post_id: str,
        keywords_data: Dict[str, List[str]],
        target_keyword: str,
        markdown_content: str,
        max_links: int = 3,
        min_similarity_score: float = 0.4,  # 유사도 임계값 완화 (0.75 → 0.4)
    ) -> List[InternalLink]:
        """
        현재 포스트에 대한 내부링크 생성

        Args:
            current_post_id: 현재 포스트 ID
            keywords_data: 키워드 데이터 (lsi_keywords, longtail_keywords)
            target_keyword: 주요 키워드
            markdown_content: 마크다운 콘텐츠
            max_links: 최대 링크 수
            min_similarity_score: 최소 유사도 점수

        Returns:
            생성된 내부링크 리스트
        """
        try:
            # 본문에서 실제 사용된 키워드만 추출
            used_keywords = self._extract_keywords_from_content(
                markdown_content, keywords_data
            )

            if (
                not used_keywords["lsi_keywords"]
                and not used_keywords["longtail_keywords"]
            ):
                logger.warning(
                    "본문에서 사용된 키워드가 없어 내부링크를 생성할 수 없음"
                )
                return []

            # 각 키워드에 대해 유사한 포스트 검색
            internal_links = []
            all_keywords = (
                [(kw, "lsi") for kw in used_keywords["lsi_keywords"]]
                + [(kw, "longtail") for kw in used_keywords["longtail_keywords"]]
                + [(target_keyword, "keyword")]
            )

            # 메타데이터 기반 키워드 매칭으로 관련 포스트 검색 (임베딩 불필요)
            keyword_list = [kw for kw, _ in all_keywords]
            matched_posts = self.content_storage.find_posts_by_keyword_similarity(
                target_keywords=keyword_list,
                exclude_post_id=current_post_id,
                min_keyword_match=1,  # 최소 1개 키워드 매치
            )

            # 이미 사용된 키워드 추적 (중복 방지)
            used_anchor_texts = set()

            # 매칭된 포스트들로 내부링크 생성
            for post in matched_posts:
                if len(internal_links) >= max_links:
                    break

                # 이미 같은 포스트에 대한 링크가 있는지 체크
                if any(
                    link.target_post_id == post["post_id"] for link in internal_links
                ):
                    continue

                # 매칭된 키워드들 중에서 첫 번째 사용
                if post.get("matched_keywords"):
                    target_kw, matched_kw = post["matched_keywords"][0]

                    # 이미 같은 키워드로 링크가 생성되었는지 체크 (중복 방지)
                    if target_kw in used_anchor_texts:
                        continue

                    # 키워드 타입 찾기
                    keyword_type = "keyword"
                    for kw, kw_type in all_keywords:
                        if kw == target_kw:
                            keyword_type = kw_type
                            break

                    internal_link = InternalLink(
                        anchor_text=target_kw,
                        target_url=post["url"],
                        target_title=post["title"],
                        target_post_id=post["post_id"],
                        similarity_score=post["match_score"],
                        keyword_type=keyword_type,
                    )

                    internal_links.append(internal_link)
                    used_anchor_texts.add(target_kw)  # 사용된 키워드 기록

            # 유사도 점수 순으로 정렬
            internal_links.sort(key=lambda x: x.similarity_score, reverse=True)

            logger.info(
                f"내부링크 {len(internal_links)}개 생성 (포스트 ID: {current_post_id})"
            )
            return internal_links[:max_links]

        except Exception as e:
            logger.error(f"내부링크 생성 실패 (포스트 ID: {current_post_id}): {e}")
            return []

    def _extract_keywords_from_content(
        self, content: str, keywords_data: Dict[str, List[str]]
    ) -> Dict[str, List[str]]:
        """본문 콘텐츠에서 실제로 사용된 키워드만 추출"""
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

        # 롱테일 키워드 확인
        for keyword in keywords_data.get("longtail_keywords", []):
            if keyword in main_text:
                used_keywords["longtail_keywords"].append(keyword)

        return used_keywords

    def insert_internal_links_into_markdown(
        self, markdown_content: str, internal_links: List[InternalLink]
    ) -> str:
        """마크다운 콘텐츠에 내부링크 삽입"""
        if not internal_links:
            return markdown_content

        try:
            content_lines = markdown_content.split("\n")
            modified_content_lines = []
            links_to_apply = internal_links.copy()

            # 첫 번째 H2 태그 이후부터 링크 삽입
            h2_found = False

            for line in content_lines:
                # 첫 번째 H2 태그 확인
                if line.startswith("## ") and not h2_found:
                    h2_found = True
                    modified_content_lines.append(line)
                    continue

                # H2 태그 이후에만 링크 삽입
                if h2_found and links_to_apply:
                    modified_line = line

                    # 사용 가능한 링크들을 순회하면서 첫 번째 매칭되는 것 사용
                    for link in links_to_apply[:]:  # 복사본을 순회
                        # 앵커 텍스트가 라인에 있고, 아직 링크로 변환되지 않은 경우
                        if (
                            link.anchor_text in modified_line
                            and f"[{link.anchor_text}]" not in modified_line
                            and not modified_line.startswith("#")
                        ):  # 헤딩은 제외

                            # 첫 번째 발견된 키워드만 링크로 변환
                            modified_line = modified_line.replace(
                                link.anchor_text,
                                f"[{link.anchor_text}]({link.target_url})",
                                1,  # 첫 번째 발견된 것만 교체
                            )

                            # 사용된 링크는 제거하여 중복 사용 방지
                            links_to_apply.remove(link)
                            logger.info(
                                f"내부링크 적용: {link.anchor_text} → {link.target_title}"
                            )
                            break  # 한 라인에는 하나의 링크만

                    modified_content_lines.append(modified_line)
                else:
                    modified_content_lines.append(line)

            return "\n".join(modified_content_lines)

        except Exception as e:
            logger.error(f"내부링크 삽입 실패: {e}")
            return markdown_content

    def get_internal_links_summary(
        self, internal_links: List[InternalLink]
    ) -> Dict[str, Any]:
        """내부링크 요약 정보 반환"""
        if not internal_links:
            return {
                "총_링크_수": 0,
                "키워드_링크_수": 0,
                "LSI_링크_수": 0,
                "롱테일_링크_수": 0,
                "평균_유사도": 0.0,
            }

        keyword_count = len([l for l in internal_links if l.keyword_type == "keyword"])
        lsi_count = len([l for l in internal_links if l.keyword_type == "lsi"])
        longtail_count = len(
            [l for l in internal_links if l.keyword_type == "longtail"]
        )
        avg_similarity = sum(l.similarity_score for l in internal_links) / len(
            internal_links
        )

        return {
            "총_링크_수": len(internal_links),
            "키워드_링크_수": keyword_count,
            "LSI_링크_수": lsi_count,
            "롱테일_링크_수": longtail_count,
            "평균_유사도": round(avg_similarity, 3),
        }

    def suggest_link_opportunities(
        self,
        current_post_id: str,
        keywords_data: Dict[str, List[str]],
        target_keyword: str,
    ) -> List[Dict[str, Any]]:
        """
        링크 기회 제안 (분석용)

        Returns:
            링크 기회 리스트 (키워드, 유사 포스트, 유사도 점수 포함)
        """
        try:
            opportunities = []
            all_keywords = (
                keywords_data.get("lsi_keywords", [])
                + keywords_data.get("longtail_keywords", [])
                + [target_keyword]
            )

            # 메타데이터 기반 키워드 매칭으로 관련 포스트 검색 (임베딩 불필요)
            matched_posts = self.content_storage.find_posts_by_keyword_similarity(
                target_keywords=all_keywords,
                exclude_post_id=current_post_id,
                min_keyword_match=1,  # 최소 1개 키워드 매치
            )

            # 매칭된 포스트들을 기회로 변환
            for post in matched_posts:
                # 매칭된 키워드들 중에서 첫 번째 사용
                if post.get("matched_keywords"):
                    target_kw, matched_kw = post["matched_keywords"][0]
                    opportunities.append(
                        {
                            "keyword": target_kw,
                            "similar_posts_count": 1,
                            "best_match": {
                                "title": post["title"],
                                "similarity": post["match_score"],
                            },
                            "all_matches": [post],
                            "match_score": post["match_score"],
                            "matched_keyword": matched_kw,
                        }
                    )

            # 매칭 점수가 높은 순으로 정렬
            opportunities.sort(
                key=lambda x: x.get("match_score", 0),
                reverse=True,
            )

            return opportunities

        except Exception as e:
            logger.error(f"링크 기회 분석 실패: {e}")
            return []


# 편의를 위한 팩토리 함수
def create_internal_link_builder(
    content_storage: ContentStorage,
) -> InternalLinkBuilder:
    """내부링크 빌더 인스턴스 생성"""
    return InternalLinkBuilder(content_storage)


if __name__ == "__main__":
    # 테스트 코드
    from .content_storage import create_content_storage

    storage = create_content_storage()
    builder = create_internal_link_builder(storage)

    print("📊 내부링크 빌더 테스트 완료")
