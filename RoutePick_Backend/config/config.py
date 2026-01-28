"""
설정 관리 모듈
환경 변수 및 설정을 관리합니다.
"""

import os
from dotenv import load_dotenv
from typing import Dict, Any

# .env 파일에서 환경 변수 로드 (모듈 최상위에서 한 번만 실행)
load_dotenv()


class Config:
    """전역 설정 클래스"""
    
    # API Keys
    TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")
    GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY", "")
    T_MAP_API_KEY = os.getenv("T_MAP_API_KEY", "")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    WEATHER_API_KEY = os.getenv("WEATHER_API_KEY", "") or os.getenv("OPENWEATHER_API_KEY", "")

    # LLM 설정
    LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")
    
    # 검색 설정
    DEFAULT_MAX_RESULTS = int(os.getenv("DEFAULT_MAX_RESULTS", "20"))
    DEFAULT_MIN_RATING = float(os.getenv("DEFAULT_MIN_RATING", "4.0"))
    
    # Google Maps 설정
    DEFAULT_TRANSPORT_MODE = os.getenv("DEFAULT_TRANSPORT_MODE", "transit")
    
    @classmethod
    def get_agent_config(cls) -> Dict[str, Any]:
        """Agent 설정 딕셔너리 반환"""
        return {
            "api_key": cls.TAVILY_API_KEY,
            "google_maps_api_key": cls.GOOGLE_MAPS_API_KEY,
            "t_map_api_key": cls.T_MAP_API_KEY,
            "openai_api_key": cls.OPENAI_API_KEY,
            "weather_api_key": cls.WEATHER_API_KEY,
            "llm_model": cls.LLM_MODEL,
            "max_results": cls.DEFAULT_MAX_RESULTS,
            "min_rating": cls.DEFAULT_MIN_RATING,
            "transport_mode": cls.DEFAULT_TRANSPORT_MODE
        }
    
    @classmethod
    def validate(cls) -> bool:
        """필수 설정값 검증"""
        errors = []
        
        if not cls.TAVILY_API_KEY:
            errors.append("TAVILY_API_KEY가 설정되지 않았습니다.")
        if not cls.GOOGLE_MAPS_API_KEY:
            errors.append("GOOGLE_MAPS_API_KEY가 설정되지 않았습니다.")
        if not cls.OPENAI_API_KEY:
            errors.append("OPENAI_API_KEY가 설정되지 않았습니다.")
        
        if errors:
            print("설정 오류:")
            for error in errors:
                print(f"  - {error}")
            return False
        
        return True

