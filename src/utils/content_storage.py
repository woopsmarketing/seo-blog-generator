#!/usr/bin/env python3
"""
콘텐츠 벡터 저장소 관리 유틸리티
- FAISS 기반 벡터 저장소
- 워드프레스 포스트 메타데이터 관리
- 내부링크 생성을 위한 유사도 계산
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import hashlib

import faiss
import numpy as np
from langchain_openai import OpenAIEmbeddings
from langchain_community.docstore.in_memory import InMemoryDocstore
from langchain_community.vectorstores import FAISS
from langchain.schema import Document

# 로거 설정
logger = logging.getLogger(__name__)


class ContentStorage:
    """콘텐츠 벡터 저장소 관리 클래스"""

    def __init__(self, storage_dir: str = "data/content_storage"):
        """
        콘텐츠 저장소 초기화

        Args:
            storage_dir: 벡터 저장소 및 메타데이터 저장 디렉토리
        """
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        # FAISS 벡터 저장소 경로
        self.vector_store_path = self.storage_dir / "faiss_index"

        # 메타데이터 저장 경로
        self.metadata_file = self.storage_dir / "content_metadata.json"

        # 임베딩 모델 초기화
        self.embeddings = OpenAIEmbeddings(
            model="text-embedding-3-small",  # 비용 효율적인 임베딩 모델
            openai_api_key=os.getenv("OPENAI_API_KEY"),
        )

        # 벡터 저장소 로드 또는 초기화
        self.vector_store = self._load_or_create_vector_store()

        # 메타데이터 로드 또는 초기화
        self.metadata = self._load_or_create_metadata()

        logger.info(f"ContentStorage 초기화 완료: {self.storage_dir}")

    def _load_or_create_vector_store(self) -> FAISS:
        """FAISS 벡터 저장소 로드 또는 생성"""
        try:
            if self.vector_store_path.exists():
                # 기존 벡터 저장소 로드
                vector_store = FAISS.load_local(
                    str(self.vector_store_path),
                    self.embeddings,
                    allow_dangerous_deserialization=True,
                )
                logger.info(
                    f"기존 벡터 저장소 로드 완료: {len(vector_store.docstore._dict)} 문서"
                )
                return vector_store
            else:
                # 새 벡터 저장소 생성
                logger.info("새로운 벡터 저장소 생성")
                # 더미 문서로 초기화
                dummy_doc = Document(
                    page_content="초기화용 더미 문서",
                    metadata={"type": "dummy", "id": "init"},
                )
                vector_store = FAISS.from_documents([dummy_doc], self.embeddings)
                return vector_store
        except Exception as e:
            logger.error(f"벡터 저장소 로드/생성 실패: {e}")
            # 실패 시 더미 문서로 새로 생성
            dummy_doc = Document(
                page_content="초기화용 더미 문서",
                metadata={"type": "dummy", "id": "init"},
            )
            return FAISS.from_documents([dummy_doc], self.embeddings)

    def _load_or_create_metadata(self) -> Dict[str, Any]:
        """메타데이터 파일 로드 또는 생성"""
        try:
            if self.metadata_file.exists():
                with open(self.metadata_file, "r", encoding="utf-8") as f:
                    metadata = json.load(f)
                logger.info(
                    f"기존 메타데이터 로드 완료: {len(metadata.get('posts', {}))} 포스트"
                )
                return metadata
            else:
                # 새 메타데이터 구조 생성
                metadata = {
                    "created_at": datetime.now().isoformat(),
                    "last_updated": datetime.now().isoformat(),
                    "posts": {},  # post_id -> metadata
                    "keywords": {},  # keyword -> [post_ids]
                    "categories": {},  # category -> [post_ids]
                    "stats": {
                        "total_posts": 0,
                        "total_words": 0,
                        "last_post_date": None,
                    },
                }
                self._save_metadata(metadata)
                logger.info("새로운 메타데이터 구조 생성")
                return metadata
        except Exception as e:
            logger.error(f"메타데이터 로드 실패: {e}")
            return {
                "created_at": datetime.now().isoformat(),
                "last_updated": datetime.now().isoformat(),
                "posts": {},
                "keywords": {},
                "categories": {},
                "stats": {"total_posts": 0, "total_words": 0, "last_post_date": None},
            }

    def _save_metadata(self, metadata: Dict[str, Any] = None):
        """메타데이터를 파일에 저장"""
        if metadata is None:
            metadata = self.metadata

        metadata["last_updated"] = datetime.now().isoformat()

        try:
            with open(self.metadata_file, "w", encoding="utf-8") as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)
            logger.debug("메타데이터 저장 완료")
        except Exception as e:
            logger.error(f"메타데이터 저장 실패: {e}")

    def _save_vector_store(self):
        """벡터 저장소를 디스크에 저장"""
        try:
            self.vector_store.save_local(str(self.vector_store_path))
            logger.debug("벡터 저장소 저장 완료")
        except Exception as e:
            logger.error(f"벡터 저장소 저장 실패: {e}")

    def _generate_content_hash(self, content: str) -> str:
        """콘텐츠의 해시값 생성 (중복 체크용)"""
        return hashlib.md5(content.encode("utf-8")).hexdigest()

    def store_wordpress_post(
        self,
        post_data: Dict[str, Any],
        content: str,
        keyword: str,
        lsi_keywords: List[str] = None,
        longtail_keywords: List[str] = None,
        categories: List[str] = None,
    ) -> bool:
        """
        워드프레스 포스트를 벡터 저장소에 저장

        Args:
            post_data: 워드프레스 포스트 정보 (id, url, title, date 등)
            content: 포스트 본문 내용 (마크다운 또는 텍스트)
            keyword: 주요 키워드
            lsi_keywords: LSI 키워드 리스트
            longtail_keywords: 롱테일 키워드 리스트
            categories: 카테고리 리스트

        Returns:
            저장 성공 여부
        """
        try:
            post_id = str(post_data["id"])

            # 중복 체크
            content_hash = self._generate_content_hash(content)
            if post_id in self.metadata["posts"]:
                existing_hash = self.metadata["posts"][post_id].get("content_hash")
                if existing_hash == content_hash:
                    logger.info(f"동일한 콘텐츠가 이미 저장됨: {post_id}")
                    return True

            # 콘텐츠를 청크 단위로 분할 (긴 콘텐츠 처리)
            chunks = self._split_content(content, max_chunk_size=1000)

            # 각 청크를 벡터 저장소에 추가
            documents = []
            for i, chunk in enumerate(chunks):
                doc_metadata = {
                    "post_id": post_id,
                    "post_title": post_data.get("title", ""),
                    "post_url": post_data.get("url", ""),
                    "post_date": post_data.get("date", ""),
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                    "keyword": keyword,
                    "lsi_keywords": lsi_keywords or [],
                    "longtail_keywords": longtail_keywords or [],
                    "categories": categories or [],
                    "content_hash": content_hash,
                    "stored_at": datetime.now().isoformat(),
                }

                documents.append(Document(page_content=chunk, metadata=doc_metadata))

            # 벡터 저장소에 문서 추가
            if documents:
                self.vector_store.add_documents(documents)
                logger.info(f"벡터 저장소에 {len(documents)}개 청크 추가: {post_id}")

            # 메타데이터 업데이트
            self.metadata["posts"][post_id] = {
                "title": post_data.get("title", ""),
                "url": post_data.get("url", ""),
                "date": post_data.get("date", ""),
                "keyword": keyword,
                "lsi_keywords": lsi_keywords or [],
                "longtail_keywords": longtail_keywords or [],
                "categories": categories or [],
                "content_length": len(content),
                "chunk_count": len(chunks),
                "content_hash": content_hash,
                "stored_at": datetime.now().isoformat(),
            }

            # 키워드 인덱스 업데이트
            self._update_keyword_index(
                post_id, keyword, lsi_keywords, longtail_keywords
            )

            # 카테고리 인덱스 업데이트
            self._update_category_index(post_id, categories)

            # 통계 업데이트
            self._update_stats(content)

            # 저장
            self._save_metadata()
            self._save_vector_store()

            logger.info(
                f"✅ 포스트 저장 완료: {post_id} ({post_data.get('title', 'No Title')})"
            )
            return True

        except Exception as e:
            logger.error(f"포스트 저장 실패 ({post_data.get('id', 'Unknown')}): {e}")
            return False

    def _split_content(self, content: str, max_chunk_size: int = 1000) -> List[str]:
        """콘텐츠를 청크 단위로 분할"""
        # 문단 단위로 분할 시도
        paragraphs = content.split("\n\n")
        chunks = []
        current_chunk = ""

        for paragraph in paragraphs:
            # 현재 청크에 문단을 추가했을 때 크기 체크
            if len(current_chunk) + len(paragraph) + 2 <= max_chunk_size:
                if current_chunk:
                    current_chunk += "\n\n" + paragraph
                else:
                    current_chunk = paragraph
            else:
                # 현재 청크를 저장하고 새 청크 시작
                if current_chunk:
                    chunks.append(current_chunk.strip())

                # 문단이 너무 긴 경우 문장 단위로 분할
                if len(paragraph) > max_chunk_size:
                    sentences = paragraph.split(". ")
                    temp_chunk = ""
                    for sentence in sentences:
                        if len(temp_chunk) + len(sentence) + 2 <= max_chunk_size:
                            if temp_chunk:
                                temp_chunk += ". " + sentence
                            else:
                                temp_chunk = sentence
                        else:
                            if temp_chunk:
                                chunks.append(temp_chunk.strip())
                            temp_chunk = sentence
                    if temp_chunk:
                        current_chunk = temp_chunk
                else:
                    current_chunk = paragraph

        # 마지막 청크 추가
        if current_chunk:
            chunks.append(current_chunk.strip())

        return chunks

    def _update_keyword_index(
        self,
        post_id: str,
        keyword: str,
        lsi_keywords: List[str] = None,
        longtail_keywords: List[str] = None,
    ):
        """키워드 인덱스 업데이트"""
        all_keywords = [keyword]
        if lsi_keywords:
            all_keywords.extend(lsi_keywords)
        if longtail_keywords:
            all_keywords.extend(longtail_keywords)

        for kw in all_keywords:
            if kw not in self.metadata["keywords"]:
                self.metadata["keywords"][kw] = []
            if post_id not in self.metadata["keywords"][kw]:
                self.metadata["keywords"][kw].append(post_id)

    def _update_category_index(self, post_id: str, categories: List[str] = None):
        """카테고리 인덱스 업데이트"""
        if not categories:
            return

        for category in categories:
            if category not in self.metadata["categories"]:
                self.metadata["categories"][category] = []
            if post_id not in self.metadata["categories"][category]:
                self.metadata["categories"][category].append(post_id)

    def _update_stats(self, content: str):
        """통계 정보 업데이트"""
        self.metadata["stats"]["total_posts"] += 1
        self.metadata["stats"]["total_words"] += len(content.split())
        self.metadata["stats"]["last_post_date"] = datetime.now().isoformat()

    def find_similar_posts(
        self,
        query_text: str,
        k: int = 5,
        exclude_post_id: str = None,
        min_similarity_score: float = 0.7,
        search_titles_only: bool = False,  # 제목만 검색 옵션 추가
    ) -> List[Dict[str, Any]]:
        """
        유사한 포스트 검색

        Args:
            query_text: 검색할 텍스트
            k: 반환할 결과 수
            exclude_post_id: 제외할 포스트 ID
            min_similarity_score: 최소 유사도 점수

        Returns:
            유사한 포스트 리스트 (메타데이터 포함)
        """
        try:
            if not self.vector_store or len(self.metadata["posts"]) == 0:
                return []

            # 제목만 검색하는 경우
            if search_titles_only:
                similar_posts = []
                for post_id, post_data in self.metadata["posts"].items():
                    if exclude_post_id and post_id == exclude_post_id:
                        continue

                    title = post_data.get("title", "")
                    if not title:
                        continue

                    # 제목과 쿼리의 유사도 계산 (간단한 키워드 매칭)
                    query_words = set(query_text.lower().split())
                    title_words = set(title.lower().split())

                    # 자카드 유사도 계산
                    intersection = len(query_words & title_words)
                    union = len(query_words | title_words)
                    similarity = intersection / union if union > 0 else 0.0

                    if similarity >= min_similarity_score:
                        similar_posts.append(
                            {
                                "post_id": post_id,
                                "title": title,
                                "url": post_data.get("url", ""),
                                "keyword": post_data.get("keyword", ""),
                                "similarity_score": similarity,
                                "metadata": post_data,
                            }
                        )

                # 유사도 순으로 정렬
                similar_posts.sort(key=lambda x: x["similarity_score"], reverse=True)
                logger.info(f"제목 검색 결과: {len(similar_posts)}개 발견")
                return similar_posts[:k]

            # 벡터 검색 수행 (전체 콘텐츠)
            results = self.vector_store.similarity_search_with_score(
                query_text, k=k * 2
            )  # 여유분 확보

            # 결과 처리 및 필터링
            similar_posts = []
            seen_post_ids = set()

            for doc, score in results:
                post_id = doc.metadata.get("post_id")

                # 제외할 포스트 ID 체크
                if exclude_post_id and post_id == exclude_post_id:
                    continue

                # 더미 문서 제외
                if doc.metadata.get("type") == "dummy":
                    continue

                # 중복 포스트 제외 (같은 포스트의 다른 청크)
                if post_id in seen_post_ids:
                    continue

                # 유사도 점수 체크 (FAISS는 거리를 반환하므로 낮을수록 유사)
                similarity = 1 / (1 + score)  # 거리를 유사도로 변환
                if similarity < min_similarity_score:
                    continue

                seen_post_ids.add(post_id)

                # 메타데이터에서 포스트 정보 가져오기
                post_metadata = self.metadata["posts"].get(post_id, {})

                similar_posts.append(
                    {
                        "post_id": post_id,
                        "title": post_metadata.get(
                            "title", doc.metadata.get("post_title", "")
                        ),
                        "url": post_metadata.get(
                            "url", doc.metadata.get("post_url", "")
                        ),
                        "keyword": post_metadata.get("keyword", ""),
                        "similarity_score": similarity,
                        "content_preview": (
                            doc.page_content[:200] + "..."
                            if len(doc.page_content) > 200
                            else doc.page_content
                        ),
                    }
                )

                if len(similar_posts) >= k:
                    break

            # 유사도 순으로 정렬
            similar_posts.sort(key=lambda x: x["similarity_score"], reverse=True)

            logger.info(
                f"유사한 포스트 {len(similar_posts)}개 발견 (쿼리: '{query_text[:50]}...')"
            )
            return similar_posts[:k]

        except Exception as e:
            logger.error(f"유사한 포스트 검색 실패: {e}")
            return []

    def get_posts_by_keyword(self, keyword: str) -> List[Dict[str, Any]]:
        """특정 키워드로 포스트 검색"""
        post_ids = self.metadata["keywords"].get(keyword, [])
        return [
            self.metadata["posts"][pid]
            for pid in post_ids
            if pid in self.metadata["posts"]
        ]

    def get_posts_by_category(self, category: str) -> List[Dict[str, Any]]:
        """특정 카테고리로 포스트 검색"""
        post_ids = self.metadata["categories"].get(category, [])
        return [
            self.metadata["posts"][pid]
            for pid in post_ids
            if pid in self.metadata["posts"]
        ]

    def find_posts_by_keyword_similarity(
        self,
        target_keywords: List[str],
        exclude_post_id: str = None,
        min_keyword_match: int = 1,
    ) -> List[Dict[str, Any]]:
        """키워드 유사도 기반으로 포스트 검색 (메타데이터 기반)

        Args:
            target_keywords: 검색할 키워드 리스트
            exclude_post_id: 제외할 포스트 ID
            min_keyword_match: 최소 매칭 키워드 수

        Returns:
            매칭된 포스트 리스트 (매칭 점수 포함)
        """
        matched_posts = []

        # 모든 키워드를 소문자로 변환
        target_keywords_lower = [kw.lower().strip() for kw in target_keywords]

        for post_id, post_data in self.metadata["posts"].items():
            if exclude_post_id and post_id == exclude_post_id:
                continue

            # 해당 포스트의 모든 키워드 수집
            post_keywords = []
            post_keywords.append(post_data.get("keyword", "").lower())
            post_keywords.extend(
                [kw.lower() for kw in post_data.get("lsi_keywords", [])]
            )
            post_keywords.extend(
                [kw.lower() for kw in post_data.get("longtail_keywords", [])]
            )

            # 빈 키워드 제거
            post_keywords = [kw.strip() for kw in post_keywords if kw.strip()]

            # 키워드 매칭 계산
            matches = 0
            matched_keywords = []

            for target_kw in target_keywords_lower:
                for post_kw in post_keywords:
                    # 완전 일치 또는 부분 일치 확인
                    if target_kw in post_kw or post_kw in target_kw:
                        matches += 1
                        matched_keywords.append((target_kw, post_kw))
                        break  # 하나의 타겟 키워드당 하나의 매치만

            # 최소 매칭 조건 확인
            if matches >= min_keyword_match:
                # 매칭 점수 계산 (매칭된 키워드 수 / 전체 타겟 키워드 수)
                match_score = matches / len(target_keywords_lower)

                matched_posts.append(
                    {
                        "post_id": post_id,
                        "title": post_data.get("title", ""),
                        "url": post_data.get("url", ""),
                        "keyword": post_data.get("keyword", ""),
                        "match_score": match_score,
                        "matched_count": matches,
                        "matched_keywords": matched_keywords,
                        "metadata": post_data,
                    }
                )

        # 매칭 점수 순으로 정렬
        matched_posts.sort(key=lambda x: x["match_score"], reverse=True)

        logger.info(f"키워드 매칭 결과: {len(matched_posts)}개 포스트 발견")
        return matched_posts

    def get_storage_stats(self) -> Dict[str, Any]:
        """저장소 통계 정보 반환"""
        return {
            "total_posts": len(self.metadata["posts"]),
            "total_keywords": len(self.metadata["keywords"]),
            "total_categories": len(self.metadata["categories"]),
            "vector_store_size": (
                len(self.vector_store.docstore._dict)
                if hasattr(self.vector_store, "docstore")
                else 0
            ),
            "stats": self.metadata["stats"],
        }


# 편의를 위한 팩토리 함수
def create_content_storage(storage_dir: str = "data/content_storage") -> ContentStorage:
    """콘텐츠 저장소 인스턴스 생성"""
    return ContentStorage(storage_dir)


if __name__ == "__main__":
    # 테스트 코드
    storage = create_content_storage()
    stats = storage.get_storage_stats()
    print(f"📊 저장소 통계: {stats}")
