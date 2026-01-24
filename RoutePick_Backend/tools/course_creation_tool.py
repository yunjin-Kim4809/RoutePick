"""
코스 제작 Tool
검색된 장소들을 바탕으로 최적의 코스를 생성합니다.
"""

import json
import os
import openai
from typing import Any, Dict, List, Optional
from .base_tool import BaseTool


class CourseCreationTool(BaseTool):
    """LLM을 사용한 맞춤형 코스 제작 Tool"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Args:
            config: Tool 설정 (llm_model, api_key 등)
        """
        super().__init__(
            name="course_creation",
            description="검색된 장소들을 바탕으로 사용자의 선호도와 시간대를 고려한 최적의 코스를 생성합니다.",
            config=config or {}
        )
        
        # LLM 설정
        self.llm_model = self.config.get("llm_model", "gpt-4o-mini")
        # OpenAI API 키 우선순위: openai_api_key > api_key > 환경 변수
        self.api_key = (
            self.config.get("openai_api_key") or 
            self.config.get("api_key") or 
            os.getenv("OPENAI_API_KEY")
        )
        if self.api_key:
            self.client = openai.AsyncOpenAI(api_key=self.api_key)
        else:
            # 환경 변수에서 직접 로드
            self.client = openai.AsyncOpenAI()
        # LLM 클라이언트 초기화 (실제 구현 시 사용)
        # 예: OpenAI, Anthropic, 등
        # self.client = OpenAI(api_key=self.api_key)
    
    async def execute(
        self,
        places: List[Dict[str, Any]],
        user_preferences: Dict[str, Any],
        time_constraints: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        코스 제작 실행
        
        Args:
            places: 검색된 장소 리스트
            user_preferences: 사용자 선호도 {
                "theme": str,  # 테마 (예: "비 오는 날 실내 데이트")
                "group_size": int,  # 인원
                "visit_date": str,  # 방문 일자
                "visit_time": str,  # 방문 시간
                "transportation": str  # 이동 수단
            }
            time_constraints: 시간 제약 {
                "start_time": str,  # 시작 시간
                "end_time": str,  # 종료 시간
                "total_duration": int  # 총 소요 시간 (분)
            }
            
        Returns:
            {
                "success": bool,
                "course": {
                    "places": List[Dict],  # 선정된 장소 리스트
                    "sequence": List[int],  # 방문 순서
                    "estimated_duration": Dict[str, int],  # 각 장소별 예상 체류 시간
                    "course_description": str  # 코스 설명
                },
                "reasoning": str,  # 코스 선정 이유
                "error": Optional[str]
            }
        """
        try:
            if not self.validate_params(places=places, user_preferences=user_preferences):
                return {
                    "success": False,
                    "course": None,
                    "reasoning": "",
                    "error": "필수 파라미터가 누락되었습니다."
                }
            
            if not places:
                return {
                    "success": False,
                    "course": None,
                    "reasoning": "",
                    "error": "장소 리스트가 비어있습니다."
                }
            
            # LLM을 사용하여 코스 생성
            course_result = await self._generate_course_with_llm(
                places, user_preferences, time_constraints
            )
            
            return {
                "success": True,
                "course": course_result.get("course"),
                "reasoning": course_result.get("reasoning", ""),
                "error": None
            }
            
        except Exception as e:
            return {
                "success": False,
                "course": None,
                "reasoning": "",
                "error": str(e)
            }
    
    def get_schema(self) -> Dict[str, Any]:
        """
        Tool 입력 스키마 반환
        
        Returns:
            스키마 딕셔너리
        """
        return {
            "type": "object",
            "properties": {
                "places": {
                    "type": "array",
                    "description": "검색된 장소 리스트",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "description": {"type": "string"},
                            "category": {"type": "string"},
                            "rating": {"type": "number"},
                            "address": {"type": "string"},
                            "tags": {"type": "array", "items": {"type": "string"}}
                        }
                    }
                },
                "user_preferences": {
                    "type": "object",
                    "description": "사용자 선호도",
                    "properties": {
                        "theme": {"type": "string"},
                        "group_size": {"type": "integer"},
                        "visit_date": {"type": "string"},
                        "visit_time": {"type": "string"},
                        "transportation": {"type": "string"}
                    },
                    "required": ["theme"]
                },
                "time_constraints": {
                    "type": "object",
                    "description": "시간 제약 (선택사항)",
                    "properties": {
                        "start_time": {"type": "string"},
                        "end_time": {"type": "string"},
                        "total_duration": {"type": "integer"}
                    }
                }
            },
            "required": ["places", "user_preferences"]
        }
    
    async def _generate_course_with_llm(
        self,
        places: List[Dict[str, Any]],
        user_preferences: Dict[str, Any],
        time_constraints: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        LLM을 사용하여 코스 생성
        
        Args:
            places: 장소 리스트
            user_preferences: 사용자 선호도
            time_constraints: 시간 제약
            
        Returns:
            코스 생성 결과
        """

        prompt = f"""
        # Role
        당신은 현지 지리에 능통하고 모든 장소를 방문해본 여행 가이드입니다. 당신은 효율적인 경로 설계에 능통합니다.
        **당신의 임무는 제공된 장소 리스트에서 최적의 코스를 선택하고 JSON 형식으로 반환하는 것입니다.**
        
        # Context
        사용자의 선호 조건과 제공된 장소 데이터를 바탕으로 최적의 여행 코스를 설계합니다.
        제공된 장소 정보를 바탕으로 작업을 수행하세요. 현재 정보가 부족하더라도 제공된 정보만으로 최선의 코스를 설계하세요.
        
        # Input Data
        - 장소 리스트 : {self._format_places_for_prompt(places)}
        - 사용자 선호 조건{{
            "theme": {user_preferences['theme']},
            "group_size": {user_preferences['group_size']},
            "visit_date": {user_preferences['visit_date']},
            "visit_time": {user_preferences['visit_time']},
            "transportation": {user_preferences['transportation']}
        }}

        # Constraints
        1. **최우선 규칙: 사용자가 저장한 장소(⭐ [사용자가 저장한 장소 - 최우선 고려] 표시가 있는 장소)는 반드시 최우선적으로 고려해야 합니다.**
           - 저장된 장소는 이미 테마와 위치 필터링을 통과했으므로, 사용자의 의도에 부합하는 장소입니다.
           - 저장된 장소가 사용자의 테마와 위치 조건에 부합한다면, 반드시 코스에 포함시켜야 합니다.
           - 저장된 장소를 포함하는 것이 다른 제약 조건(거리, 시간 등)과 충돌하더라도, 가능한 한 포함하도록 노력하세요.
        2. 제공된 [위치 좌표(위도, 경도)] 데이터를 기반으로 장소 간의 실제 물리적 거리를 계산하여 코스를 짤 것.
        3. 당신의 배경지식보다 입력된 좌표 정보가 서로 가까운 장소들을 우선적으로 그룹화할 것.
        4. 추천 신뢰도(Trust Score)가 높은 장소를 우선적으로 고려하되, 지리적 동선 효율성을 해치지 않는 범위 내에서 선택할 것.
        5. 각 코스 간 이동 거리는 30분 이내일 것. (좌표 데이터를 참고하여 보수적으로 판단)
        6. 도보 외의 교통 수단의 사용 빈도를 최소화할 것. 단, 환승은 사용 빈도 계산에서 제외한다. 도보와 교통 수단의 이동 시간 차이가 20분 이내이면 도보를 선택한다.
        7. 이전에 방문한 장소를 다시 지나지 않을 것.
        8. 장소에 현재 인원이 모두 수용 가능할 것.
        9. 장소가 방문 일자에 운영중임을 확인할 것. 입력된 정보가 없을 시 보수적으로 판단한다.
        10. 음식점, 카페 등을 코스 중간마다 배치할 것.

        # Task Workflow
        1. **최우선 단계: 사용자가 저장한 장소(⭐ [사용자가 저장한 장소 - 최우선 고려] 표시)를 먼저 선정합니다.**
           - 저장된 장소는 이미 테마와 위치 필터링을 통과했으므로, 가능한 한 모두 포함하도록 노력하세요.
           - 저장된 장소가 여러 개인 경우, 모두 포함하거나 최대한 많이 포함하세요.
        2. 저장된 장소를 포함한 상태에서, 사용자의 테마와 장소의 특징을 대조하여 추가로 적합한 장소들을 선정합니다.
        3. 이동 거리를 최소화하는 순서로 배열합니다. (저장된 장소를 포함한 전체 코스 기준)
        4. 선정된 순서가 실제 방문 가능 시간(영업시간) 내에 있는지 검증합니다.
        5. 모든 논리적 검증이 끝나면 최종 JSON을 출력합니다.
        
        **중요: 저장된 장소를 코스에 포함시키는 것이 이 작업의 최우선 목표입니다.**

        # IMPORTANT: Output Format
        **당신은 반드시 이 작업을 수행해야 합니다. 작업을 거부하거나 설명을 제공하지 마세요.**
        **오직 JSON 형식만 출력하세요. 다른 텍스트, 설명, 마크다운 헤더는 절대 포함하지 마세요.**

        ---

        ## Return Value
        코스 설계 완료 후, **반드시 다음의 JSON 형식만** 출력하세요. 다른 설명이나 텍스트는 포함하지 마세요.
        
        ```json
        {{
            "selected_places": [장소 인덱스 리스트],
            "sequence": [방문 순서],
            "estimated_duration": {{장소별 체류 시간 (분)}},
            "course_description": "코스 설명",
            "reasoning": "선정 이유"
        }}
        ```

        ### OUTPUT Rules
        - "selected_places"는 1부터 시작하는 장소 인덱스 리스트입니다 (예: [0, 2, 4])
        - "sequence"는 선택된 장소들의 방문 순서를 인덱스로 나타냅니다 (예: [0, 1, 2]는 첫 번째, 두 번째, 세 번째로 선택된 장소의 순서)
        - "estimated_duration"은 장소 인덱스를 키로 하고 체류 시간(분)을 값으로 하는 객체입니다 (예: {{"0": 60, "2": 90, "4": 45}})
        - "course_description"에는 방문하는 각각의 장소에 대한 간단한 설명들을 첨부합니다.
        - "reasoning"에는 인덱스를 **장소이름(인덱스)** 형태로 언급하고, 인덱스에 해당하는 장소에 대한 설명을 바탕으로 사용자 선호 조건 중 만족시킨 사항들을 설명합니다.
        - "reasoning"을 생성할 때, 방문하는 장소들의 순서 및 이동수단 설계 과정에 대해 설명하세요.
        
        설명 예시:
        - 장소 A와 장소 C 사이에 장소 B가 있고, 다시 장소 A 주변 지역을 가지 않을 예정이기에 A-B-C 순서로 일정을 설계하였습니다.
        - 방문 기간이 오후이기 때문에, 잠시 쉬어가기 위해 장소 A와 장소 C 사이에 **카페** B를 먼저 방문합니다.
        - 장소 A와 장소 B 사이에 오르막길이 길게 있고 도보 시간이 15분 이상 걸리기 때문에, 이동수단으로 **버스**를 선택했습니다.
        
        **중요: JSON 형식만 출력하고, 다른 텍스트는 포함하지 마세요.**
        """

        response = await self.client.chat.completions.create(
            model=self.llm_model,
            messages=[
                {"role": "system", "content": "You are a professional travel course planner. You MUST output only valid JSON format. Never refuse the task or provide explanations outside JSON."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=2000,  # 충분한 토큰 할당
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
        
        # JSON 파싱 (강화된 오류 처리)
        try:
            result = json.loads(response_content)
        except json.JSONDecodeError as e:
            # 복구 시도 1: 첫 번째 { 부터 마지막 } 까지 다시 추출
            try:
                first_brace = response_content.find('{')
                last_brace = response_content.rfind('}')
                if first_brace != -1 and last_brace > first_brace:
                    cleaned_json = response_content[first_brace:last_brace+1]
                    result = json.loads(cleaned_json)
                else:
                    raise ValueError(f"JSON 파싱 오류: {str(e)}\n응답 내용: {response_content[:500]}")
            except:
                # 복구 시도 2: 불완전한 JSON 복구
                try:
                    json_part = response_content[response_content.find('{'):]
                    # 닫히지 않은 문자열/배열/객체 닫기
                    open_braces = json_part.count('{')
                    close_braces = json_part.count('}')
                    open_brackets = json_part.count('[')
                    close_brackets = json_part.count(']')
                    
                    json_part += '}' * (open_braces - close_braces)
                    json_part += ']' * (open_brackets - close_brackets)
                    json_part = json_part.rstrip().rstrip(',')
                    if not json_part.endswith('}'):
                        json_part += '}'
                    
                    result = json.loads(json_part)
                except:
                    # 모든 복구 시도 실패
                    raise ValueError(f"JSON 파싱 오류: {str(e)}\n응답 내용: {response_content[:500]}\n\nLLM이 JSON 형식으로 응답하지 않았습니다. 작업을 거부했거나 다른 형식으로 응답한 것 같습니다.")

        # ============================================================
        # [최종 버그 수정] LLM이 반환한 인덱스 유효성 검증
        # ============================================================
        
        # 1. selected_places 인덱스 검증
        valid_selected_indices = []
        if "selected_places" in result:
            for index in result["selected_places"]:
                # 인덱스가 정수이고, 유효한 범위 내에 있는지 확인
                if isinstance(index, int) and 0 <= index < len(places):
                    valid_selected_indices.append(index)
                else:
                    print(f"   ⚠️ LLM이 잘못된 장소 인덱스({index})를 반환하여 무시합니다.")
        
        if not valid_selected_indices:
            raise ValueError("LLM이 유효한 장소를 하나도 선택하지 않았습니다.")

        # 2. sequence 인덱스 검증 (selected_places의 인덱스를 참조하므로 주의)
        valid_sequence = []
        if "sequence" in result:
            for seq_index in result["sequence"]:
                # sequence의 인덱스가 valid_selected_indices의 유효한 범위 내에 있는지 확인
                if isinstance(seq_index, int) and 0 <= seq_index < len(valid_selected_indices):
                    valid_sequence.append(seq_index)
                else:
                    print(f"   ⚠️ LLM이 잘못된 순서 인덱스({seq_index})를 반환하여 무시합니다.")
        
        # 만약 sequence가 잘못되었으면, 그냥 selected 순서대로라도 복구
        if not valid_sequence or len(valid_sequence) != len(valid_selected_indices):
            print(f"   ⚠️ LLM이 반환한 sequence가 유효하지 않아, 선택된 순서로 복구합니다.")
            valid_sequence = list(range(len(valid_selected_indices)))

        # 3. estimated_duration 키 검증
        valid_duration = {}
        if "estimated_duration" in result and isinstance(result["estimated_duration"], dict):
            for key, value in result["estimated_duration"].items():
                try:
                    # 키를 정수로 변환하여 유효한 인덱스인지 확인
                    index_key = int(key)
                    if index_key in valid_selected_indices:
                        valid_duration[str(index_key)] = value
                except (ValueError, TypeError):
                    continue # 키가 숫자가 아니면 무시

        # 검증된 인덱스를 사용하여 최종 결과 생성
        selected_places = [places[i] for i in valid_selected_indices]
        
        return {
            "course": {
                "places": selected_places,
                "sequence": valid_sequence,
                "estimated_duration": valid_duration,
                "course_description": result.get("course_description", "")
            },
            "reasoning": result.get("reasoning", "")
        }
    
    
    def _format_places_for_prompt(self, places: List[Dict[str, Any]]) -> str:
        """
        프롬프트용 장소 정보 포맷팅
        
        Args:
            places: 장소 리스트 (name, category, coordinates, rating, trust_score, address, source_url, map_url 포함)
            
        Returns:
            포맷팅된 문자열
        """
        formatted = []
        for i, place in enumerate(places, 1):
            # 필수 정보: 이름 및 카테고리
            info = f"[{i}] {place.get('name', 'Unknown')}"
            if place.get('category'):
                info += f" ({place['category']})"
            
            # 저장된 장소 플래그 표시 (우선순위 표시)
            if place.get('is_saved_place'):
                info += " ⭐ [사용자가 저장한 장소 - 최우선 고려]"
            
            # [추가] 좌표 정보를 LLM이 읽을 수 있게 텍스트로 포함
            coords = place.get('coordinates')
            if coords:
                info += f" (위치: {coords.get('lat')}, {coords.get('lng')})"

            # 점수 정보 (평점 및 신뢰도)
            scores = []
            if place.get('rating'):
                scores.append(f"평점: {place['rating']}")
            if place.get('trust_score'):
                scores.append(f"신뢰도: {place['trust_score']}")
            
            if scores:
                info += f" - {' / '.join(scores)}"
                
            # 주소 정보
            if place.get('address'):
                info += f"\n   주소: {place['address']}"
                
            # 링크 정보 (출처 및 지도)
            links = []
            if place.get('source_url'):
                links.append(f"추천 근거: {place['source_url']}")
            if place.get('map_url'):
                links.append(f"지도: {place['map_url']}")
                
            if links:
                info += f"\n   링크: {' | '.join(links)}"
                
            formatted.append(info)
            
        return "\n\n".join(formatted)

