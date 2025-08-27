# -*- coding: utf-8 -*-
"""
토큰 사용량 추적 및 비용 계산
"""

import json
import time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime
import tiktoken

@dataclass
class LLMCall:
    """LLM 호출 정보"""
    timestamp: str
    component: str  # title_generator, outline_generator 등
    operation: str  # generate_title, generate_outline 등
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost_usd: float
    duration_seconds: float
    success: bool
    error_message: Optional[str] = None

class TokenTracker:
    """토큰 사용량 및 비용 추적기"""
    
    # OpenAI 모델별 가격 (USD per 1K tokens) - 2024년 기준
    MODEL_PRICING = {
        "gpt-4o-mini": {
            "input": 0.00015,   # $0.15 per 1M input tokens
            "output": 0.0006    # $0.60 per 1M output tokens
        },
        "gpt-3.5-turbo": {
            "input": 0.0005,    # $0.50 per 1M input tokens  
            "output": 0.0015    # $1.50 per 1M output tokens
        },
        "gpt-4o": {
            "input": 0.0025,    # $2.50 per 1M input tokens
            "output": 0.01      # $10.00 per 1M output tokens
        },
        "gpt-4-turbo": {
            "input": 0.01,      # $10.00 per 1M input tokens
            "output": 0.03      # $30.00 per 1M output tokens
        }
    }
    
    def __init__(self):
        self.calls: List[LLMCall] = []
        self.session_start = datetime.now().isoformat()
        
    def estimate_tokens(self, text: str, model: str = "gpt-4o-mini") -> int:
        """텍스트의 토큰 수 추정"""
        try:
            # gpt-4o-mini는 cl100k_base 인코딩 사용
            encoding = tiktoken.encoding_for_model("gpt-4")  # fallback
            return len(encoding.encode(text))
        except:
            # 대략적 추정: 영어 기준 4글자당 1토큰, 한글 기준 2글자당 1토큰
            korean_chars = sum(1 for c in text if ord(c) > 127)
            english_chars = len(text) - korean_chars
            return (korean_chars // 2) + (english_chars // 4)
    
    def calculate_cost(self, model: str, prompt_tokens: int, completion_tokens: int) -> float:
        """비용 계산"""
        if model not in self.MODEL_PRICING:
            model = "gpt-4o-mini"  # 기본값
            
        pricing = self.MODEL_PRICING[model]
        
        # 1M 토큰 기준 가격을 1토큰 기준으로 변환
        input_cost = (prompt_tokens / 1000000) * pricing["input"] * 1000000
        output_cost = (completion_tokens / 1000000) * pricing["output"] * 1000000
        
        return input_cost + output_cost
    
    def start_call(self, component: str, operation: str, model: str, prompt: str) -> Dict[str, Any]:
        """LLM 호출 시작 추적"""
        call_id = len(self.calls)
        prompt_tokens = self.estimate_tokens(prompt, model)
        
        start_info = {
            "call_id": call_id,
            "start_time": time.time(),
            "component": component,
            "operation": operation,
            "model": model,
            "prompt_tokens": prompt_tokens,
            "prompt_preview": prompt[:200] + "..." if len(prompt) > 200 else prompt
        }
        
        return start_info
    
    def end_call(self, start_info: Dict[str, Any], response: str, success: bool = True, error: str = None):
        """LLM 호출 종료 및 결과 기록"""
        end_time = time.time()
        duration = end_time - start_info["start_time"]
        
        completion_tokens = self.estimate_tokens(response, start_info["model"]) if response else 0
        total_tokens = start_info["prompt_tokens"] + completion_tokens
        cost = self.calculate_cost(start_info["model"], start_info["prompt_tokens"], completion_tokens)
        
        call = LLMCall(
            timestamp=datetime.now().isoformat(),
            component=start_info["component"],
            operation=start_info["operation"],
            model=start_info["model"],
            prompt_tokens=start_info["prompt_tokens"],
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            cost_usd=cost,
            duration_seconds=duration,
            success=success,
            error_message=error
        )
        
        self.calls.append(call)
        return call
    
    def get_summary(self) -> Dict[str, Any]:
        """전체 사용량 요약"""
        total_prompt_tokens = sum(call.prompt_tokens for call in self.calls)
        total_completion_tokens = sum(call.completion_tokens for call in self.calls)
        total_tokens = sum(call.total_tokens for call in self.calls)
        total_cost = sum(call.cost_usd for call in self.calls)
        total_duration = sum(call.duration_seconds for call in self.calls)
        
        # 컴포넌트별 통계
        component_stats = {}
        for call in self.calls:
            if call.component not in component_stats:
                component_stats[call.component] = {
                    "calls": 0,
                    "tokens": 0,
                    "cost": 0,
                    "duration": 0
                }
            
            stats = component_stats[call.component]
            stats["calls"] += 1
            stats["tokens"] += call.total_tokens
            stats["cost"] += call.cost_usd
            stats["duration"] += call.duration_seconds
        
        # 모델별 통계
        model_stats = {}
        for call in self.calls:
            if call.model not in model_stats:
                model_stats[call.model] = {
                    "calls": 0,
                    "tokens": 0,
                    "cost": 0
                }
            
            stats = model_stats[call.model]
            stats["calls"] += 1
            stats["tokens"] += call.total_tokens
            stats["cost"] += call.cost_usd
        
        return {
            "session_info": {
                "start_time": self.session_start,
                "end_time": datetime.now().isoformat(),
                "total_calls": len(self.calls),
                "successful_calls": len([c for c in self.calls if c.success]),
                "failed_calls": len([c for c in self.calls if not c.success])
            },
            "token_usage": {
                "total_prompt_tokens": total_prompt_tokens,
                "total_completion_tokens": total_completion_tokens,
                "total_tokens": total_tokens
            },
            "cost_analysis": {
                "total_cost_usd": round(total_cost, 6),
                "average_cost_per_call": round(total_cost / len(self.calls), 6) if self.calls else 0,
                "cost_breakdown_by_component": {k: round(v["cost"], 6) for k, v in component_stats.items()},
                "cost_breakdown_by_model": {k: round(v["cost"], 6) for k, v in model_stats.items()}
            },
            "performance": {
                "total_duration_seconds": round(total_duration, 2),
                "average_duration_per_call": round(total_duration / len(self.calls), 2) if self.calls else 0,
                "duration_by_component": {k: round(v["duration"], 2) for k, v in component_stats.items()}
            },
            "component_breakdown": component_stats,
            "model_breakdown": model_stats,
            "detailed_calls": [
                {
                    "timestamp": call.timestamp,
                    "component": call.component,
                    "operation": call.operation,
                    "model": call.model,
                    "tokens": {
                        "prompt": call.prompt_tokens,
                        "completion": call.completion_tokens,
                        "total": call.total_tokens
                    },
                    "cost_usd": round(call.cost_usd, 6),
                    "duration_seconds": round(call.duration_seconds, 2),
                    "success": call.success,
                    "error": call.error_message
                }
                for call in self.calls
            ]
        }
    
    def save_report(self, filepath: str):
        """리포트를 JSON 파일로 저장"""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.get_summary(), f, ensure_ascii=False, indent=2)

# 전역 토큰 트래커 인스턴스
global_token_tracker = TokenTracker()