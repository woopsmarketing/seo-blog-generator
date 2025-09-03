#!/usr/bin/env python3
"""
다중 워드프레스 계정 관리자
- 콘텐츠 카테고리에 따른 계정 자동 선택
- 계정별 전문성 기반 매칭 시스템
- 로드 밸런싱 및 계정 상태 관리
"""

import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
import re
from src.utils.wordpress_poster import WordPressPoster

# 로거 설정
logger = logging.getLogger(__name__)


class AccountType(Enum):
    """계정 유형 분류"""
    DATA_ANALYST = "data_analyst"          # 데이터 분석 전문가
    MARKETING_MASTER = "marketing_master"  # 마케팅 & 자동화 전문가  
    SEO_SPECIALIST = "seo_specialist"      # SEO & 링크 빌딩 전문가
    DEFAULT = "default"                    # 기본 계정


@dataclass
class WordPressAccount:
    """워드프레스 계정 정보"""
    account_id: str
    nickname: str
    username: str
    password: str
    app_password: str
    domain: str
    account_type: AccountType
    expertise_categories: List[str]
    description: str
    is_active: bool = True
    post_count: int = 0  # 업로드된 포스트 수 (로드 밸런싱용)
    
    def __post_init__(self):
        """초기화 후 처리"""
        # 앱 패스워드에서 공백 제거
        self.app_password = self.app_password.replace(" ", "")


class MultiWordPressManager:
    """다중 워드프레스 계정 관리자"""
    
    def __init__(self, domain: str = "https://followsales.com"):
        """
        다중 워드프레스 매니저 초기화
        
        Args:
            domain: 공통 워드프레스 도메인
        """
        self.domain = domain
        self.accounts: Dict[str, WordPressAccount] = {}
        self.posters: Dict[str, WordPressPoster] = {}
        
        # 계정 정보 초기화
        self._initialize_accounts()
        
        # 카테고리 매칭 가중치 설정
        self._setup_category_weights()
        
        logger.info(f"다중 워드프레스 매니저 초기화 완료: {len(self.accounts)}개 계정")
    
    def _initialize_accounts(self):
        """계정 정보 초기화"""
        accounts_data = [
            {
                "account_id": "datahunter",
                "nickname": "데이터헌터 (DataHunter)",
                "username": "datahunter",
                "password": "datahunter123!@#",
                "app_password": "vYkA TN1J BzGC vWea jSK3 d44H",
                "account_type": AccountType.DATA_ANALYST,
                "expertise_categories": ["분석도구", "구글", "PYTHON"],
                "description": "데이터 기반으로 SEO와 마케팅을 분석하는 전문가. 수치, 툴 활용, 성과 측정 중심."
            },
            {
                "account_id": "marketingmaster", 
                "nickname": "마케팅마스터 (MarketingMaster)",
                "username": "marketingmaster",
                "password": "marketingmaster123!@#", 
                "app_password": "ucjc yEPL EZaN wgaa PgUh UGwY",
                "account_type": AccountType.MARKETING_MASTER,
                "expertise_categories": ["마케팅", "블로그", "자동화", "구글"],
                "description": "디지털 마케팅 전략가. 구글 광고, 자동화 툴, 블로그 운영을 통한 확장 전략."
            },
            {
                "account_id": "linkmaker",
                "nickname": "링크메이커 (LinkMaker)", 
                "username": "linkmaker",
                "password": "linkmaker123!@#",
                "app_password": "m2qA LJnU ixbZ atGN 1Bmz GLnp",
                "account_type": AccountType.SEO_SPECIALIST,
                "expertise_categories": ["SEO", "백링크", "블로그"],
                "description": "SEO 최적화와 백링크 구축 전문가. 구글 상위노출과 링크 전략에 집중."
            },
            # 기본 계정 (기존)
            {
                "account_id": "followsales",
                "nickname": "팔로우세일즈 (기본)",
                "username": "followsales", 
                "password": "",  # 기본 계정은 비밀번호 별도 관리
                "app_password": "otFv tHVG aAQc gYvi 518v Ah4o",
                "account_type": AccountType.DEFAULT,
                "expertise_categories": ["IT", "AI", "내부최적화"],
                "description": "기본 계정. 일반적인 IT 및 AI 관련 콘텐츠 담당."
            }
        ]
        
        # 계정 객체 생성
        for account_data in accounts_data:
            account = WordPressAccount(
                domain=self.domain,
                **account_data
            )
            self.accounts[account.account_id] = account
            
            # WordPressPoster 객체 생성
            try:
                poster = WordPressPoster(
                    domain=self.domain,
                    username=account.username,
                    application_password=account.app_password
                )
                self.posters[account.account_id] = poster
                logger.info(f"✅ 계정 설정 완료: {account.nickname}")
            except Exception as e:
                logger.error(f"❌ 계정 설정 실패 ({account.nickname}): {e}")
                account.is_active = False
    
    def _setup_category_weights(self):
        """카테고리별 계정 매칭 가중치 설정"""
        # 카테고리별 키워드 매핑 (더 상세화)
        self.category_keywords = {
            "분석도구": [
                "분석", "analytics", "구글애널리틱스", "ga4", "데이터", "통계", "지표", 
                "측정", "추적", "모니터링", "리포트", "대시보드", "시각화", "차트",
                "성과분석", "데이터분석", "웹분석", "트래픽분석", "전환분석"
            ],
            "PYTHON": [
                "python", "파이썬", "django", "flask", "pandas", "numpy", "matplotlib",
                "jupyter", "anaconda", "pip", "라이브러리", "프레임워크", "스크립트",
                "코딩", "프로그래밍", "개발", "자동화스크립트", "데이터처리"
            ],
            "마케팅": [
                "마케팅", "marketing", "디지털마케팅", "온라인마케팅", "광고", "홍보",
                "브랜딩", "고객", "타겟", "전환", "roi", "ctr", "cpc", "캠페인",
                "구글광고", "페이스북광고", "인스타그램", "소셜미디어", "콘텐츠마케팅"
            ],
            "블로그": [
                "블로그", "포스팅", "콘텐츠", "글쓰기", "워드프레스", "티스토리",
                "네이버블로그", "블로거", "포스트", "아티클", "글", "작성", "발행",
                "게시", "콘텐츠마케팅", "블로그운영", "콘텐츠제작"
            ],
            "자동화": [
                "자동화", "automation", "봇", "스크립트", "매크로", "크롤링", "스크래핑",
                "rpa", "워크플로우", "프로세스", "효율화", "자동", "배치", "스케줄링",
                "업무자동화", "마케팅자동화"
            ],
            "SEO": [
                "seo", "검색엔진최적화", "검색엔진", "검색", "순위", "키워드", "메타태그",
                "최적화", "랭킹", "트래픽", "serp", "온페이지", "오프페이지",
                "검색결과", "구글seo", "네이버seo", "검색순위", "상위노출"
            ],
            "백링크": [
                "백링크", "backlink", "링크빌딩", "외부링크", "도메인권한", "da", "pa",
                "링크", "참조", "인용", "연결", "링크프로필", "앵커텍스트",
                "링크구축", "링크전략", "링크획득"
            ],
            "구글": [
                "구글", "google", "서치콘솔", "애드워즈", "애드센스", "구글봇",
                "구글알고리즘", "페이지스피드", "구글마이비즈니스", "구글광고",
                "구글검색", "구글상위노출"
            ],
            "IT": [
                "it", "정보기술", "소프트웨어", "하드웨어", "시스템", "네트워크",
                "데이터베이스", "서버", "클라우드", "보안", "기술", "프로그래밍",
                "개발", "코딩"
            ],
            "AI": [
                "ai", "인공지능", "머신러닝", "딥러닝", "neural", "gpt", "chatgpt",
                "llm", "자연어처리", "컴퓨터비전", "알고리즘", "모델", "학습",
                "예측", "분류", "인공지능기술"
            ],
            "내부최적화": [
                "내부최적화", "온페이지", "메타태그", "title", "description", "h1", "h2",
                "내부링크", "사이트구조", "url구조", "속도최적화", "모바일최적화",
                "사이트속도", "페이지최적화"
            ]
        }
        
        # 계정별 카테고리 점수 가중치
        self.account_category_weights = {
            "datahunter": {
                "분석도구": 1.0,
                "구글": 0.8, 
                "PYTHON": 0.9,
                "데이터": 1.0,  # 추가 키워드
                "통계": 0.9,
                "측정": 0.8
            },
            "marketingmaster": {
                "마케팅": 1.0,
                "블로그": 0.8,
                "자동화": 0.9,
                "구글": 0.7,
                "광고": 0.9,  # 추가 키워드
                "캠페인": 0.8
            },
            "linkmaker": {
                "SEO": 1.0,
                "백링크": 1.0,
                "블로그": 0.7,
                "최적화": 0.9,  # 추가 키워드
                "검색": 0.8,
                "순위": 0.8
            },
            "followsales": {  # 기본 계정
                "IT": 0.8,
                "AI": 0.8,
                "내부최적화": 0.7,
                "기술": 0.7,  # 추가 키워드
                "개발": 0.6
            }
        }
    
    def analyze_content_categories(
        self, 
        title: str, 
        content: str, 
        keywords: List[str] = None
    ) -> Dict[str, float]:
        """
        콘텐츠 분석을 통한 카테고리 점수 계산
        
        Args:
            title: 글 제목
            content: 글 본문
            keywords: 키워드 리스트
            
        Returns:
            카테고리별 점수 딕셔너리
        """
        # 텍스트 전처리
        clean_content = re.sub(r"<[^>]+>", " ", content).lower()
        clean_title = re.sub(r"<[^>]+>", " ", title).lower()
        
        # 전체 분석 텍스트 구성
        full_text = f"{clean_title} {clean_content}"
        if keywords:
            full_text += " " + " ".join([kw.lower() for kw in keywords])
        
        # 카테고리별 점수 계산
        category_scores = {}
        
        for category, category_keywords in self.category_keywords.items():
            score = 0.0
            
            for keyword in category_keywords:
                # 키워드 출현 빈도 계산
                content_count = full_text.count(keyword.lower())
                title_count = clean_title.count(keyword.lower())
                
                if content_count > 0:
                    # 제목에서 발견되면 가중치 3배, 본문은 1배
                    score += content_count + (title_count * 2)
            
            category_scores[category] = score
        
        # 정규화 (총합으로 나누어 비율로 변환)
        total_score = sum(category_scores.values())
        if total_score > 0:
            category_scores = {k: v/total_score for k, v in category_scores.items()}
        
        return category_scores
    
    def select_best_account(
        self, 
        title: str, 
        content: str, 
        keywords: List[str] = None
    ) -> Tuple[str, WordPressAccount, float]:
        """
        콘텐츠에 가장 적합한 계정 선택
        
        Args:
            title: 글 제목  
            content: 글 본문
            keywords: 키워드 리스트
            
        Returns:
            (계정_ID, 계정_객체, 매칭_점수)
        """
        # 1. 콘텐츠 카테고리 분석
        category_scores = self.analyze_content_categories(title, content, keywords)
        
        # 2. 각 계정별 적합성 점수 계산
        account_scores = {}
        
        for account_id, account in self.accounts.items():
            if not account.is_active:
                continue
                
            account_score = 0.0
            
            # 계정의 전문 카테고리에 대한 가중합 계산
            for category in account.expertise_categories:
                if category in category_scores:
                    # 카테고리 점수 × 계정별 가중치
                    weight = self.account_category_weights.get(account_id, {}).get(category, 0.5)
                    account_score += category_scores[category] * weight
            
            # 로드 밸런싱 요소 추가 (포스트 수가 적을수록 약간의 보너스)
            if len([acc for acc in self.accounts.values() if acc.is_active]) > 1:
                max_posts = max([acc.post_count for acc in self.accounts.values() if acc.is_active])
                if max_posts > 0:
                    load_bonus = (max_posts - account.post_count) / max_posts * 0.1
                    account_score += load_bonus
            
            account_scores[account_id] = account_score
        
        # 3. 최고 점수 계정 선택
        if not account_scores:
            # 활성화된 계정이 없으면 기본 계정 반환
            default_account = self.accounts.get("followsales")
            return "followsales", default_account, 0.0
            
        best_account_id = max(account_scores, key=account_scores.get)
        best_score = account_scores[best_account_id]
        best_account = self.accounts[best_account_id]
        
        # 로깅
        logger.info(f"🎯 계정 선택 결과:")
        logger.info(f"   선택된 계정: {best_account.nickname} (점수: {best_score:.3f})")
        logger.info(f"   카테고리 점수: {dict(sorted(category_scores.items(), key=lambda x: x[1], reverse=True)[:3])}")
        logger.info(f"   모든 계정 점수: {dict(sorted(account_scores.items(), key=lambda x: x[1], reverse=True))}")
        
        return best_account_id, best_account, best_score
    
    def get_poster(self, account_id: str) -> Optional[WordPressPoster]:
        """계정 ID로 WordPressPoster 객체 반환"""
        return self.posters.get(account_id)
    
    def increment_post_count(self, account_id: str):
        """계정의 포스트 수 증가 (로드 밸런싱용)"""
        if account_id in self.accounts:
            self.accounts[account_id].post_count += 1
    
    def get_account_stats(self) -> Dict[str, Any]:
        """계정별 통계 정보 반환"""
        stats = {}
        for account_id, account in self.accounts.items():
            stats[account_id] = {
                "nickname": account.nickname,
                "account_type": account.account_type.value,
                "expertise_categories": account.expertise_categories,
                "is_active": account.is_active,
                "post_count": account.post_count,
                "description": account.description
            }
        return stats
    
    def test_all_connections(self) -> Dict[str, bool]:
        """모든 계정의 워드프레스 연결 테스트"""
        results = {}
        
        for account_id, poster in self.posters.items():
            account = self.accounts[account_id]
            try:
                result = poster.test_connection()
                results[account_id] = result
                
                if result:
                    logger.info(f"✅ 연결 성공: {account.nickname}")
                else:
                    logger.error(f"❌ 연결 실패: {account.nickname}")
                    account.is_active = False
                    
            except Exception as e:
                logger.error(f"❌ 연결 오류 ({account.nickname}): {e}")
                results[account_id] = False
                account.is_active = False
                
        return results


# 편의를 위한 팩토리 함수
def create_multi_wordpress_manager(domain: str = "https://followsales.com") -> MultiWordPressManager:
    """다중 워드프레스 매니저 생성"""
    return MultiWordPressManager(domain=domain)


if __name__ == "__main__":
    # 테스트 코드
    manager = create_multi_wordpress_manager()
    
    # 연결 테스트
    print("🔗 모든 계정 연결 테스트 중...")
    results = manager.test_all_connections()
    
    print(f"\n📊 연결 결과:")
    for account_id, success in results.items():
        account = manager.accounts[account_id]
        status = "✅ 성공" if success else "❌ 실패"
        print(f"  {account.nickname}: {status}")
    
    # 샘플 콘텐츠로 계정 선택 테스트
    print(f"\n🧪 계정 선택 테스트:")
    test_cases = [
        {
            "title": "구글 애널리틱스 GA4로 트래픽 분석하는 방법",
            "content": "구글 애널리틱스를 사용하여 웹사이트 트래픽을 분석하고 데이터를 시각화하는 방법을 알아봅니다.",
            "keywords": ["분석", "데이터", "구글애널리틱스"]
        },
        {
            "title": "SEO 백링크 구축 전략 완벽 가이드", 
            "content": "검색엔진 최적화를 위한 백링크 구축 방법과 링크빌딩 전략을 소개합니다.",
            "keywords": ["SEO", "백링크", "링크빌딩"]
        },
        {
            "title": "디지털 마케팅 자동화로 효율성 극대화하기",
            "content": "마케팅 캠페인 자동화 도구를 활용하여 광고 성과를 높이는 전략입니다.",
            "keywords": ["마케팅", "자동화", "캠페인"]
        }
    ]
    
    for i, test in enumerate(test_cases, 1):
        print(f"\n--- 테스트 케이스 {i}: {test['title'][:30]}... ---")
        account_id, account, score = manager.select_best_account(
            test["title"], test["content"], test["keywords"]
        )
        print(f"결과: {account.nickname} (점수: {score:.3f})")