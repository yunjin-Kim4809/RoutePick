import os
from typing import Any, Dict, Optional
from tavily import TavilyClient
from .base_tool import BaseTool

class TavilySearchTool(BaseTool):
    """Tavily API를 사용한 실시간 검색 Tool"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(
            name="tavily_search",
            description="전략적 쿼리를 통해 웹상에서 장소 후보를 발굴합니다.",
            config=config or {}
        )
        self.api_key = self.config.get("api_key") or os.getenv("TAVILY_API_KEY")
        if not self.api_key:
            raise ValueError("TAVILY_API_KEY가 설정되지 않았습니다.")
        
        self.client = TavilyClient(api_key=self.api_key)

    async def execute(self, query: str, max_results: int = 10, **kwargs) -> Dict[str, Any]:
        """Tavily 검색 실행"""
        try:
            # 고급 검색(advanced)으로 본문 텍스트를 풍부하게 가져옴
            response = self.client.search(
                query=query, 
                max_results=max_results, 
                search_depth="advanced"
            )
            
            raw_results = response.get("results", [])
            places = []
            
            for res in raw_results:
                places.append({
                    "name": res.get("title"),
                    "description": res.get("content", ""),
                    "source_url": res.get("url")
                })
                
            return {"success": True, "places": places}
        except Exception as e:
            return {"success": False, "places": [], "error": str(e)}

    def get_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "max_results": {"type": "integer", "default": 10}
            },
            "required": ["query"]
        }