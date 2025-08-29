# src/utils/config.py
# 환경 설정 및 API 키 관리

import os
from typing import Dict, Any, Optional
from dotenv import load_dotenv
import logging

# .env 파일 로드
load_dotenv()

# 로깅 설정
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def load_config() -> Dict[str, Any]:
    """
    환경 변수에서 설정 정보를 로드합니다.

    Returns:
        Dict: 프로젝트 설정 정보
    """
    config = {
        # LLM 설정
        "llm": {
            "default_provider": os.getenv(
                "DEFAULT_LLM_PROVIDER", "openai"
            ),  # openai 또는 anthropic
            "openai_model": os.getenv(
                "OPENAI_MODEL", "gpt-5-nano"
            ),  # GPT-5 nano 공식 모델명 사용 (가장 경제적이고 빠른 GPT-5 모델)
            "anthropic_model": os.getenv("ANTHROPIC_MODEL", "claude-3-sonnet-20240229"),
            "temperature": float(os.getenv("LLM_TEMPERATURE", "1.0")),
            "max_tokens": int(os.getenv("LLM_MAX_TOKENS", "2000")),
        },
        # WordPress 설정
        "wordpress": {
            "url": os.getenv("WP_URL", ""),
            "username": os.getenv("WP_USERNAME", ""),
            "password": os.getenv("WP_PASSWORD", ""),
        },
        # 로깅 설정
        "logging": {
            "level": os.getenv("LOG_LEVEL", "INFO"),
            "file": os.getenv("LOG_FILE", "blog_generation.log"),
        },
        # 콘텐츠 생성 설정
        "content": {
            "min_section_length": int(os.getenv("MIN_SECTION_LENGTH", "300")),
            "max_section_length": int(os.getenv("MAX_SECTION_LENGTH", "500")),
            "target_total_length": int(os.getenv("TARGET_TOTAL_LENGTH", "3000")),
        },
    }

    logger.info(
        f"설정 로드 완료: LLM 프로바이더={config['llm']['default_provider']}, 모델={config['llm']['openai_model']}"
    )
    return config


def get_api_key(provider: str) -> Optional[str]:
    """
    지정된 프로바이더의 API 키를 반환합니다.

    Args:
        provider: API 프로바이더 이름 ("openai", "anthropic")

    Returns:
        Optional[str]: API 키 또는 None
    """
    provider_key_mapping = {
        "openai": "OPENAI_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
    }

    env_key = provider_key_mapping.get(provider)
    if not env_key:
        logger.error(f"지원하지 않는 프로바이더: {provider}")
        return None

    api_key = os.getenv(env_key)
    if not api_key:
        logger.warning(f"{provider} API 키가 설정되지 않았습니다 (환경변수: {env_key})")

    return api_key


def validate_config(config: Dict) -> str:
    """설정 유효성 검사 및 API 키 상태 확인"""
    try:
        provider = config["llm"]["default_provider"]
        api_key = get_api_key(provider)

        if api_key:
            return f"{provider.upper()} API 키 설정됨"
        else:
            return f"{provider.upper()} API 키 없음"
    except Exception as e:
        return f"설정 오류: {e}"


def setup_logging(config: Dict[str, Any]) -> None:
    """
    로깅 설정을 초기화합니다.

    Args:
        config: 설정 딕셔너리
    """
    log_level = config.get("logging", {}).get("level", "INFO")
    log_file = config.get("logging", {}).get("file_path", "blog_generation.log")

    # 로그 레벨 설정
    numeric_level = getattr(logging, log_level.upper(), None)
    if not isinstance(numeric_level, int):
        numeric_level = logging.INFO

    # 루트 로거 설정
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    # 파일 핸들러 추가 (만약 없다면)
    if not any(isinstance(h, logging.FileHandler) for h in root_logger.handlers):
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(numeric_level)

        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    logger.info(f"로깅 초기화 완료: 레벨={log_level}, 파일={log_file}")


if __name__ == "__main__":
    # 설정 테스트
    config = load_config()
    print("=== 설정 정보 ===")
    print(f"LLM 프로바이더: {config['llm']['default_provider']}")
    print(f"API 키 상태: {validate_config(config)}")
    print(f"WordPress URL: {config['wordpress']['url'] or '설정되지 않음'}")
    print(f"로그 레벨: {config['logging']['level']}")
