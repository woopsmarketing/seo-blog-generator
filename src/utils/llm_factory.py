# src/utils/llm_factory.py
# LLM 인스턴스 생성 및 관리를 위한 팩토리 클래스

from typing import Dict, Any, Optional, Union
from dataclasses import dataclass
import logging

# LangChain imports
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain.schema.language_model import BaseLanguageModel

from .config import load_config, get_api_key

logger = logging.getLogger(__name__)


@dataclass
class LLMConfig:
    """LLM 설정을 위한 데이터 클래스"""

    provider: str  # "openai" 또는 "anthropic"
    model: str
    temperature: float = 0.7
    max_tokens: int = 2000
    api_key: Optional[str] = None


class LLMFactory:
    """LLM 인스턴스를 생성하고 관리하는 팩토리 클래스"""

    def __init__(self):
        self.config = load_config()
        self._llm_cache: Dict[str, BaseLanguageModel] = {}

    def create_openai_llm(self, config: LLMConfig) -> ChatOpenAI:
        """
        OpenAI LLM 인스턴스 생성

        Args:
            config: LLM 설정

        Returns:
            ChatOpenAI: OpenAI LLM 인스턴스
        """
        api_key = config.api_key or get_api_key("openai")

        if not api_key:
            raise ValueError("OpenAI API 키가 설정되지 않았습니다")

        # GPT-5 Nano는 temperature 고정 (1.0)이므로 기본값 사용
        llm_params = {
            "model_name": config.model,
            "openai_api_key": api_key,
            "max_tokens": config.max_tokens,
        }

        # GPT-5 Nano는 temperature 설정 불가능하므로 제거
        if not config.model.startswith("gpt-5"):
            llm_params["temperature"] = config.temperature

        return ChatOpenAI(**llm_params)

    def create_anthropic_llm(self, config: LLMConfig) -> ChatAnthropic:
        """
        Anthropic LLM 인스턴스 생성

        Args:
            config: LLM 설정

        Returns:
            ChatAnthropic: Anthropic LLM 인스턴스
        """
        api_key = config.api_key or get_api_key("anthropic")

        if not api_key:
            raise ValueError("Anthropic API 키가 설정되지 않았습니다")

        return ChatAnthropic(
            model=config.model,
            anthropic_api_key=api_key,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
        )

    def create_llm(self, config: LLMConfig) -> BaseLanguageModel:
        """
        설정에 따라 적절한 LLM 인스턴스를 생성합니다.

        Args:
            config: LLM 설정

        Returns:
            BaseLanguageModel: 생성된 LLM 인스턴스
        """
        # 캐시 키 생성
        cache_key = (
            f"{config.provider}_{config.model}_{config.temperature}_{config.max_tokens}"
        )

        # 캐시된 인스턴스가 있으면 반환
        if cache_key in self._llm_cache:
            logger.debug(f"캐시된 LLM 인스턴스 반환: {cache_key}")
            return self._llm_cache[cache_key]

        # 프로바이더에 따라 LLM 생성
        try:
            if config.provider == "openai":
                llm = self.create_openai_llm(config)
            elif config.provider == "anthropic":
                llm = self.create_anthropic_llm(config)
            else:
                raise ValueError(f"지원하지 않는 LLM 프로바이더: {config.provider}")

            # 캐시에 저장
            self._llm_cache[cache_key] = llm

            logger.info(f"LLM 인스턴스 생성 완료: {config.provider}/{config.model}")
            return llm

        except Exception as e:
            logger.error(f"LLM 인스턴스 생성 실패: {e}")
            raise

    def get_available_models(self) -> Dict[str, Dict[str, Any]]:
        """
        사용 가능한 모델 목록을 반환합니다.

        Returns:
            Dict: 프로바이더별 모델 정보
        """
        return {
            "openai": {
                "models": [
                    {
                        "name": "gpt-5-nano",
                        "description": "GPT-5 Nano - 가장 빠르고 경제적인 GPT-5 모델",
                        "context_window": 400000,
                        "input_cost": "$0.05/1M tokens",
                        "output_cost": "$0.40/1M tokens",
                        "features": [
                            "fastest",
                            "most_affordable",
                            "everyday_questions",
                        ],
                    },
                    {
                        "name": "gpt-5-mini",
                        "description": "GPT-5 Mini - 균형잡힌 성능과 비용",
                        "context_window": 400000,
                        "input_cost": "$0.25/1M tokens",
                        "output_cost": "$2.00/1M tokens",
                        "features": ["balanced", "cost_effective", "defined_tasks"],
                    },
                    {
                        "name": "gpt-5",
                        "description": "GPT-5 - 최고 성능의 플래그십 모델",
                        "context_window": 400000,
                        "input_cost": "$1.25/1M tokens",
                        "output_cost": "$10.00/1M tokens",
                        "features": [
                            "flagship",
                            "best_performance",
                            "complex_reasoning",
                        ],
                    },
                ]
            },
            "anthropic": {
                "models": [
                    {
                        "name": "claude-3-sonnet-20240229",
                        "description": "Claude 3 Sonnet - 균형잡힌 성능",
                        "context_window": 200000,
                        "features": ["balanced", "reasoning", "creative"],
                    },
                    {
                        "name": "claude-3-opus-20240229",
                        "description": "Claude 3 Opus - 최고 성능",
                        "context_window": 200000,
                        "features": [
                            "highest_quality",
                            "complex_reasoning",
                            "analysis",
                        ],
                    },
                    {
                        "name": "claude-3-haiku-20240307",
                        "description": "Claude 3 Haiku - 빠르고 경제적",
                        "context_window": 200000,
                        "features": ["fastest", "economical", "simple_tasks"],
                    },
                ]
            },
        }


def create_default_llm(
    custom_config: Optional[Dict[str, Any]] = None,
) -> BaseLanguageModel:
    """
    기본 설정으로 LLM 인스턴스를 생성합니다.

    Args:
        custom_config: 사용자 정의 설정 (선택사항)

    Returns:
        BaseLanguageModel: 기본 LLM 인스턴스
    """
    config = load_config()

    # 사용자 정의 설정이 있으면 병합
    if custom_config:
        config.update(custom_config)

    factory = LLMFactory()

    llm_config = LLMConfig(
        provider=config["llm"]["default_provider"],
        model=config["llm"]["openai_model"],  # 기본적으로 gpt-5-nano 사용
        temperature=config["llm"]["temperature"],
        max_tokens=config["llm"]["max_tokens"],
    )

    return factory.create_llm(llm_config)


# 팩토리 함수들 (편의성을 위한)
def create_gpt5_nano(
    api_key: Optional[str] = None, max_tokens: int = 2000
) -> ChatOpenAI:
    """GPT-5 Nano 전용 생성 함수"""
    factory = LLMFactory()
    config = LLMConfig(
        provider="openai",
        model="gpt-5-nano",
        temperature=1.0,  # GPT-5 Nano는 temperature 고정
        max_tokens=max_tokens,
        api_key=api_key,
    )
    return factory.create_openai_llm(config)


def create_gpt5_mini(
    api_key: Optional[str] = None, max_tokens: int = 2000
) -> ChatOpenAI:
    """GPT-5 Mini 전용 생성 함수"""
    factory = LLMFactory()
    config = LLMConfig(
        provider="openai",
        model="gpt-5-mini",
        temperature=1.0,  # GPT-5 시리즈는 temperature 고정
        max_tokens=max_tokens,
        api_key=api_key,
    )
    return factory.create_openai_llm(config)


def create_gpt5(api_key: Optional[str] = None, max_tokens: int = 2000) -> ChatOpenAI:
    """GPT-5 전용 생성 함수"""
    factory = LLMFactory()
    config = LLMConfig(
        provider="openai",
        model="gpt-5",
        temperature=1.0,  # GPT-5 시리즈는 temperature 고정
        max_tokens=max_tokens,
        api_key=api_key,
    )
    return factory.create_openai_llm(config)


if __name__ == "__main__":
    # 테스트 코드
    print("=== LLM Factory 테스트 ===")

    factory = LLMFactory()

    # 사용 가능한 모델 출력
    models = factory.get_available_models()
    print("\n사용 가능한 OpenAI 모델:")
    for model in models["openai"]["models"]:
        print(f"  - {model['name']}: {model['description']}")
        print(f"    컨텍스트: {model.get('context_window', 'N/A'):,} 토큰")
        print(
            f"    비용: {model.get('input_cost', 'N/A')} (입력) / {model.get('output_cost', 'N/A')} (출력)"
        )

    print("\n사용 가능한 Anthropic 모델:")
    for model in models["anthropic"]["models"]:
        print(f"  - {model['name']}: {model['description']}")

    print(f"\n기본 LLM: GPT-5 Nano (가장 빠르고 경제적인 선택)")
