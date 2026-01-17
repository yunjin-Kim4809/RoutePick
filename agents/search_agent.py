import json
import asyncio
import os
import random 
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
        print(f"📡 [Step 2] Tavily를 통해 방대한 실시간 데이터 수집 중... (60개 후보 탐색)")

        tasks = [
            self.search_tool.execute(query=step['search_query'], max_results=20) 
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
        print(f"📝 [Step 3-2] LLM이 60개 원문 전체를 전수 조사 중...")
        
        # [Step 3 수정] 이름과 카테고리를 함께 추출
        # 수정된 추출 함수 호출
        refined_data = await self._extract_place_entities_with_source(all_raw_data, location)

        #  LLM의 성실도 체크
        print(f"   ✅ LLM이 60개 데이터에서 발굴한 유니크 장소: {len(refined_data)}개")

        # 인기도(언급 횟수) 계산
        # 어떤 장소가 60개 검색 결과 중 여러 번 등장했는지 카운트합니다.
        mention_counts = {}
        for item in refined_data:
            name = item.get('name')
            mention_counts[name] = mention_counts.get(name, 0) + 1

        # 4. Google Maps 기반 검증
        category_buckets = {} # 카테고리별로 장소를 담을 바구니
        seen_names = set() # 중복 제거용

        for item in refined_data:
            # 이제 name뿐만 아니라 category도 item 안에 들어있습니다.
            place_name = item.get('name')
            place_category = item.get('category', '기타') # 기본값 설정
            
            clean_name = self._clean_place_name(place_name)
            google_info = self._get_google_data(clean_name, location)
    
            # 카테고리에 따른 유연한 필터링
            is_valid = False
            cat = place_category
            
            if google_info:
                g_rating = google_info['rating']
                # [강력 처방] 평점이 0.1~3.0 사이라면 '진짜 나쁜 곳' 혹은 '부동산'임. 가차없이 커트!
                if 0.1 <= g_rating < 3.0:
                    print(f"   - [Hard Cut] {google_info['name']}: 평점 {g_rating} (품질 미달)")
                    continue

                if cat in ['식당', '카페']:
                    if g_rating >= 4.0: is_valid = True
                else:
                    is_valid = True # 평점 0.0(신규) 이거나 3.0 이상인 활동/관광지는 통과
            
            elif cat in ['활동', '관광지', '쇼핑']:
                # 구글에 없어도 LLM이 추출했다면 '최신 팝업'일 가능성이 높으므로 통과
                is_valid = True
                google_info = {"name": place_name, "rating": 0.0, "reviews_count": 0, "address": "주소 정보 확인 필요"}
            
            
            if is_valid:
                g_name = google_info['name']
                if g_name in seen_names: continue

                # all_raw_data에서 이 장소의 원본 텍스트를 찾아옵니다.
                # item['source_url']과 일치하는 원문을 검색
                original_desc = ""
                for raw in all_raw_data:
                    if raw['url'] == item.get('source_url'):
                        # title과 snippet을 조합하여 원본 텍스트 재구성
                        original_desc = f"{raw.get('title', '')} {raw.get('snippet', '')}".strip()
                        break
 
                # [V3 업그레이드] 언급 횟수(Mentions)를 점수 계산기에 전달
                trust_score = self._calculate_trust_score_v3(
                    google_info['rating'], 
                    google_info['reviews_count'], 
                    original_desc, 
                    cat,
                    mention_counts.get(place_name, 1) # 언급 횟수 추가
                )

                # 🔗 URL 인코딩 처리 (공백을 +로 치환하여 클릭 가능하게)
                encoded_name = g_name.replace(" ", "+")
                map_url = f"https://www.google.com/maps/search/?api=1&query={encoded_name}+{location.replace(' ', '+')}"

                #print(f"   - [Keep] {google_info['name']} (평점: {google_info['rating']})")
                
                place_obj = {
                    "name": g_name,
                    "category": cat,
                    "rating": google_info['rating'],
                    "trust_score": trust_score,
                    "address": google_info['address'],
                    "source_url": item.get('source_url'),
                    "map_url": map_url
                }

                # [핵심 추가] 바구니에 담기
                if cat not in category_buckets:
                    category_buckets[cat] = []
                category_buckets[cat].append(place_obj)

                seen_names.add(g_name)


        # ============================================================
        # 5. [라운드 로빈 선발] 다양성 보장 로직
        # ============================================================
        final_pool = []
        TOTAL_LIMIT = 15

        # 각 카테고리 내에서 점수 순으로 미리 정렬
        for cat in category_buckets:
            category_buckets[cat].sort(key=lambda x: x['trust_score'], reverse=True)

        # 1차 목표: 전략 카테고리 (Step 2에서 설계한 3개)
        strategic_cats = [step['category'] for step in strategy['course_structure']]
        # 2차 목표: 나머지 카테고리
        other_cats = [c for c in category_buckets.keys() if c not in strategic_cats]
        
        # 전체 순회 순서: [전략1, 전략2, 전략3, 기타1, 기타2...]
        ordered_cats = strategic_cats + other_cats

        # ❗ [핵심] 한 바퀴 돌 때마다 '딱 한 개씩'만 뽑습니다.
        while len(final_pool) < TOTAL_LIMIT:
            added_in_this_round = False
            
            for cat in ordered_cats:
                if len(final_pool) >= TOTAL_LIMIT: break
                
                if cat in category_buckets and category_buckets[cat]:
                    final_pool.append(category_buckets[cat].pop(0))
                    added_in_this_round = True
            
            # 모든 바구니가 비었으면 종료
            if not added_in_this_round:
                break

        # 중복 제거 (이름 기준)
        seen = set()
        unique_final_pool = []
        for p in final_pool:
            if p['name'] not in seen:
                unique_final_pool.append(p)
                seen.add(p['name'])
        
        final_pool = unique_final_pool[:TOTAL_LIMIT]
        
        # SearchAgent.execute()의 리턴값 다음 에이전트에게 줄 '최종 패키지'
        return {
            "success": True,
            "agent_name": self.name,
            "action_analysis": strategy.get('action_analysis'),
            "candidate_pool": final_pool,
            "user_intent": {
                "course_structure": strategy.get('course_structure'),
                # 여기에 reasoning 정보가 step별로 포함되어 있어 데이터가 휘발되지 않음
                "raw_theme": theme,
                "location": location
            }
        }
    

    # async def _extract_place_entities_with_source(self, raw_data: List[Dict], location: str) -> List[Dict]:
    #     """
    #     [범용 고도화] 어떤 테마에서도 60개 데이터를 샅샅이 뒤져 최대한 많은 장소를 발굴함.
    #     배치 처리로 토큰 제한 문제 해결.
    #     """
    #     if not raw_data: return []
        
    #     # 배치 크기 설정 (토큰 제한 고려: gpt-4o-mini는 8192 토큰 제한이므로 6-8개씩 처리)
    #     BATCH_SIZE = 6
    #     all_results = []
        
    #     # 데이터를 배치로 나누기
    #     batches = [raw_data[i:i + BATCH_SIZE] for i in range(0, len(raw_data), BATCH_SIZE)]
    #     total_batches = len(batches)
        
    #     print(f"   📦 총 {len(raw_data)}개 데이터를 {total_batches}개 배치로 나눠 처리합니다...")
        
    #     # 각 배치를 순차적으로 처리
    #     for batch_idx, batch_data in enumerate(batches, 1):
    #         print(f"   🔄 배치 {batch_idx}/{total_batches} 처리 중... ({len(batch_data)}개 데이터)")
            
    #         try:
    #             batch_results = await self._process_batch(batch_data, location, batch_idx, total_batches)
    #             if batch_results:
    #                 all_results.extend(batch_results)
    #         except Exception as e:
    #             print(f"   ⚠️  배치 {batch_idx} 처리 중 오류: {e}")
    #             continue
        
    #     # 중복 제거 (같은 장소명, 같은 URL)
    #     unique_results = []
    #     seen = set()
    #     for item in all_results:
    #         key = (item.get('name', ''), item.get('source_url', ''))
    #         if key not in seen and key[0]:  # 이름이 있는 경우만
    #             seen.add(key)
    #             unique_results.append(item)
        
    #     return unique_results
    
    async def _extract_place_entities_with_source(self, raw_data: List[Dict], location: str) -> List[Dict]:
        """
        [병렬 고도화] 60개 데이터를 배치로 나눠 '동시에' LLM에게 전달합니다.
        정확도는 유지하고 속도는 10배 향상시킵니다.
        """
        if not raw_data: return []
        
        # 1. 배치 크기 설정
        BATCH_SIZE = 6
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
        """Google Places API 검증 (이름 정제 로직 포함) - 지역 검증 추가"""
        try:
            # [수정] 지저분한 이름을 청소하고 검색
            search_name = self._clean_place_name(name)
            query = f"{location} {search_name}"
            
            #print(f"   🔎 구글 검색 시도: '{query}'") # 어떤 키워드로 구글에 물어보는지 확인용
            
            res = self.gmaps.places(query=query)
            if res.get('results'):
                # 지역 검증: 주소에 해당 지역이 포함되어 있는지 확인
                location_normalized = self._normalize_location(location)
                
                for place in res.get('results', []):
                    address = place.get("formatted_address", "")
                    
                    # 주소에 해당 지역이 포함되어 있는지 확인
                    if self._is_location_match(address, location_normalized, location):
                        return {
                            "name": place.get("name"), # 구글이 확인해준 진짜 가게 이름
                            "rating": place.get("rating", 0.0),
                            "reviews_count": place.get("user_ratings_total", 0),
                            "address": address
                        }
                
                # 해당 지역에 맞는 결과가 없으면 첫 번째 결과도 사용하지 않음 (None 반환)
                # 이렇게 하면 잘못된 지역의 장소가 제외됨
                return None
        except Exception as e:
            print(f"      ⚠️ 구글 API 에러: {e}")
            return None
        return None
    
    def _normalize_location(self, location: str) -> str:
        """지역명 정규화 (서울특별시 -> 서울, 부산광역시 -> 부산)"""
        # 한국의 주요 도시 정규화
        location_map = {
            "서울특별시": "서울",
            "서울시": "서울",
            "부산광역시": "부산",
            "부산시": "부산",
            "대구광역시": "대구",
            "대구시": "대구",
            "인천광역시": "인천",
            "인천시": "인천",
            "광주광역시": "광주",
            "광주시": "광주",
            "대전광역시": "대전",
            "대전시": "대전",
            "울산광역시": "울산",
            "울산시": "울산",
            "경기도": "경기",
            "강원도": "강원",
            "충청북도": "충북",
            "충청남도": "충남",
            "전라북도": "전북",
            "전라남도": "전남",
            "경상북도": "경북",
            "경상남도": "경남",
        }
        
        normalized = location_map.get(location, location)
        # 마지막으로 공백 제거
        return normalized.strip()
    
    def _is_location_match(self, address: str, normalized_location: str, original_location: str) -> bool:
        """주소가 해당 지역에 속하는지 확인"""
        if not address:
            return False
        
        # 주소를 소문자로 변환하여 비교 (대소문자 무시)
        address_lower = address.lower()
        normalized_lower = normalized_location.lower()
        original_lower = original_location.lower()
        
        # 한국의 주요 도시별 검증 (특수 케이스 - 제외 도시 먼저 확인)
        # 예: "서울"인데 주소에 "부산"이나 "경주"가 포함되어 있으면 False
        exclusion_map = {
            "서울": ["부산", "대구", "인천", "광주", "대전", "울산", "경주", "제주"],
            "부산": ["서울", "대구", "인천", "광주", "대전", "울산", "경주", "제주"],
            "경주": ["서울", "부산", "대구", "인천", "광주", "대전", "울산", "제주"],
        }
        
        # 제외 도시가 주소에 포함되어 있으면 False 반환
        if normalized_location in exclusion_map:
            for excluded_city in exclusion_map[normalized_location]:
                if excluded_city.lower() in address_lower:
                    return False
        
        # 정규화된 지역명 또는 원본 지역명이 주소에 포함되어 있는지 확인
        if normalized_lower in address_lower or original_lower in address_lower:
            return True
        
        # 지역명이 주소에 포함되어 있지 않으면 False
        return False
    
    def _calculate_trust_score_v3(self, google_rating: float, google_reviews: int, content: str, category: str, mention_count: int) -> float:
        """
        [V3] 인기도(Mention Count)가 반영된 최종 신뢰도 점수
        """
        # 1. 기본 점수 (평점 0.0인 최신 장소는 4.0점에서 시작)
        score = google_rating if google_rating > 0 else 4.0
        
        # 2. 보조 지표 1: 구글 리뷰 수 (공식 인기도)
        if google_reviews > 500: score += 0.2
        elif google_reviews > 100: score += 0.1
    
        # 3. 보조 지표 2: 웹 언급 횟수 (트렌드 인기도)
        # 여러 블로그/사이트에서 공통으로 발견될수록 가산점 부여 (최대 0.4)
        if mention_count > 1:
            score += (mention_count - 1) * 0.15

        # 4. 보조 지표 3: 키워드 가산점
        trust_keywords = ['내돈내산', '솔직후기', '분위기', '친절']
        for kw in trust_keywords:
            if kw in content: score += 0.05
            
        # 활동/관광지 전용 트렌드 키워드
        if category in ['활동', '쇼핑', '관광지']:
            if any(kw in content for kw in ['최신', '팝업', '오픈', '핫플']):
                score += 0.1

        return round(min(score, 5.0), 2)


    def validate_input(self, input_data: Dict[str, Any]) -> bool:
        """BaseAgent의 필수 구현 추상 메서드"""
        if not isinstance(input_data, dict):
            return False
        return bool(input_data.get("theme") and input_data.get("location"))