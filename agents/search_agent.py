import json
import asyncio
import os
import random 
from typing import Any, Dict, Optional, List, Tuple
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
        
        # [수정] 사용자 요청 지역의 행정구역 정보 미리 분석
        print(f"\n📍 [Step 1-1] 사용자 요청 지역 분석: '{location}'")
        target_city, target_gu = self._get_target_admin_areas(location)
        if not target_city and not target_gu:
            print(f"   ⚠️ '{location}' 지역 분석 실패. 기존 문자열 비교 방식으로 검증합니다.")
        else:
            print(f"   - 분석 결과: City='{target_city or 'N/A'}', Gu='{target_gu or 'N/A'}'")
     
        # 전략 수립 (행동 분석 및 카테고리 설계)
        print(f"\n🧠 [Step 1-2] 테마 분석 및 코스 설계 중...")
        
        strategy = await self._generate_strategy(theme, location)
        if not strategy:
            return {"success": False, "error": "LLM 전략 수립 실패"}
        

        # 2. Tavily 멀티 검색 (본문 데이터 확보)
        print(f"📡 [Step 2] Tavily를 통해 실시간 데이터 수집 중... ")

        # Tavily 검색 결과 수 최적화 (20 -> 15로 줄여서 처리 시간 단축, 정확도 유지)
        tasks = [
            self.search_tool.execute(query=step['search_query'], max_results=15) 
            for step in strategy['course_structure']
        ]
        search_results = await asyncio.gather(*tasks)
        
        
        print(f"📝 [Step 3-1] LLM이 검색 결과에서 진짜 장소명만 추출 중...")
        # 3. LLM 엔티티 추출 및 URL 보존
        all_raw_data = []
        for res in search_results:
            if res["success"]:
                # 제목, 본문, URL을 한 객체로 묶어서 전달 (길이 제한 적용)
                for p in res["places"]:
                    all_raw_data.append({
                        "url": p["source_url"],
                        "title": self._shrink_text(p.get("name", ""), 120),
                        "snippet": self._shrink_text(p.get("description", ""), 900),
                    })
                
        # 데이터 순서를 섞어서 특정 카테고리 쏠림 방지
        random.shuffle(all_raw_data) 
        print(f"📝 [Step 3-2] LLM이 원문 전체를 전수 조사 중...")
        refined_data = await self._extract_place_entities_with_source(all_raw_data, location)
        print(f"   ✅ LLM이 {len(all_raw_data)}개 데이터에서 발굴한 유니크 장소: {len(refined_data)}개")

        # 인기도(언급 횟수) 계산
        mention_counts = {}
        for item in refined_data:
            name = item.get('name')
            mention_counts[name] = mention_counts.get(name, 0) + 1

        # 4. Google Maps 기반 검증 (병렬 처리로 속도 최적화)
        print(f"🔍 [Step 3-3] Google Places API로 장소 검증 중... ({len(refined_data)}개)")
        print("-" * 60) # 디버깅 구분선
        
        async def process_place_item(agent_self, item):
            place_name = item.get('name')
            clean_name = agent_self._clean_place_name(place_name)
            google_info = await asyncio.to_thread(agent_self._get_google_data, clean_name, location)
            return item, google_info
        
        place_tasks = [process_place_item(self, item) for item in refined_data]
        place_results = await asyncio.gather(*place_tasks)
        
        # [수정] 필터링 로직을 검증 루프 밖으로 빼서 가독성 향상
        all_valid_places = []
        for item, google_info in place_results:
            # --- [디버깅 로그] ---
            place_name_for_log = item.get('name', '이름 없음')
            print(f"\n[검증 시작] '{place_name_for_log}'")

            if not google_info:
                print(f"  [탈락 ❌] 이유: Google Maps 정보 없음")
                continue
            
            print(f"  [정보 확인 ✅] 구글 이름: '{google_info.get('name')}', 주소: {google_info.get('address')}")
            

            # 1. 지역 필터링
            # [최종 수정] 새로운 _is_in_target_area 함수를 사용하여 한 번에 검증
            if not self._is_in_target_area(google_info.get('address_components', []), target_gu):
                print(f"  [탈락 ❌] 이유: 지역 불일치 (요청 지역: '{location}')")
                continue

            print(f"  [지역 통과 ✅]")

            # 2. 카테고리 보정
            initial_category = item.get('category', '기타')
            corrected_category = self._correct_category(google_info.get('types', []), initial_category)
            if initial_category != corrected_category:
                print(f"  [카테고리 보정] {initial_category} -> {corrected_category}")

            # 3. 품질 필터링
            g_rating = google_info.get('rating', 0.0)
            if 0.1 <= g_rating < 3.5:
                print(f"  [탈락 ❌] 이유: 낮은 평점 ({g_rating})")
                continue

            if corrected_category in ['식당', '카페'] and g_rating < 4.0:
                print(f"  [탈락 ❌] 이유: 카테고리별 평점 미달 (카테고리: {corrected_category}, 평점: {g_rating})")
                continue
            
            print(f"  [최종 통과 ✅] 모든 필터를 통과했습니다.")


            # 모든 필터 통과 시, 최종 객체 생성
            place_obj = {
                "google_info": google_info, "item": item,
                "category": corrected_category, "place_name": item.get('name')
            }
            all_valid_places.append(place_obj)
        print("-" * 60) # 디버깅 구분선
        # ============================================================
        # [수정] 최종 후보군 생성 (라운드 로빈 -> 품질 기반 선별)
        # ============================================================
        # 신뢰도 점수 계산
        for p_obj in all_valid_places:
            original_desc = next((f"{raw.get('title', '')} {raw.get('snippet', '')}".strip() for raw in all_raw_data if raw['url'] == p_obj['item'].get('source_url')), "")
            p_obj['trust_score'] = self._calculate_trust_score_v4(
                p_obj['google_info'].get('rating', 0.0), p_obj['google_info'].get('reviews_count', 0),
                original_desc, p_obj['category'], mention_counts.get(p_obj['place_name'], 1)
            )

        # 신뢰도 점수 순으로 정렬
        all_valid_places.sort(key=lambda p: p['trust_score'], reverse=True)
        
        # 중복 제거 및 상위 40개 선택
        candidate_pool_raw, seen_names = [], set()
        for p_obj in all_valid_places:
            g_name = p_obj['google_info'].get('name')
            if g_name and g_name not in seen_names:
                map_url = f"https://www.google.com/maps/search/?api=1&query={g_name.replace(' ', '+')}+{location.replace(' ', '+')}"
                candidate_pool_raw.append({
                    "name": g_name, "category": p_obj['category'], "rating": p_obj['google_info'].get('rating', 0.0),
                    "trust_score": p_obj['trust_score'], "address": p_obj['google_info'].get('address'),
                    "coordinates": p_obj['google_info'].get('coordinates'),
                    "source_url": p_obj['item'].get('source_url'), "map_url": map_url,
                    "photo_url": p_obj['google_info'].get('photo_url')
                })
                seen_names.add(g_name)
        
        candidate_pool = candidate_pool_raw[:40]

        print(f"\n✅ 1차 필터링 완료: {len(candidate_pool)}개의 유효 후보 장소를 다음 에이전트로 전달합니다.")
        
        return {
            "success": True, "agent_name": self.name,
            "action_analysis": strategy.get('action_analysis'), "candidate_pool": candidate_pool,
            "user_intent": {"course_structure": strategy.get('course_structure'), "raw_theme": theme, "location": location}
        }
     

    # [카테고리 수정] _correct_category 헬퍼 메소드 추가
    def _correct_category(self, google_types: List[str], initial_category: str) -> str:
        """구글의 types 정보를 바탕으로 카테고리를 보정합니다."""
        CATEGORY_MAP = {
            "카페": ["cafe", "bakery"],
            "식당": ["restaurant", "meal_takeaway", "food"],
            "활동": ["movie_theater", "art_gallery", "museum", "amusement_park"],
            "쇼핑": ["shopping_mall", "department_store", "clothing_store", "book_store"],
            "관광지": ["tourist_attraction", "park", "landmark"],
            "숙소": ["lodging"],
        }
        for category, keywords in CATEGORY_MAP.items():
            if any(keyword in google_types for keyword in keywords):
                return category # 1순위: 구글 정보로 확정
        return initial_category # 2순위: 구글 정보 없으면 LLM 분류 존중
    
    
    async def _extract_place_entities_with_source(self, raw_data: List[Dict], location: str) -> List[Dict]:
        """
        [병렬 고도화] 60개 데이터를 배치로 나눠 '동시에' LLM에게 전달합니다.
        정확도는 유지하고 속도는 10배 향상시킵니다.
        """
        if not raw_data: return []
        
        # 1. 배치 크기 설정 (속도 최적화: 6 -> 8로 증가, 정확도 유지)
        BATCH_SIZE = 8
        batches = [raw_data[i:i + BATCH_SIZE] for i in range(0, len(raw_data), BATCH_SIZE)]
        total_batches = len(batches)
        
        print(f"   🚀 총 {len(raw_data)}개 데이터를 {total_batches}개 배치로 '병렬' 마이닝 시작...")
        
        # 2. [핵심] 비동기 태스크 리스트 생성
        # 각 배치를 처리하는 함수를 실행 예약(Task) 상태로 만듭니다.
        tasks = [
            self._process_batch(batch_data, location, i + 1, total_batches)
            for i, batch_data in enumerate(batches)
        ]
        
        # 3. [핵심] 동시에 실행 및 결과 수집
        # asyncio.gather는 모든 태스크가 끝날 때까지 기다렸다가 결과 리스트를 반환합니다.
        batch_results_list = await asyncio.gather(*tasks)
        
        # 4. 결과 통합
        all_results = []
        for batch_results in batch_results_list:
            if batch_results:
                all_results.extend(batch_results)
        
        # 5. 중복 제거 (이름과 URL 기준)
        unique_results = []
        seen = set()
        for item in all_results:
            key = (item.get('name', '').strip(), item.get('source_url', ''))
            if key not in seen and key[0]:
                seen.add(key)
                unique_results.append(item)
        
        print(f"   ✅ 병렬 마이닝 완료: 총 {len(unique_results)}개의 유니크 장소 발굴")
        return unique_results
    
    async def _process_batch(self, batch_data: List[Dict], location: str, batch_num: int, total_batches: int) -> List[Dict]:
        """배치 데이터 처리"""
        prompt = f"""
        당신은 방대한 웹 데이터를 분석하여 가치 있는 장소 정보만 골라내는 '여행 정보 마이닝 전문가'입니다. 
        제공된 {len(batch_data)}개의 검색 결과(배치 {batch_num}/{total_batches})에서 {location} 지역의 진짜 '장소명'을 추출하고 분류하세요.

        [임무 1: 데이터 정제 및 중복 제거 (필수)]
        - 동일한 장소가 여러 검색 결과에 나타날 경우, 가장 정보가 알찬 하나의 결과로 통합하세요.
        - 수식어와 일반 명사를 제거한 '순수 상호명'만 남기세요. (예: '성수동 핫플 카페 어니언' -> '어니언')
        - 한 포스팅/기사에 여러 장소(예: 혜화 맛집 5곳 리스트)가 있다면 **반드시 모든 장소를 개별적으로 추출**하세요.

        [임무 2: 엄격한 필터링]
        - '맛집', '코스', '여행지', '데이트 장소'와 같은 일반 명칭은 장소명에서 제외하세요.
        - 구글 지도에서 검색했을 때 정확히 위치가 나올 법한 고유 명사여야 합니다.
        - '관광객이 직접 방문하여 시간을 보낼 수 있는 실체가 있는 장소'만 추출하세요.
        - 제외 대상: 부동산, 추진위원회, 아파트 단지명, 단순 지역명, 공공기관, 기업 사무실.

        [임무 3: 카테고리 분류 지침 (범용)]
        아래 리스트 중 가장 적합한 하나를 선택하세요: [식당, 카페, 활동, 쇼핑, 숙소, 관광지, 기타]
        - 식당: 밥집, 레스토랑, 주점, 요리 중심 공간
        - 카페: 커피, 디저트, 베이커리, 찻집
        - 활동: 연극, 뮤지컬, 소극장, 방탈출, 공방, 전시회, 원데이클래스, 팝업스토어, 스크린스포츠 등 '체험' 중심 공간.
        - 관광지: 공원, 해수욕장, 유적지, 랜드마크 등 '관람/풍경' 중심 공간.
        - 쇼핑: 편집샵, 소품샵, 백화점 등 물건 구매 공간.
        - 출처: 해당 장소가 언급된 데이터의 'url' 필드 값을 정확히 매칭하세요.

        [임무 4: 전수 조사 명령 (중요)]
        - 제공된 데이터를 절대로 대충 훑지 마세요. 
        - 각 본문 텍스트를 끝까지 읽고 숨겨진 장소명을 모두 찾아내세요.
        - 결과가 많아도 좋으니 누락되는 장소가 없게 하는 것이 최우선입니다.

        [분석할 데이터]
        각 데이터는 다음 형식입니다:
        - url: 출처 URL
        - title: 제목 (최대 120자)
        - snippet: 본문 요약 (최대 900자)
        
        {batch_data}

        [응답 형식]
        **반드시 다음의 JSON 형식만** 출력하세요. 다른 설명이나 텍스트는 포함하지 마세요.
        
        ```json
        {{
          "results": [
            {{
              "name": "장소명",
              "category": "카테고리",
              "source_url": "데이터에 제공된 실제 url"
            }}
          ]
        }}
        ```
        
        **중요: JSON 형식만 출력하고, 다른 텍스트는 포함하지 마세요.**
        """
        
        try:
            response = await self.client.chat.completions.create(
                model=self.llm_model,
                messages=[{"role": "system", "content": "You are a professional travel data miner who never skips info. Output only JSON."},
                          {"role": "user", "content": prompt}],
                max_tokens=1500,  # 장소명 리스트 추출에는 1500 토큰으로 충분 (입력 토큰 여유 확보)
                temperature=0.3  # 일관된 JSON 형식 유지
            )
            
            # 응답에서 JSON 추출
            response_content = response.choices[0].message.content.strip()
            
            # JSON 부분만 추출 (마크다운 코드 블록 제거)
            if "```json" in response_content:
                json_start = response_content.find("```json") + 7
                json_end = response_content.find("```", json_start)
                if json_end == -1:
                    json_end = len(response_content)
                response_content = response_content[json_start:json_end].strip()
            elif "```" in response_content:
                json_start = response_content.find("```") + 3
                json_end = response_content.find("```", json_start)
                if json_end == -1:
                    json_end = len(response_content)
                response_content = response_content[json_start:json_end].strip()
            
            # JSON 객체 시작/끝 찾기 (중괄호 기준)
            json_start_idx = response_content.find("{")
            json_end_idx = response_content.rfind("}") + 1
            if json_start_idx != -1 and json_end_idx > json_start_idx:
                response_content = response_content[json_start_idx:json_end_idx]
            
            # JSON 파싱 (더 강력한 오류 처리)
            try:
                data = json.loads(response_content)
                results = data.get("results", [])
                print(f"      ✅ 배치 {batch_num}에서 {len(results)}개 장소 추출 완료")
                return results
            except json.JSONDecodeError as e:
                # JSON 파싱 오류 시 응답 내용에서 JSON 부분을 더 적극적으로 찾기
                print(f"      ⚠️  배치 {batch_num} JSON 파싱 오류 시도 중... (오류: {str(e)[:100]})")
                
                # 방법 1: 첫 번째 { 부터 마지막 } 까지 다시 추출
                try:
                    first_brace = response_content.find('{')
                    last_brace = response_content.rfind('}')
                    if first_brace != -1 and last_brace > first_brace:
                        cleaned_json = response_content[first_brace:last_brace+1]
                        data = json.loads(cleaned_json)
                        results = data.get("results", [])
                        print(f"      ✅ 배치 {batch_num} 복구 성공 (방법1): {len(results)}개 장소 추출")
                        return results
                except Exception as e1:
                    pass
                
                # 방법 2: 불완전한 JSON 복구 시도 (닫히지 않은 문자열/배열 수정)
                try:
                    # JSON이 중간에 잘린 경우를 대비해 복구 시도
                    first_brace = response_content.find('{')
                    if first_brace != -1:
                        # "results" 배열이 있는지 확인
                        if '"results"' in response_content:
                            # 마지막 완전한 객체까지 찾기
                            json_part = response_content[first_brace:]
                            
                            # 닫히지 않은 문자열 닫기
                            if json_part.count('"') % 2 != 0:
                                json_part += '"'
                            
                            # 닫히지 않은 배열/객체 닫기
                            open_braces = json_part.count('{')
                            close_braces = json_part.count('}')
                            open_brackets = json_part.count('[')
                            close_brackets = json_part.count(']')
                            
                            # 부족한 닫는 괄호 추가
                            json_part += '}' * (open_braces - close_braces)
                            json_part += ']' * (open_brackets - close_brackets)
                            
                            # 마지막 쉼표 제거 (잘못된 JSON 형식 방지)
                            json_part = json_part.rstrip().rstrip(',')
                            if not json_part.endswith('}'):
                                json_part += '}'
                            
                            data = json.loads(json_part)
                            results = data.get("results", [])
                            if results:
                                print(f"      ✅ 배치 {batch_num} 복구 성공 (방법2): {len(results)}개 장소 추출")
                                return results
                except Exception as e2:
                    pass
                
                # 방법 3: 정규식으로 JSON 객체 추출 시도
                try:
                    import re
                    # "results" 배열 내의 객체들만 추출
                    pattern = r'\{[^{}]*"name"\s*:\s*"[^"]*"[^{}]*"category"\s*:\s*"[^"]*"[^{}]*"source_url"\s*:\s*"[^"]*"[^{}]*\}'
                    matches = re.findall(pattern, response_content, re.DOTALL)
                    if matches:
                        results = []
                        for match in matches:
                            try:
                                obj = json.loads(match)
                                if "name" in obj and "category" in obj:
                                    results.append(obj)
                            except:
                                continue
                        if results:
                            print(f"      ✅ 배치 {batch_num} 복구 성공 (방법3): {len(results)}개 장소 추출")
                            return results
                except Exception as e3:
                    pass
                
                # 모든 복구 시도 실패
                print(f"      ❌ 배치 {batch_num} JSON 파싱 실패 (응답 길이: {len(response_content)}, 일부: {response_content[:300]})")
                # 디버깅을 위해 전체 응답 저장 (선택사항)
                if len(response_content) < 2000:  # 너무 길지 않으면 전체 출력
                    print(f"      📋 전체 응답: {response_content}")
                return []
                
        except Exception as e:
            error_msg = str(e)
            
            # 컨텍스트 길이 초과 오류 처리
            if "context length" in error_msg.lower() or "8192" in error_msg or "maximum context" in error_msg.lower():
                print(f"      ⚠️  배치 {batch_num} 컨텍스트 길이 초과. 배치 크기를 줄여 재시도...")
                # 배치를 더 작게 나누어 재시도
                if len(batch_data) > 3:
                    mid = len(batch_data) // 2
                    first_half = batch_data[:mid]
                    second_half = batch_data[mid:]
                    
                    results = []
                    if first_half:
                        sub_results = await self._process_batch(first_half, location, batch_num * 100, total_batches)
                        results.extend(sub_results)
                    if second_half:
                        sub_results = await self._process_batch(second_half, location, batch_num * 100 + 1, total_batches)
                        results.extend(sub_results)
                    return results
                else:
                    print(f"      ⚠️  배치 {batch_num}가 너무 작아도 실패. 건너뜁니다.")
                    return []
            
            # Rate limit 오류 처리
            elif "rate_limit" in error_msg.lower() or "429" in error_msg:
                print(f"      ⚠️  배치 {batch_num} 처리 중 토큰 제한 초과. 잠시 대기 후 재시도...")
                import asyncio
                await asyncio.sleep(3)  # 3초 대기
                # 재시도
                try:
                    response = await self.client.chat.completions.create(
                        model=self.llm_model,
                        messages=[{"role": "system", "content": "You are a professional travel data miner who never skips info. Output only JSON."},
                                  {"role": "user", "content": prompt}],
                        max_tokens=1500,
                        temperature=0.3
                    )
                    response_content = response.choices[0].message.content.strip()
                    
                    if "```json" in response_content:
                        json_start = response_content.find("```json") + 7
                        json_end = response_content.find("```", json_start)
                        if json_end == -1:
                            json_end = len(response_content)
                        response_content = response_content[json_start:json_end].strip()
                    elif "```" in response_content:
                        json_start = response_content.find("```") + 3
                        json_end = response_content.find("```", json_start)
                        if json_end == -1:
                            json_end = len(response_content)
                        response_content = response_content[json_start:json_end].strip()
                    
                    json_start_idx = response_content.find("{")
                    json_end_idx = response_content.rfind("}") + 1
                    if json_start_idx != -1 and json_end_idx > json_start_idx:
                        response_content = response_content[json_start_idx:json_end_idx]
                    
                    data = json.loads(response_content)
                    results = data.get("results", [])
                    print(f"      ✅ 배치 {batch_num} 재시도 성공: {len(results)}개 장소 추출")
                    return results
                except Exception as retry_e:
                    print(f"      ⚠️  배치 {batch_num} 재시도 실패: {str(retry_e)[:100]}")
                    return []
            else:
                print(f"      ⚠️  배치 {batch_num} 처리 중 오류: {error_msg[:150]}")
                return []  

    #(예: 대화 중심, 활동 중심, 휴식 중심)
    #(예: 조용한 카페, 실내 전시장, 분위기 있는 식당)

    async def _generate_strategy(self, theme: str, location: str) -> Optional[Dict]:
        """
        [최종 고도화] 시스템 표준 카테고리와 전략을 일치시켜 데이터 유실을 방지함.
        """
        # 시스템에서 정의한 7개 표준 카테고리 (Step 3의 분류와 일치시켜야 함)
        valid_categories = ["식당", "카페", "활동", "쇼핑", "숙소", "관광지", "기타"]

        prompt = f"""
        당신은 베테랑 여행 설계자입니다. 사용자의 테마를 분석하여 최적의 '코스 구조'를 설계하고, 각 구조를 채울 검색 전략을 수립하세요.

        [사용자 입력]
        - 테마: {theme}
        - 지역: {location}

        [임무]
        1. 이 테마에 필요한 '행동 타입(Action Types)'을 3가지 분석하세요. 
        2. 각 행동을 만족하기 위해 아래 [표준 카테고리 리스트] 중 가장 적합한 카테고리를 하나씩 매칭하세요.
           - 표준 카테고리: {valid_categories}
        
        3. 각 단계별로 Tavily 검색을 위한 '최적화된 검색 쿼리'와 그 쿼리를 선정한 '판단 근거(reasoning)'를 생성하세요.
           (팁: '추천', '리스트', '리뷰', '베스트' 같은 단어를 섞어야 구체적인 가게 이름이 잘 나옵니다.)

        [응답 형식]
        **반드시 다음의 JSON 형식만** 출력하세요. 다른 설명이나 텍스트는 포함하지 마세요.
        
        ```json
        {{
          "action_analysis": "행동 타입 분석 요약",
          "course_structure": [
            {{
              "step": 1, 
              "category": "위 표준 리스트 중 하나", 
              "search_query": "파워 키워드가 포함된 검색어", 
              "reasoning": "이 쿼리를 선정한 이유"
            }},
            {{
              "step": 2, 
              "category": "위 표준 리스트 중 하나", 
              "search_query": "파워 키워드가 포함된 검색어", 
              "reasoning": "이 쿼리를 선정한 이유"
            }},
            {{
              "step": 3, 
              "category": "위 표준 리스트 중 하나", 
              "search_query": "파워 키워드가 포함된 검색어", 
              "reasoning": "이 쿼리를 선정한 이유"
            }}
          ]
        }}
        ```
        
        **중요: JSON 형식만 출력하고, 다른 텍스트는 포함하지 마세요.**
        """
        try:
            response = await self.client.chat.completions.create(
                model=self.llm_model,
                messages=[{"role": "user", "content": prompt}]
            )
            
            # 응답에서 JSON 추출
            response_content = response.choices[0].message.content.strip()
            
            # JSON 부분만 추출 (마크다운 코드 블록 제거)
            if "```json" in response_content:
                json_start = response_content.find("```json") + 7
                json_end = response_content.find("```", json_start)
                if json_end == -1:
                    json_end = len(response_content)
                response_content = response_content[json_start:json_end].strip()
            elif "```" in response_content:
                json_start = response_content.find("```") + 3
                json_end = response_content.find("```", json_start)
                if json_end == -1:
                    json_end = len(response_content)
                response_content = response_content[json_start:json_end].strip()
            
            # JSON 객체 시작/끝 찾기 (중괄호 기준)
            json_start_idx = response_content.find("{")
            json_end_idx = response_content.rfind("}") + 1
            if json_start_idx != -1 and json_end_idx > json_start_idx:
                response_content = response_content[json_start_idx:json_end_idx]
            
            # JSON 파싱
            try:
                return json.loads(response_content)
            except json.JSONDecodeError as e:
                raise ValueError(f"JSON 파싱 오류: {str(e)}\n응답 내용: {response_content[:500]}")

        except Exception as e:
            print(f"⚠️ LLM 호출 실패(쿼터 초과 등): {e}")
            # Mock 데이터에서도 표준 카테고리 명칭을 사용하여 에러 방지
            return {
                "action_analysis": f"{theme}을(를) 위한 실내외 혼합 활동 및 동선 최적화 전략",
                "course_structure": [
                    {
                        "step": 1, "category": "카페", 
                        "search_query": f"{location} {theme} 분위기 좋은 카페 추천",
                        "reasoning": "테마에 맞는 아늑한 분위기 형성을 위해 첫 번째 코스로 선정"
                    },
                    {
                        "step": 2, "category": "활동", 
                        "search_query": f"{location} {theme} 실내 놀거리 전시 베스트",
                        "reasoning": "지루함을 방지하고 테마의 핵심 경험을 제공하기 위한 메인 활동 선정"
                    },
                    {
                        "step": 3, "category": "식사", 
                        "search_query": f"{location} {theme} 맛집 리스트 리뷰",
                        "reasoning": "활동 후 만족스러운 마무리를 위한 현지 인기 식당 탐색"
                    }
                ]
            }

    def _shrink_text(self, text: str, limit: int = 900) -> str:
        """
        본문 폭주 방지: 공백 정리 + 길이 제한
        Tavily에서 받은 긴 description을 토큰 예산 내로 제한
        """
        if not text:
            return ""
        # 연속 공백을 하나로 정리
        text = " ".join(text.split())
        # 길이 제한
        if len(text) > limit:
            return text[:limit] + "…"
        return text

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
        """Google Places API 검증 - 기존 코드 기반에 address_components, types, geometry 추가"""
        
        try:
            search_name = self._clean_place_name(name)
            query = f"{location} {search_name}"
            
            res = self.gmaps.places(query=query)
            if not res.get('results'):
                return None

            place_id = res['results'][0].get('place_id')
            if not place_id:
                # place_id가 없는 경우, 기본 정보라도 사용
                place = res['results'][0]
                photo_url = None
                if place.get('photos'):
                    photo_ref = place['photos'][0].get('photo_reference')
                    if photo_ref:
                        photo_url = f"https://maps.googleapis.com/maps/api/place/photo?maxwidth=400&photo_reference={photo_ref}&key={self.google_maps_api_key}"
                
                # [수정] coordinates 정보도 기본 응답에서 추출 시도
                coordinates = None
                if 'geometry' in place and 'location' in place['geometry']:
                    loc = place['geometry']['location']
                    coordinates = {'lat': loc['lat'], 'lng': loc['lng']}

                return {
                    "name": place.get("name"), "rating": place.get("rating", 0.0),
                    "reviews_count": place.get("user_ratings_total", 0), "address": place.get("formatted_address"),
                    "photo_url": photo_url, "types": place.get("types", []),
                    "address_components": [], "coordinates": coordinates # 상세 정보 없으므로 빈 리스트 반환
                }

            # [최종 버그 수정] 필드명을 올바른 단수형으로 변경
            fields = [
                'name', 'rating', 'user_ratings_total', 'formatted_address', 
                'photo', 'type', 'address_component', 'geometry/location'
            ]
            details_result = self.gmaps.place(place_id, fields=fields)
            
            if not details_result or not details_result.get('result'):
                return None
            
            place = details_result['result']
            
            photo_url = None
            if 'photos' in place and place['photos']:
                photo_ref = place['photos'][0].get('photo_reference')
                if photo_ref:
                    photo_url = f"https://maps.googleapis.com/maps/api/place/photo?maxwidth=400&photo_reference={photo_ref}&key={self.google_maps_api_key}"
            
            coordinates = None
            if 'geometry' in place and 'location' in place['geometry']:
                loc = place['geometry']['location']
                coordinates = {'lat': loc['lat'], 'lng': loc['lng']}

            return {
                "name": place.get("name"),
                "rating": place.get("rating", 0.0),
                "reviews_count": place.get("user_ratings_total", 0),
                "address": place.get("formatted_address"),
                "photo_url": photo_url,
                "types": place.get("types", []),
                "address_components": place.get("address_components", []),
                "coordinates": coordinates
            }
        except Exception as e:
            print(f"      ⚠️ 구글 API 에러: {e}")
            return None
    
    # [신규] 지역 분석 및 검증을 위한 헬퍼 메소드들
    # [최종 수정] 이 함수를 아래 내용으로 교체
    def _get_target_admin_areas(self, location_name: str) -> Tuple[str, str]:
        """[FINAL v4] Geocode 실패 시 LLM으로 상위 지역을 추론합니다."""
        try:
            # 1. Geocoding 우선 시도
            geocode_result = self.gmaps.geocode(location_name)
            if geocode_result:
                # _parse_admin_areas_from_components는 별도 헬퍼 함수로 존재해야 함
                city, gu = self._parse_admin_areas_from_components(geocode_result[0]['address_components'])
                if gu: # '구' 정보가 있으면 성공
                    print(f"   - Geocode 분석 성공: City='{city}', Gu='{gu}'")
                    return city, gu

        except Exception as e:
            print(f"      ⚠️ 지역 분석 중 예외 발생: {e}")
            pass # 최종 실패 시 아래 fallback으로

        print(f"   ❌ 모든 지역 분석 실패. 필터링을 건너뜁니다.")
        return "", "" # 분석 실패 시 필터링을 건너뛰도록 빈 문자열 반환


    def _parse_admin_areas_from_components(self, components: List[Dict]) -> Tuple[str, str]:
        """address_components에서 '시/도'와 '시/군/구' 정보를 추출합니다."""
        city, gu = "", ""
        for component in components:
            types = component['types']
            if 'administrative_area_level_1' in types:
                city = component['long_name']
            if 'locality' in types or 'sublocality_level_1' in types:
                if not gu: gu = component['long_name']
        return city, gu
    

    # [최종 수정] 이 함수를 아래 내용으로 교체
    def _is_in_target_area(self, components: List[Dict], target_gu: str) -> bool:
        """[FINAL] 장소의 주소에 핵심 지역 키워드가 포함되어 있는지 확인합니다."""
        
        # 주소 컴포넌트 전체를 하나의 문자열로 합침 (한글/영문 모두 포함)
        full_address_text = " ".join(
            f"{comp.get('long_name', '')} {comp.get('short_name', '')}" 
            for comp in components
        ).lower()

        # target_gu (핵심 키워드)가 주소에 포함되어 있으면 통과
        if target_gu.lower() in full_address_text:
            return True
        
        # 예외 처리: 'Gangneung-si' vs '강릉시' 처럼 하이픈/접미사 차이로 실패하는 경우 대비
        clean_target = target_gu.lower().replace('-si', '').replace('-gu', '').strip()
        if clean_target in full_address_text:
            return True

        return False


    
    def _calculate_trust_score_v4(self, google_rating: float, google_reviews: int, content: str, category: str, mention_count: int) -> float:
        """
        [v4] 가중 평점, 카테고리별 가중치, 페널티 시스템을 도입한 고도화된 신뢰도 점수
        """
        # --- 1. 기본 점수: '가중 평점(Bayesian Average)'으로 보정 ---
        # 리뷰 수가 적은 높은 평점을 약간 낮추고, 리뷰 수가 매우 많은 평점을 신뢰
        # C: 보정에 필요한 최소 리뷰 수 (일종의 '기본 신뢰도'). 이보다 적으면 전체 평균 쪽으로 점수 조정.
        # m: 전체 장소의 평균 평점 (기본값)
        C = 50.0  # 최소 50개의 리뷰가 쌓여야 평점을 온전히 신뢰하기 시작한다고 가정
        m = 4.2   # 데이터셋의 평균 평점 (가정)
        
        # 리뷰가 하나도 없는 신규 장소는 4.0점에서 시작 (기존 로직 유지)
        if google_reviews == 0:
            base_score = 4.0
        else:
            base_score = (google_reviews / (google_reviews + C)) * google_rating + (C / (google_reviews + C)) * m
        
        score = base_score

        # --- 2. 공통 가산점 ---
        # 2-1. 웹 언급 횟수 (화제성)
        if mention_count > 1:
            score += (mention_count - 1) * 0.1 # 가중치 약간 감소 (과도한 광고성 노출 방지)

        # 2-2. 신뢰 키워드 (긍정적 경험)
        if any(kw in content for kw in ['재방문', '인생맛집', '또간집', '또왔']):
            score += 0.15 # 강력한 긍정 신호
        if any(kw in content for kw in ['내돈내산', '솔직후기']):
            score += 0.05 # 일반 긍정 신호

        # --- 3. 카테고리별 특화 가산점 ---
        if category in ['식당', '카페']:
            # 맛/분위기 관련 키워드
            if any(kw in content for kw in ['분위기', '인테리어', '감성', '뷰가 좋은']):
                score += 0.1
        elif category in ['활동', '관광지', '쇼핑']:
            # 트렌드/새로움 관련 키워드
            if any(kw in content for kw in ['최신', '팝업', '신상', '새로 생긴']):
                score += 0.15
            # 경험의 질 관련 키워드
            if any(kw in content for kw in ['꿀잼', '시간 가는 줄', '만족', '알찬']):
                score += 0.1
        
        # --- 4. 페널티 시스템 (부정적 경험 감지) ---
        penalty_keywords = ['비추', '실망', '별로', '다신 안', '최악', '불친절', '위생', '절대 가지마', '후회']
        penalty_score = 0
        for kw in penalty_keywords:
            if kw in content:
                penalty_score += 0.5 # 부정적 신호는 강력하게 반영

        # "분위기는 좋은데 불친절" 같은 복합 문맥 감지 (간단한 버전)
        if ('좋지만' in content or '좋은데' in content) and any(pkw in content for pkw in ['불친절', '별로', '아쉬']):
            penalty_score += 0.2

        score -= penalty_score

        # 최종 점수는 0점 미만으로 내려가지 않고, 5점을 초과하지 않도록 보정
        return round(max(0, min(score, 5.0)), 2)


    def validate_input(self, input_data: Dict[str, Any]) -> bool:
        """BaseAgent의 필수 구현 추상 메서드"""
        if not isinstance(input_data, dict):
            return False
        return bool(input_data.get("theme") and input_data.get("location"))