# config.example.py
# 환경 변수 설정 예제 파일
# 이 파일을 참고하여 .env 파일을 생성하거나 환경 변수를 설정하세요

"""
환경 변수 설정 가이드:

1. .env 파일 생성:
   - 프로젝트 루트에 .env 파일을 만드세요
   - 아래 변수들을 복사하여 실제 값으로 바꾸세요

2. 필수 설정:
   - OPENAI_API_KEY 또는 ANTHROPIC_API_KEY 중 하나는 반드시 설정
   - DEFAULT_LLM_PROVIDER로 사용할 프로바이더 지정

3. .env 파일 예시:
"""

ENV_TEMPLATE = """
# LLM API 키 설정 (필수)
OPENAI_API_KEY=your_openai_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# 기본 LLM 프로바이더 (openai 또는 anthropic)
DEFAULT_LLM_PROVIDER=openai

# 모델 설정 (GPT-5 시리즈)
OPENAI_MODEL=gpt-5-nano
ANTHROPIC_MODEL=claude-3-sonnet-20240229
LLM_TEMPERATURE=0.7
LLM_MAX_TOKENS=2000

# WordPress 설정 (선택사항)
WP_URL=https://yourblog.com
WP_USERNAME=your_wp_username
WP_PASSWORD=your_wp_app_password

# 로깅 설정
LOG_LEVEL=INFO
LOG_FILE=blog_generation.log

# 콘텐츠 설정
MIN_SECTION_LENGTH=300
MAX_SECTION_LENGTH=500
TARGET_TOTAL_LENGTH=3000
"""

# GPT-5 시리즈 모델 정보
GPT5_MODELS = {
    "gpt-5-nano": {
        "description": "가장 빠르고 경제적인 GPT-5 모델",
        "context_window": 400000,
        "input_cost": "$0.05/1M tokens",
        "output_cost": "$0.40/1M tokens",
        "best_for": ["일상적인 질문", "빠른 응답", "비용 최적화"],
        "temperature_support": False,  # GPT-5 시리즈는 temperature 고정
        "special_features": ["fastest_response", "ultra_low_latency", "cost_effective"],
    },
    "gpt-5-mini": {
        "description": "균형잡힌 성능과 비용의 GPT-5 모델",
        "context_window": 400000,
        "input_cost": "$0.25/1M tokens",
        "output_cost": "$2.00/1M tokens",
        "best_for": ["정의된 작업", "균형잡힌 품질", "일반적인 용도"],
        "temperature_support": False,
        "special_features": ["balanced_performance", "cost_effective", "defined_tasks"],
    },
    "gpt-5": {
        "description": "최고 성능의 플래그십 GPT-5 모델",
        "context_window": 400000,
        "input_cost": "$1.25/1M tokens",
        "output_cost": "$10.00/1M tokens",
        "best_for": ["복잡한 추론", "코딩", "고품질 콘텐츠"],
        "temperature_support": False,
        "special_features": [
            "best_performance",
            "complex_reasoning",
            "coding_excellence",
        ],
    },
}


def print_config_guide():
    """설정 가이드 출력"""
    print("=" * 60)
    print("SEO 블로그 자동 생성 시스템 - 환경 설정 가이드")
    print("=" * 60)

    print("\n📋 필수 환경 변수:")
    print(ENV_TEMPLATE)

    print("\n🚀 GPT-5 시리즈 모델 정보:")
    for model_name, info in GPT5_MODELS.items():
        print(f"\n  🔹 {model_name}")
        print(f"     설명: {info['description']}")
        print(f"     컨텍스트 윈도우: {info['context_window']:,} 토큰")
        print(f"     비용: {info['input_cost']} (입력) / {info['output_cost']} (출력)")
        print(f"     최적 용도: {', '.join(info['best_for'])}")
        print(
            f"     Temperature 설정: {'지원 안함 (고정값)' if not info['temperature_support'] else '지원'}"
        )

    print("\n💡 권장 설정:")
    print("  - 개발/테스트: gpt-5-nano (빠르고 경제적)")
    print("  - 일반 사용: gpt-5-mini (균형잡힌 성능)")
    print("  - 고품질 콘텐츠: gpt-5 (최고 품질)")

    print("\n⚠️  주의사항:")
    print("  - GPT-5 시리즈는 temperature 파라미터가 고정됨 (1.0)")
    print("  - API 키는 반드시 보안이 유지되는 곳에 저장")
    print("  - .env 파일은 Git에 커밋하지 말 것")


def validate_env_file(env_path: str = ".env") -> bool:
    """
    .env 파일의 유효성을 검증합니다.

    Args:
        env_path: .env 파일 경로

    Returns:
        bool: 유효한 설정인지 여부
    """
    import os
    from pathlib import Path

    if not Path(env_path).exists():
        print(f"❌ .env 파일이 없습니다: {env_path}")
        return False

    # 필수 변수 체크
    required_vars = ["OPENAI_API_KEY", "DEFAULT_LLM_PROVIDER"]
    missing_vars = []

    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)

    if missing_vars:
        print(f"❌ 필수 환경 변수 누락: {', '.join(missing_vars)}")
        return False

    # 모델 설정 확인
    model = os.getenv("OPENAI_MODEL", "gpt-5-nano")
    if model not in GPT5_MODELS:
        print(f"⚠️  알 수 없는 모델: {model}")
        print(f"   지원되는 모델: {', '.join(GPT5_MODELS.keys())}")

    print("✅ 환경 설정이 올바르게 구성되었습니다!")
    return True


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "validate":
        validate_env_file()
    else:
        print_config_guide()
