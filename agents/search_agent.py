import json
import asyncio
import os
from typing import Any, Dict, Optional, List
from openai import AsyncOpenAI
import googlemaps
from .base_agent import BaseAgent
from tools.tavily_search_tool import TavilySearchTool

class SearchAgent(BaseAgent):
    """
    사용자의 테마를 [행동 단위]로 분석하여 [코스 구조]를 먼저 설계하고,
    그 설계를 채울 최적의 장소를 발굴 및 검증하는 전략가 에이전트.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(name="SearchAgent", config=config)
        self.search_tool = TavilySearchTool(config=config)
        
        # 1. config에서 먼저 찾고, 없으면 os.environ에서 직접 찾음
        self.openai_api_key = self.config.get("openai_api_key") or os.getenv("OPENAI_API_KEY")
        self.google_maps_api_key = self.config.get("google_maps_api_key") or os.getenv("GOOGLE_MAPS_API_KEY")
        self.llm_model = self.config.get("llm_model", "gpt-4o-mini")
        
        # 2. 키가 여전히 없으면 명확한 에러 메시지 출력
        if not self.google_maps_api_key:
            raise ValueError("GOOGLE_MAPS_API_KEY가 설정되지 않았습니다. .env 파일이나 환경변수를 확인하세요.")
        
        self.client = AsyncOpenAI(api_key=self.openai_api_key)
        self.gmaps = googlemaps.Client(key=self.google_maps_api_key)

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """전략 수립 -> 행동 분해 -> 검색 -> 구글 검증 -> 후보 풀 반환"""
        if not self.validate_input(input_data):
            return {"success": False, "error": "입력 데이터가 유효하지 않습니다."}

        theme = input_data.get("theme")
        location = input_data.get("location")
        
        # 1. 전략 수립 (행동 분석 및 카테고리 설계)
        print(f"\n🧠 [Step 1] 테마 분석 및 코스 설계 중...")
        
        strategy = await self._generate_strategy(theme, location)
        if not strategy:
            return {"success": False, "error": "LLM 전략 수립 실패"}
        

        # 2. Tavily 멀티 검색 (본문 데이터 확보)
        print(f"📡 [Step 2] Tavily를 통해 실시간 데이터 수집 중...")

        tasks = [
            self.search_tool.execute(query=step['search_query'], max_results=10) 
            for step in strategy['course_structure']
        ]
        search_results = await asyncio.gather(*tasks)
        
        # ⭐ [여기서부터 추가/수정] 3. LLM 엔티티 추출 단계 (핵심 기획)
        print(f"📝 [Step 3] LLM이 검색 결과에서 진짜 장소명만 추출 중...")
        # 3. LLM 엔티티 추출 및 URL 보존
        all_raw_data = []
        for res in search_results:
            if res["success"]:
                # 제목, 본문, URL을 한 객체로 묶어서 전달
                for p in res["places"]:
                    all_raw_data.append({
                        "url": p['source_url'],
                        "text": f"제목: {p['name']}, 본문: {p['description']}"
                    })
                    
        # [Step 3 수정] 이름과 카테고리를 함께 추출
        # 수정된 추출 함수 호출
        refined_data = await self._extract_place_entities_with_source(all_raw_data, location)

        # 4. Google Maps 기반 검증
        candidate_pool = []
        seen_names = set() # 중복 제거용

        for item in refined_data:
            # 이제 name뿐만 아니라 category도 item 안에 들어있습니다.
            place_name = item.get('name')
            place_category = item.get('category', '장소') # 기본값 설정
            
            clean_name = self._clean_place_name(place_name)
            google_info = self._get_google_data(clean_name, location)
    
                
            # [핵심] 카테고리에 따른 유연한 필터링
            is_valid = False
            cat = item['category']
            
            if cat in ['식당', '카페']:
                # 식당/카페는 평점이 중요함
                if google_info and google_info['rating'] >= 4.0:
                    is_valid = True
            else:
                # 팝업, 전시, 활동 등은 평점이 없어도(0.0) 존재만 확인되면 통과
                if google_info: 
                    is_valid = True
                elif item['name']: # 구글에 없어도 Tavily에서 여러 번 언급되면 통과 (최신 팝업 대비)
                    is_valid = True
                    google_info = {"name": item['name'], "rating": 0.0, "reviews_count": 0, "address": "위치 정보 확인 필요"}

            if is_valid:
                g_name = google_info['name']
                if g_name in seen_names: continue
 
                # V2 점수 계산기 사용
                trust_score = self._calculate_trust_score_v2(
                    google_info['rating'], google_info['reviews_count'], item.get('text', ''), cat
                )

                               # 🔗 URL 인코딩 처리 (공백을 +로 치환하여 클릭 가능하게)
                encoded_name = g_name.replace(" ", "+")
                map_url = f"https://www.google.com/maps/search/?api=1&query={encoded_name}+{location.replace(' ', '+')}"

                print(f"   - [Keep] {google_info['name']} (평점: {google_info['rating']})")
                
                candidate_pool.append({
                    "name": g_name,
                    "category": place_category,
                    "rating": google_info['rating'],
                    "trust_score": trust_score,
                    "address": google_info['address'],
                    "source_url": item.get('source_url'), # 블로그/뉴스 링크
                    "map_url": map_url                    # 구글 지도 링크
                })
                seen_names.add(g_name)


        # 신뢰도 점수(Trust Score) 순으로 정렬하여 가장 쌈뽕한 곳을 위로
        candidate_pool.sort(key=lambda x: x['trust_score'], reverse=True)
        
        # SearchAgent.execute()의 리턴값 다음 에이전트에게 줄 '최종 패키지'
        return {
            "success": True,
            "agent_name": self.name,
            "action_analysis": strategy.get('action_analysis'),
            "candidate_pool": candidate_pool,
            "user_intent": {
                "course_structure": strategy.get('course_structure'),
                # 여기에 reasoning 정보가 step별로 포함되어 있어 데이터가 휘발되지 않음
                "raw_theme": theme,
                "location": location
            }
        }
    

    async def _extract_place_entities_with_source(self, raw_data: List[Dict], location: str) -> List[Dict]:
        """
        [최종형] 기존 Slop 제거 로직을 유지하며, 각 장소에 원본 URL을 매칭함.
        """
        if not raw_data: return []

        prompt = f"""
        당신은 정보 정제 및 여행 데이터 전문가입니다. 
        제공된 [검색 결과 데이터]를 분석하여 {location} 지역의 구체적인 '장소 이름(가게명, 카페명, 전시장명 등)'을 추출하고 카테고리를 분류하세요.
        또한, 각 장소가 어떤 'url'에서 추출되었는지 반드시 함께 기록해야 합니다.

        [임무 1: 엄격한 장소 이름 정제 (Slop 제거)]
        - 고유 명칭만 남기세요. (예: '성수동 힙한 카페 베이크모굴' -> '베이크모굴')
        - 일반 명사(맛집, 데이트 코스, 성수동 놀거리 등)는 절대 추출하지 말고 무시하세요.
        - 수식어(분위기 좋은, 맛있는, 핫플 등)를 완전히 제거하세요.
        - 블로그 제목 전체가 아닌, 그 안에서 언급된 '가게/장소의 이름'만 찾아내야 합니다.

        [임무 2: 카테고리 분류 및 URL 매칭]
        - 카테고리: [식당, 카페, 활동, 쇼핑, 숙소, 기타] 중 선택하세요.
        - URL: 제공된 데이터의 'url' 필드 값을 그대로 사용하세요.

        [분석할 데이터]
        {raw_data[:15]}

        [응답 형식 (JSON 고정)]
        {{
        "results": [
            {{
            "name": "장소명",
            "category": "식당",
            "source_url": "해당 데이터의 원본 url"
            }}
        ]
        }}
        """
        try:
            response = await self.client.chat.completions.create(
                model=self.llm_model,
                messages=[{"role": "system", "content": "You are a professional data cleaner. Output only JSON."},
                        {"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            data = json.loads(response.choices[0].message.content)
            return data.get("results", [])
        except Exception as e:
            print(f"❌ 엔티티 추출 에러: {e}")
            return []

    #(예: 대화 중심, 활동 중심, 휴식 중심)
    #(예: 조용한 카페, 실내 전시장, 분위기 있는 식당)

    async def _generate_strategy(self, theme: str, location: str) -> Optional[Dict]:
            """
            [핵심 페르소나 반영] 테마 분석 및 검색 전략 수립
            """
            prompt = f"""
            당신은 베테랑 여행 설계자입니다. 사용자의 테마를 분석하여 최적의 '코스 구조'를 설계하고, 각 구조를 채울 검색 쿼리를 생성하세요.

            [사용자 입력]
            - 테마: {theme}
            - 지역: {location}

            [임무]
            1. 이 테마에 필요한 '행동 타입(Action Types)'을 3가지 분석하세요. 
            2. 각 행동에 맞는 '장소 카테고리'를 결정하세요.
            3. 각 카테고리별로 Tavily 검색을 위한 최적화된 '검색 쿼리'와 그 쿼리를 선정한 '판단 근거'를 생성하세요.
            (팁: '추천', '리스트', '리뷰', '베스트' 같은 단어를 섞어야 구체적인 가게 이름이 잘 나옵니다.)

            [응답 형식 (JSON 고정)]
            {{
            "action_analysis": "행동 타입 분석 요약",
            "course_structure": [
                {{
                "step": 1, 
                "category": "카테고리명", 
                "search_query": "쿼리", 
                "reasoning": "이 쿼리를 선정한 이유"
                }},
                {{
                "step": 2, 
                "category": "카테고리명", 
                "search_query": "쿼리", 
                "reasoning": "이 쿼리를 선정한 이유"
                }},
                {{
                "step": 3, 
                "category": "카테고리명", 
                "search_query": "쿼리", 
                "reasoning": "이 쿼리를 선정한 이유"
                }}
            ]
            }}
            """
            try:
                response = await self.client.chat.completions.create(
                    model=self.llm_model,
                    messages=[{"role": "user", "content": prompt}],
                    response_format={"type": "json_object"}
                )
                return json.loads(response.choices[0].message.content)

            except Exception as e:
                print(f"⚠️ LLM 호출 실패(쿼터 초과 등): {e}")
                # Mock 데이터에서도 'reasoning' 필드를 유지하여 데이터 유실 방지
                return {
                    "action_analysis": f"{theme}을(를) 위한 실내외 혼합 활동 및 동선 최적화 전략",
                    "course_structure": [
                        {
                            "step": 1, "category": "카페", 
                            "search_query": f"{location} {theme} 분위기 좋은 카페",
                            "reasoning": "테마에 맞는 아늑한 분위기 형성을 위해 첫 번째 코스로 선정"
                        },
                        {
                            "step": 2, "category": "활동", 
                            "search_query": f"{location} {theme} 팝업스토어 전시회",
                            "reasoning": "지루함을 방지하고 테마의 핵심 경험을 제공하기 위한 메인 활동 선정"
                        },
                        {
                            "step": 3, "category": "식사", 
                            "search_query": f"{location} {theme} 맛집 추천",
                            "reasoning": "활동 후 만족스러운 마무리를 위한 현지 인기 식당 탐색"
                        }
                    ]
                }

    ## 한번 추가해보는 청소기
    def _clean_place_name(self, raw_name: str) -> str:
        """
        블로그 제목 등에서 실제 가게 이름만 남기기 위한 청소기
        예: '성수동 카페 베이크모굴 실내 놀거리 - 네이버 블로그' -> '베이크모굴'
        """
        # 1. 흔한 수식어 및 플랫폼 이름 제거
        junk_words = [
            '네이버 블로그', '네이버 포스트', '티스토리', '인스타그램', 'Instagram',
            '유튜브', 'YouTube', '트립닷컴', '나무위키', '총정리', '추천', 'BEST', 'TOP'
        ]
        
        clean_name = raw_name
        for word in junk_words:
            clean_name = clean_name.replace(word, "")
        
        # 2. 특수기호 제거 및 다듬기
        import re
        clean_name = re.sub(r'[\-\|\:\[\]\(\)]', ' ', clean_name) # 기호를 공백으로
        clean_name = re.sub(r'\s+', ' ', clean_name).strip()     # 연속 공백 제거
        
        # 3. 너무 길면 앞의 2~3단어만 사용 (보통 앞에 가게 이름이 나옴)
        parts = clean_name.split()
        if len(parts) > 3:
            return " ".join(parts[:2]) # '성수동 베이크모굴' 정도로 압축
            
        return clean_name
    
    def _get_google_data(self, name: str, location: str) -> Optional[Dict]:
        """Google Places API 검증 (이름 정제 로직 포함)"""
        try:
            # [수정] 지저분한 이름을 청소하고 검색
            search_name = self._clean_place_name(name)
            query = f"{location} {search_name}"
            
            print(f"   🔎 구글 검색 시도: '{query}'") # 어떤 키워드로 구글에 물어보는지 확인용
            
            res = self.gmaps.places(query=query)
            if res.get('results'):
                place = res['results'][0]
                return {
                    "name": place.get("name"), # 구글이 확인해준 진짜 가게 이름
                    "rating": place.get("rating", 0.0),
                    "reviews_count": place.get("user_ratings_total", 0),
                    "address": place.get("formatted_address")
                }
        except Exception as e:
            print(f"      ⚠️ 구글 API 에러: {e}")
            return None
        return None
    
    def _calculate_trust_score_v2(self, google_rating: float, google_reviews: int, content: str, category: str) -> float:
        """
        [V2] 카테고리별 차등 신뢰도 점수 로직
        - 식당/카페: 구글 평점의 비중이 높음
        - 활동/팝업/전시: 평점이 낮거나 없어도 최신 키워드(오픈, 핫플)에 가산점 부여
        """
        # 1. 기본 점수 설정
        if category in ['활동', '쇼핑', '기타'] and google_rating == 0:
            # 평점이 없는 최신 전시/팝업은 기본 점수를 4.0으로 보정 (발굴 가치 부여)
            base_score = 4.0
        else:
            base_score = google_rating

        score = base_score

        # 2. 보조 지표 1: 리뷰 수 가산점 (모든 카테고리 공통)
        if google_reviews > 500: score += 0.2
        elif google_reviews > 100: score += 0.1
    
        # 3. 보조 지표 2: 키워드 가산점 (카테고리별 차등)
        # 기존 '내돈내산' 등은 유지
        trust_keywords = ['내돈내산', '솔직후기', '분위기', '친절']
        for kw in trust_keywords:
            if kw in content: score += 0.05
            
        # [추가] 활동/팝업 전용 키워드 가산점
        if category in ['활동', '쇼핑', '기타']:
            trend_keywords = ['최신', '팝업', '전시', '오픈', '핫플', '기간한정']
            for kw in trend_keywords:
                if kw in content: score += 0.1 # 활동형 장소는 트렌드 점수를 더 높게 줌

        return round(min(score, 5.0), 2)

    def validate_input(self, input_data: Dict[str, Any]) -> bool:
        """BaseAgent의 필수 구현 추상 메서드"""
        if not isinstance(input_data, dict):
            return False
        return bool(input_data.get("theme") and input_data.get("location"))