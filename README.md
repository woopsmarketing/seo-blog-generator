# SEO Blog Content Generator

한국어 SEO 최적화 블로그 콘텐츠 자동 생성 시스템

## 🚀 주요 기능

- **키워드 기반 콘텐츠 생성**: 입력된 키워드를 바탕으로 SEO 최적화된 블로그 포스트 자동 생성
- **섹션별 개별 LLM 호출**: 각 H2 섹션마다 독립적인 LLM 호출로 정교한 콘텐츠 제어
- **자연스러운 플로우**: 섹션 간 매끄러운 연결과 컨텍스트 유지
- **동적 길이 조절**: 목표 길이(4000-6000자)에 맞춘 자동 길이 분배
- **워드프레스 최적화**: 바로 업로드 가능한 HTML 형태로 출력
- **비용 분석**: 상세한 LLM 사용량 및 비용 분석 리포트

## 🛠️ 기술 스택

- **Python 3.8+**
- **OpenAI GPT Models** (gpt-4o-mini, gpt-5-nano-2025-08-07)
- **LangChain**: 메모리 관리 및 컨텍스트 유지
- **Task Master AI**: 프로젝트 관리 및 작업 추적

## 📁 프로젝트 구조

```
Seo_blog/
├── src/
│   ├── generators/
│   │   ├── content/           # 콘텐츠 생성 엔진
│   │   │   ├── title_generator.py      # 제목 생성
│   │   │   ├── outline_generator.py    # 아웃라인 생성
│   │   │   ├── section_generator.py    # 섹션별 콘텐츠 생성
│   │   │   └── memory/                 # 메모리 관리
│   │   └── html/              # HTML 변환 모듈
│   ├── models/                # 데이터 모델
│   └── utils/                 # 유틸리티 함수
├── data/                      # 생성된 콘텐츠 저장소
├── .taskmaster/              # Task Master 설정
├── .claude/                  # Claude Code 설정
└── requirements.txt          # 의존성 패키지
```

## 🚀 설치 및 설정

### 1. 프로젝트 클론
```bash
git clone <repository-url>
cd Seo_blog
```

### 2. 가상환경 생성 및 활성화
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 또는
venv\Scripts\activate     # Windows
```

### 3. 의존성 설치
```bash
pip install -r requirements.txt
```

### 4. 환경 변수 설정
```bash
cp config.example.py config.py
```

`.env` 파일 생성하고 API 키 설정:
```
OPENAI_API_KEY=your_openai_api_key_here
DEFAULT_LLM_PROVIDER=openai
OPENAI_MODEL=gpt-4o-mini
```

## 💻 사용법

### 기본 사용법
```python
python test_americano_pipeline.py
```

### 커스텀 키워드로 실행
```python
from src.generators.content.title_generator import TitleGenerator
from src.generators.content.outline_generator import OutlineGenerator
from src.generators.content.section_generator import SectionGenerator

# 키워드 설정
keyword = "your_keyword_here"

# 파이프라인 실행
title_generator = TitleGenerator()
outline_generator = OutlineGenerator()
section_generator = SectionGenerator()
```

## 📊 생성되는 파일들

1. **Markdown 파일** (`.md`): 원본 블로그 콘텐츠
2. **HTML 파일** (`.html`): 워드프레스 업로드용 HTML
3. **JSON 리포트** (`.json`): 상세 비용 분석 및 성능 지표

## 🎯 주요 개선사항

### v2.0 - GPT-5 nano 대응 및 섹션별 호출
- **개별 섹션 생성**: 각 H2 섹션마다 독립적인 LLM 호출
- **콘텐츠 플로우**: 섹션 간 자연스러운 연결 시스템
- **동적 길이 제어**: 전체 문서 길이 목표에 맞춘 섹션별 길이 조절
- **정교한 프롬프트**: 섹션 특성에 맞춘 맞춤형 프롬프트
- **GPT-5 nano 지원**: 최신 경제적 모델 지원

### 성능 지표
- **목표 길이 달성률**: 95% 이상 (4000-6000자)
- **섹션별 평균 생성 시간**: 25-30초
- **예상 비용**: $0.003-0.005 per 블로그 포스트

## 🔧 설정 옵션

### `src/utils/config.py`에서 설정 가능한 옵션들:
- LLM 모델 선택 (gpt-4o-mini, gpt-5-nano-2025-08-07)
- 온도(Temperature) 조절
- 최대 토큰 수
- 콘텐츠 길이 설정

## 🧪 테스트

```bash
# 전체 파이프라인 테스트
python test_americano_pipeline.py

# 특정 모델 테스트
python test_gpt5_nano.py

# 커피 키워드 테스트
python test_coffee_gpt5_nano.py
```

## 📈 예시 결과

**생성된 블로그 예시**: "아메리카노 완벽 가이드"
- **총 길이**: 4,621자 ✅
- **섹션 수**: 6개 (개요, 시작하기, 핵심방법, 실무노하우, 마무리, FAQ)
- **생성 시간**: 167.8초
- **예상 비용**: $0.003153

## 🤝 기여

이 프로젝트는 지속적으로 개선되고 있습니다. 기여를 원하시면:

1. Fork the project
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Open a Pull Request

## 📄 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다.

## 🔗 관련 링크

- [OpenAI API Documentation](https://platform.openai.com/docs)
- [LangChain Documentation](https://python.langchain.com/)
- [Task Master AI](https://github.com/task-master-ai)

---

**개발자**: Claude Code Enhanced Pipeline  
**최신 업데이트**: 2025-08-27  
**버전**: 2.0 - GPT-5 nano Integration