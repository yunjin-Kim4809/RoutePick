"""
코스 제작 Tool
검색된 장소들을 바탕으로 최적의 코스를 생성합니다.
"""

import json
import os
import openai
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_core.tools import tool
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from typing import Any, Dict, List, Optional
from .base_tool import BaseTool
from .google_maps_tool import GoogleMapsTool
from config.config import Config

load_dotenv()

config = Config.get_agent_config()
config["api_key"] = os.getenv("GOOGLE_MAPS_API_KEY") 
maptool = GoogleMapsTool(config=config)

@tool
async def check_routing(
        places: List[Dict[str, Any]],
        origin: Optional[Dict[str, Any]] = None,
        destination: Optional[Dict[str, Any]] = None,
        mode: str = "transit",  # 'driving', 'walking', 'transit', 'bicycling'
    ) -> Dict[str, Any]:
    """
    주어진 장소들에 대해 경로 최적화를 실행합니다.
    Args:
            places: 장소 정보 리스트 (각 장소는 name, address, coordinates 등을 포함)
            origin: 출발지 (선택사항, 없으면 places의 첫 번째 항목)
            destination: 도착지 (선택사항, 없으면 places의 마지막 항목)
            mode: 이동 수단 ('driving', 'walking', 'transit', 'bicycling')
            optimize_waypoints: 경유지 순서 최적화 여부
    """

    return await maptool.execute(
        places=places,
        origin=origin,
        destination=destination,
        mode=mode
    )

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
        self.tools = [check_routing]
    
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
                        "transportation": {"type": "string"},
                        "budget": {"type": "string"}
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
        time_constraints: Optional[Dict[str, Any]],
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
        for i, place in enumerate(places):
            place['original_index'] = i
        
        system_instruction = """
            # Role
            당신은 현지 지리에 능통하고 모든 장소를 방문해본 여행 가이드입니다. 당신은 효율적인 경로 설계에 능통합니다.
            **당신의 임무는 제공된 장소 리스트에서 최적의 코스를 선택하고 JSON 형식으로 반환하는 것입니다.**

            # Context
            사용자의 선호 조건과 제공된 장소 데이터를 바탕으로 최적의 여행 코스를 설계합니다.
            제공된 장소 정보를 바탕으로 작업을 수행하세요. 현재 정보가 부족하더라도 제공된 정보만으로 최선의 코스를 설계하세요.

            # Input Data
            - 장소 리스트 : {places}
            - 사용자 선호 조건 : {user_preferences}
            - 활동 시간 제약 : {time_constraints}
            **중요사항** : 각 장소에는 original_index 필드가 포함되어 있습니다. 모든 인덱스 참조(sequence, reasoning 등)는 반드시 이 필드 값을 기준으로 작성하십시오.

            # Constraints
            1. **최우선 규칙: 사용자가 저장한 장소(⭐ [사용자가 저장한 장소 - 최우선 고려] 표시가 있는 장소)는 반드시 최우선적으로 고려해야 합니다.**
            - 저장된 장소는 이미 테마와 위치 필터링을 통과했으므로, 사용자의 의도에 부합하는 장소입니다.
            - 저장된 장소가 사용자의 테마와 위치 조건에 부합한다면, 반드시 코스에 포함시켜야 합니다.
            - 저장된 장소를 포함하는 것이 다른 제약 조건(거리, 시간 등)과 충돌하더라도, 가능한 한 포함하도록 노력하세요.
            2. 장소 간의 실제 거리 및 이동 시간을 계산할 때는 항상 'check_routing' tool을 사용하세요.
            - `check_routing`의 `places` 파라미터에는 입력 데이터로 제공된 '장소 리스트'의 객체들을 전달하되, 각 장소의 위치 정보는 반드시 `{{"coordinates": {{"lat": 위도숫자, "lng": 경도숫자}}}}` 형식을 포함해야 합니다.
            - 입력 데이터에 'latitude', 'longitude'로 되어 있더라도 도구 호출 시에는 반드시 'lat', 'lng' 키를 사용하세요.
            3. 제공된 [위치 좌표(위도, 경도)] 데이터를 기반으로 장소 간의 실제 물리적 거리를 계산하여 코스를 짜야 합니다.
            4. 당신의 배경지식보다 입력된 좌표 정보가 서로 가까운 장소들을 우선적으로 그룹화하세요.
            5. 추천 신뢰도(Trust Score)가 높은 장소를 우선적으로 고려하되, 지리적 동선 효율성을 해치지 않는 범위 내에서 선택하세요.
            6. 각 코스 간 이동 거리는 30분 이내여야 합니다. (좌표 데이터를 참고하여 보수적으로 판단)
            7. 도보 외의 교통 수단의 사용 빈도를 최소화하세요. 단, 환승은 사용 빈도 계산에서 제외하세요. 도보와 교통 수단의 이동 시간 차이가 20분 이내이면 도보를 선택하세요.
            8. 이전에 방문한 장소를 다시 지나지 않도록 경로를 설계하세요.
            9. 장소에 현재 인원이 모두 수용 가능해야 합니다.
            10. 장소가 방문 일자에 운영중임을 확인하세요. 입력된 정보가 없을 시 보수적으로 판단하세요.
            11. 사용자의 동선상 식사와 휴식이 적절히 교차되도록 설계하세요.
            - [동일 카테고리 식음료 시설 연속 방문 제한]: '식당'과 '카페' 카테고리는 각각 연속적으로 배치하지 마세요.
            - 금지 예시: [식당 -> 식당] (X), [카페 -> 카페] (X)
            - 허용 예시: [식당 -> 카페] (O), [카페 -> 식당] (O)

            # Task Workflow
            1. **최우선 단계: 사용자가 저장한 장소(⭐ [사용자가 저장한 장소 - 최우선 고려] 표시)를 먼저 선정합니다.**
            - 저장된 장소는 이미 테마와 위치 필터링을 통과했으므로, 가능한 한 모두 포함하도록 노력하세요.
            - 저장된 장소가 여러 개인 경우, 모두 포함하거나 최대한 많이 포함하세요.
            2. 저장된 장소를 포함한 상태에서, 사용자의 테마와 장소의 특징을 대조하여 추가로 적합한 장소들을 선정합니다.
            3. 선정된 코스에서 '식당' 카테고리가 연속되거나 '카페' 카테고리가 연속되는 구간이 있는지 확인합니다. 만약 그러한 구간이 있다면 중간에 다른 카테고리인 장소를 넣어 순서를 재조정합니다.
            4. 이동 거리를 최소화하는 순서로 배열합니다. (저장된 장소를 포함한 전체 코스 기준)
            5. 인덱스 매핑 확인: 최종 답변 전, check_routing이 제안한 장소 이름들이 원본 리스트의 어떤 original_index와 매칭되는지 내부적으로 표를 작성하여 대조하세요.
            6. 선정된 순서가 실제 방문 가능 시간(영업시간) 내에 있는지 검증합니다.
            7. 모든 논리적 검증이 끝나면 최종 JSON을 출력합니다.
            
            **중요: 저장된 장소를 코스에 포함시키는 것이 이 작업의 최우선 목표입니다.**

            # IMPORTANT: Output Format
            **당신은 반드시 이 작업을 수행해야 합니다. 작업을 거부하거나 설명을 제공하지 마세요.**
            **오직 JSON 형식만 출력하세요. 다른 텍스트, 설명, 마크다운 헤더는 절대 포함하지 마세요.**

            ---

            ## Return Value
            코스 설계 완료 후, **반드시 다음의 JSON 형식만** 출력하세요. (LangChain Agent의 Final Answer로 이 형식을 사용하세요)

            ```json
            {{
                "selected_places": [장소 리스트]
                "sequence": [방문 순서],
                "estimated_duration": {{장소별 체류 시간 (분)}},
                "course_description": "코스 설명",
                "reasoning": "선정 이유"
            }}
            
            ### OUTPUT Rules
            "selected_places"는 '장소 리스트'를 그대로 반환합니다.
            "sequence"의 정의: 사용자가 최종적으로 방문하게 될 장소들의 원본 리스트(Original Input List)를 기준으로, 방문 순서대로 나열된 [original_index]의 리스트입니다. 최솟값은 0입니다.
            - check_routing 툴이 반환한 결과의 순서가 인덱스가 아닙니다.
            - 툴 결과에 포함된 '장소 이름'을 처음 입력받은 '장소 리스트'에서 찾아, 해당 장소가 위치했던 원래의 인덱스 번호를 추출하세요.
            - **절대 주의**: 이는 '선택된 장소 중 몇 번째인가'를 나타내는 순번이 아니라, 입력받은 '장소 리스트'에서의 **절대적인 위치 번호**입니다.
            - 예: 리스트의 5번째에 있던 장소(index 4)를 첫 번째로 방문한다면, sequence의 첫 번째 값은 무조건 4여야 합니다.
            "estimated_duration"은 sequence에 따른 장소 인덱스를 키로 하고 체류 시간(분)을 값으로 하는 객체입니다.
            "course_description" 및 "reasoning" 작성 규칙:
            - [필수 엄수]: sequence 리스트에 나열된 인덱스 순서대로 각 장소의 설명을 작성하세요. 예: sequence가 [3, 0]이라면, '장소 리스트'의 3번 원소 설명 후 0번 원소 설명을 작성합니다.
            - [인덱스 직접 참조]: 장소를 언급할 때 반드시 '장소 이름(인덱스)' 형식을 유지하되, 이때 인덱스는 sequence에 포함된 숫자를 수정 없이 그대로(As-is) 사용하세요. (절대 -1을 하거나 숫자를 바꾸지 마십시오.)
            - [구조적 작성]: reasoning은 반드시 다음 형식을 엄수하세요: "1. [인덱스 N] 장소이름: (설명...)" 형식으로 작성하여, 숫자가 sequence의 원소와 1:1로 대응됨을 시각적으로 명증하세요.
            - [순차적 논리]: sequence의 인덱스 순서에 따라 장소 방문 목적과 사용자 선호 조건 만족 여부를 설명하세요.
            - [식사 및 휴식 설계]: 식사(식당)와 디저트(카페)의 순서를 어떻게 고려했는지, 혹은 동일 카테고리 연속 방문을 피하기 위해 중간에 어떤 장소를 배치했는지 그 설계 의도를 포함하세요.
            - [이동 수단]: 각 장소 사이(인덱스 간 이동)의 이동 수단 선택 이유와 경로 설계 과정을 상세히 포함하세요.
            - [전수 포함 규칙 (Mandatory)]: sequence 리스트에 포함된 모든 인덱스를 하나도 빠짐없이 순서대로 언급해야 합니다. 특정 장소를 생략하거나 건너뛰는 것은 허용되지 않습니다.
            - [흐름의 완결성]: 첫 번째 장소부터 마지막 장소까지, sequence의 인덱스 이동 경로를 따라가며 전체 코스를 설명하세요. 각 장소 사이의 연결 고리(이동 수단, 소요 시간, 선택 이유)를 빠짐없이 서술해야 합니다.
            - [최종 정합성 체크]: 모든 답변 작성을 마친 후, sequence 리스트의 총 개수($N$)와 course_description에 나열된 장소의 개수, 그리고 reasoning에서 번호 매겨진 항목의 개수가 모두 $N$으로 일치하는지 숫자를 직접 세어 확인하십시오. 하나라도 다르면 처음부터 다시 구성하십시오.
            **주의 사항 (Critical)**:
            - **[매핑 루프]**: 작성 시 반드시 "이 장소의 original_index가 무엇인가?"를 먼저 확인하고 쓰십시오.
            - **[인덱스 고정]**: '장소이름(인덱스)' 표기 시, 괄호 안의 숫자는 오직 sequence 리스트에 포함된 해당 장소의 original_index여야 합니다.
            - **[전수 검증]**: reasoning의 항목 개수가 sequence 리스트의 길이와 다를 경우, 이는 논리적 결함으로 간주되어 작업이 실패합니다.
            - **[연산 금지]**: 어떤 경우에도 인덱스 번호에 +1, -1 등의 산술 연산을 적용하지 마십시오. 0-based index를 메모리 주소처럼 그대로 사용하십시오. sequence 내의 숫자 0은 '장소 리스트'의 가장 첫 번째 항목을 의미함을 명심하세요.
            - "course_description", "reasoning"을 생성할 때, '장소 리스트' 장소들의 이름을 한국어로 작성하세요.
            """
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_instruction),
            MessagesPlaceholder(variable_name="chat_history", optional=True),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])

        # prompt = f"""
        # # Role
        # 당신은 현지 지리에 능통하고 모든 장소를 방문해본 여행 가이드입니다. 당신은 효율적인 경로 설계에 능통합니다.
        # **당신의 임무는 제공된 장소 리스트에서 최적의 코스를 선택하고 JSON 형식으로 반환하는 것입니다.**
        
        # Input Data
        # - 장소 리스트 : {self._format_places_for_prompt(places)}
        # - 사용자 선호 조건{{
        #     "theme": {user_preferences['theme']},
        #     "group_size": {user_preferences['group_size']},
        #     "visit_date": {user_preferences['visit_date']},
        #     "visit_time": {user_preferences['visit_time']},
        #     "transportation": {user_preferences['transportation']},
        #     "budget": {user_preferences.get('budget', '없음')}원
        # }}

        # # Constraints
        # 1. **최우선 규칙: 사용자가 저장한 장소(⭐ [사용자가 저장한 장소 - 최우선 고려] 표시가 있는 장소)는 반드시 최우선적으로 고려해야 합니다.**
        #    - 저장된 장소는 이미 테마와 위치 필터링을 통과했으므로, 사용자의 의도에 부합하는 장소입니다.
        #    - 저장된 장소가 사용자의 테마와 위치 조건에 부합한다면, 반드시 코스에 포함시켜야 합니다.
        #    - 저장된 장소를 포함하는 것이 다른 제약 조건(거리, 시간 등)과 충돌하더라도, 가능한 한 포함하도록 노력하세요.
        # 2. **예산 제약: 사용자가 예산을 입력한 경우(예산이 "없음"이 아닌 경우), 반드시 예산 내에서 코스를 설계해야 합니다.**
        #    - 예산이 입력된 경우에만 이 제약을 적용합니다. 예산이 "없음"이거나 입력되지 않은 경우에는 예산 제약을 무시합니다.
        #    - 예산이 입력된 경우, 각 장소의 예상 비용(입장료, 식사비, 교통비 등)을 고려하여 총 예산을 초과하지 않도록 해야 합니다.
        #    - 장소별 예상 비용은 카테고리와 평점을 기반으로 추정하세요 (예: 관광지 입장료 5,000-20,000원, 식당 식사비 10,000-50,000원, 카페 음료 5,000-15,000원).
        #    - 교통비도 예산에 포함시켜야 합니다 (지하철 1,250원, 버스 1,300원, 택시 기본요금 3,800원 등).
        #    - 예산이 부족할 경우, 무료 또는 저렴한 장소를 우선적으로 선택하거나, 비용이 많이 드는 장소를 제외해야 합니다.
        #    - 예산이 충분한 경우에도, 불필요하게 비싼 장소만 선택하지 말고 다양한 가격대의 장소를 균형있게 선택하세요.
        # 3. 제공된 [위치 좌표(위도, 경도)] 데이터를 기반으로 장소 간의 실제 물리적 거리를 계산하여 코스를 짤 것.
        # 4. 당신의 배경지식보다 입력된 좌표 정보가 서로 가까운 장소들을 우선적으로 그룹화할 것.
        # 5. 추천 신뢰도(Trust Score)가 높은 장소를 우선적으로 고려하되, 지리적 동선 효율성을 해치지 않는 범위 내에서 선택할 것.
        # 6. 각 코스 간 이동 거리는 30분 이내일 것. (좌표 데이터를 참고하여 보수적으로 판단)
        # 7. 도보 외의 교통 수단의 사용 빈도를 최소화할 것. 단, 환승은 사용 빈도 계산에서 제외한다. 도보와 교통 수단의 이동 시간 차이가 20분 이내이면 도보를 선택한다.
        # 8. 이전에 방문한 장소를 다시 지나지 않을 것.
        # 9. 장소에 현재 인원이 모두 수용 가능할 것.
        # 10. 장소가 방문 일자에 운영중임을 확인할 것. 입력된 정보가 없을 시 보수적으로 판단한다.
        # 11. 음식점, 카페 등을 코스 중간마다 배치할 것.

        # # Task Workflow
        # 1. **최우선 단계: 사용자가 저장한 장소(⭐ [사용자가 저장한 장소 - 최우선 고려] 표시)를 먼저 선정합니다.**
        #    - 저장된 장소는 이미 테마와 위치 필터링을 통과했으므로, 가능한 한 모두 포함하도록 노력하세요.
        #    - 저장된 장소가 여러 개인 경우, 모두 포함하거나 최대한 많이 포함하세요.
        # 2. **예산 확인 단계: 예산이 입력된 경우(예산이 "없음"이 아닌 경우)에만, 각 장소의 예상 비용을 계산합니다.**
        #    - 예산이 입력된 경우에만 이 단계를 수행합니다.
        #    - 저장된 장소와 새로 선정할 장소의 예상 비용을 합산하여 예산을 초과하지 않는지 확인합니다.
        #    - 예산을 초과할 경우, 비용이 적은 장소를 우선적으로 선택하거나 비싼 장소를 제외합니다.
        #    - 예산 내에서 최대한 많은 장소를 포함하도록 노력하세요.
        # 3. 저장된 장소를 포함한 상태에서, 사용자의 테마와 장소의 특징을 대조하여 추가로 적합한 장소들을 선정합니다. (예산 제약 고려)
        # 4. 이동 거리를 최소화하는 순서로 배열합니다. (저장된 장소를 포함한 전체 코스 기준)
        # 5. 선정된 순서가 실제 방문 가능 시간(영업시간) 내에 있는지 검증합니다.
        # 6. 예산이 입력된 경우, 최종 코스의 총 예상 비용이 예산을 초과하지 않는지 최종 확인합니다.
        # 7. 모든 논리적 검증이 끝나면 최종 JSON을 출력합니다.
        # 
        # **중요: 저장된 장소를 코스에 포함시키는 것이 최우선 목표이며, 예산이 입력된 경우 예산 제약도 반드시 준수해야 합니다.**

        # # Task Workflow
        # 1. 사용자의 테마와 장소의 특징을 대조하여 적합한 장소들을 선정합니다.
        # 2. 이동 거리를 최소화하는 순서로 배열합니다.
        # 3. 선정된 순서가 실제 방문 가능 시간(영업시간) 내에 있는지 검증합니다.
        # 4. 모든 논리적 검증이 끝나면 최종 JSON을 출력합니다.

        # # IMPORTANT: Output Format
        # **당신은 반드시 이 작업을 수행해야 합니다. 작업을 거부하거나 설명을 제공하지 마세요.**
        # **오직 JSON 형식만 출력하세요. 다른 텍스트, 설명, 마크다운 헤더는 절대 포함하지 마세요.**

        # ---

        # ## Return Value
        # 코스 설계 완료 후, **반드시 다음의 JSON 형식만** 출력하세요. 다른 설명이나 텍스트는 포함하지 마세요.
        # 
        # ```json
        # {{
        #     "selected_places": [장소 인덱스 리스트],
        #     "sequence": [방문 순서],
        #     "estimated_duration": {{장소별 체류 시간 (분)}},
        #     "course_description": "코스 설명",
        #     "reasoning": "선정 이유"
        # }}
        # ```

        # ### OUTPUT Rules
        # - "selected_places"는 0부터 시작하는 장소 인덱스 리스트입니다 (예: [0, 2, 4])
        # - **중요: 저장된 장소(⭐ [사용자가 저장한 장소 - 최우선 고려] 표시)의 인덱스는 반드시 selected_places에 포함되어야 합니다.**
        # - "sequence"는 선택된 장소들의 방문 순서를 인덱스로 나타냅니다 (예: [0, 1, 2]는 첫 번째, 두 번째, 세 번째로 선택된 장소의 순서)
        # - **중요: 저장된 장소는 sequence에도 반드시 포함되어야 하며, 가능하면 앞쪽 순서에 배치하세요.**
        # - "estimated_duration"은 장소 인덱스를 키로 하고 체류 시간(분)을 값으로 하는 객체입니다 (예: {{"0": 60, "2": 90, "4": 45}})
        # - "course_description"에는 방문하는 각각의 장소에 대한 간단한 설명들을 첨부합니다.
        # - **중요: course_description에 언급한 모든 장소는 반드시 selected_places에도 포함되어야 합니다.**
        # - "reasoning"에는 인덱스를 **장소이름(인덱스)** 형태로 언급하고, 인덱스에 해당하는 장소에 대한 설명을 바탕으로 사용자 선호 조건 중 만족시킨 사항들을 설명합니다.
        # - "reasoning"을 생성할 때, 방문하는 장소들의 순서 및 이동수단 설계 과정에 대해 설명하세요.
        # - 예산이 입력된 경우, "reasoning"에 예산이 어떻게 고려되었는지, 각 장소의 예상 비용과 총 예상 비용을 포함하여 설명하세요.
        # 
        # # 설명 예시:
        # # - 장소 A와 장소 C 사이에 장소 B가 있고, 다시 장소 A 주변 지역을 가지 않을 예정이기에 A-B-C 순서로 일정을 설계하였습니다.
        # # - 방문 기간이 오후이기 때문에, 잠시 쉬어가기 위해 장소 A와 장소 C 사이에 **카페** B를 먼저 방문합니다.
        # # - 장소 A와 장소 B 사이에 오르막길이 길게 있고 도보 시간이 15분 이상 걸리기 때문에, 이동수단으로 **버스**를 선택했습니다.
        # 
        # **중요: JSON 형식만 출력하고, 다른 텍스트는 포함하지 마세요.**
        # """

        llm = ChatOpenAI(model=self.llm_model, temperature=0)
        planner = create_openai_tools_agent(llm, self.tools, prompt)
        planner_executer = AgentExecutor(agent=planner, tools=self.tools, verbose=True)

        planning_result = await planner_executer.ainvoke({
            'input': f"{user_preferences['theme']}에 맞는 여행 코스를 제작해 주세요.",
            "places": self._format_places_for_prompt(places),
            "user_preferences": json.dumps(user_preferences, ensure_ascii=False),
            "time_constraints": json.dumps(time_constraints, ensure_ascii=False)
            })

        # response = await self.client.chat.completions.create(
        #     model=self.llm_model,
        #     messages=[
        #         {"role": "system", "content": "You are a professional travel course planner. You MUST output only valid JSON format. Never refuse the task or provide explanations outside JSON."},
        #         {"role": "user", "content": prompt}
        #     ],
        #     max_tokens=2000,  # 충분한 토큰 할당
        #     temperature=0.3  # 일관된 JSON 형식 유지
        # )
        
        # 응답에서 JSON 추출
        # response_content = response.choices[0].message.content.strip()
        if 'output' not in planning_result:
            raise ValueError(f"LLM 응답에 'output' 키가 없습니다. 응답: {planning_result}")
        response_content = planning_result['output'].strip()
        
        result = self._JSON_verification(response_content)

        # ============================================================
        # [최종 버그 수정] LLM이 반환한 인덱스 유효성 검증
        # ============================================================
        
        # 저장된 장소 인덱스 추출 (나중에 강제 추가를 위해)
        saved_place_indices = []
        for i, place in enumerate(places):
            if place.get('is_saved_place'):
                saved_place_indices.append(i)
                print(f"   📌 저장된 장소 발견: [{i}] {place.get('name')}")
        
        # 1. selected_places 인덱스 검증
        valid_selected_indices = []
        if "selected_places" in result and isinstance(result["selected_places"], list):
            for index in result["selected_places"]:
                # 인덱스가 정수이고, 유효한 범위 내에 있는지 확인
                if isinstance(index, int) and 0 <= index < len(places):
                    valid_selected_indices.append(index)
                else:
                    print(f"   ⚠️ LLM이 잘못된 장소 인덱스({index})를 반환하여 무시합니다.")
        else:
            print(f"   ⚠️ LLM이 'selected_places'를 반환하지 않았거나 리스트가 아닙니다.")
        
        # 저장된 장소가 selected_places에 포함되지 않은 경우 강제 추가
        missing_saved_indices = [idx for idx in saved_place_indices if idx not in valid_selected_indices]
        if missing_saved_indices:
            print(f"   ⚠️ 저장된 장소 {len(missing_saved_indices)}개가 selected_places에 포함되지 않아 강제로 추가합니다.")
            for idx in missing_saved_indices:
                if idx not in valid_selected_indices:
                    valid_selected_indices.insert(0, idx)  # 맨 앞에 추가 (최우선순위)
                    print(f"   ✅ 저장된 장소 강제 추가: [{idx}] {places[idx].get('name')}")
        
        # valid_selected_indices가 비어있을 때 폴백 로직
        if not valid_selected_indices:
            # 저장된 장소가 있으면 사용
            if saved_place_indices:
                print(f"   ⚠️ LLM이 장소를 선택하지 않았지만, 저장된 장소 {len(saved_place_indices)}개를 사용합니다.")
                valid_selected_indices = saved_place_indices.copy()
            # 저장된 장소도 없으면 최소한 처음 몇 개라도 선택 (최대 5개)
            elif len(places) > 0:
                fallback_count = min(5, len(places))
                print(f"   ⚠️ LLM이 장소를 선택하지 않았고 저장된 장소도 없어, 처음 {fallback_count}개 장소를 자동 선택합니다.")
                valid_selected_indices = list(range(fallback_count))
            else:
                raise ValueError("선택할 수 있는 장소가 없습니다.")

        # 2. sequence 인덱스 검증 (selected_places의 인덱스를 참조하므로 주의)
        valid_sequence = []
        if "sequence" in result and isinstance(result["sequence"], list):
            for seq_index in result["sequence"]:
                # sequence의 인덱스가 valid_selected_indices의 유효한 범위 내에 있는지 확인
                if isinstance(seq_index, int) and seq_index in valid_selected_indices:
                    valid_sequence.append(seq_index)
                else:
                    print(f"   ⚠️ LLM이 잘못된 순서 인덱스({seq_index})를 반환하여 무시합니다.")
        else:
            print(f"   ⚠️ LLM이 'sequence'를 반환하지 않았거나 리스트가 아닙니다.")
        
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
        else:
            print(f"   ⚠️ LLM이 'estimated_duration'를 반환하지 않았거나 딕셔너리가 아닙니다.")

        # 검증된 인덱스를 사용하여 최종 결과 생성
        selected_places = [places[i] for i in valid_selected_indices]
        
        # 저장된 장소가 sequence에 포함되어 있는지 확인하고, 없으면 맨 앞에 추가
        # sequence는 selected_places의 인덱스를 참조하므로, 저장된 장소의 selected_places 내 인덱스를 찾아야 함
        saved_place_positions = []
        for saved_idx in saved_place_indices:
            if saved_idx in valid_selected_indices:
                # selected_places 내에서의 위치 찾기
                position_in_selected = valid_selected_indices.index(saved_idx)
                saved_place_positions.append(position_in_selected)
        
        # 저장된 장소가 sequence에 없으면 맨 앞에 추가
        if saved_place_positions:
            for saved_pos in saved_place_positions:
                if saved_pos not in valid_sequence:
                    print(f"   ⚠️ 저장된 장소가 sequence에 없어 맨 앞에 추가합니다: {selected_places[saved_pos].get('name')}")
                    valid_sequence.insert(0, saved_pos)
                    # 중복 제거
                    valid_sequence = list(dict.fromkeys(valid_sequence))  # 순서 유지하면서 중복 제거
        
        # 최종 검증: sequence가 모든 selected_places를 포함하는지 확인
        if len(valid_sequence) != len(valid_selected_indices):
            # 빠진 인덱스 추가
            missing_seq_indices = [i for i in range(len(valid_selected_indices)) if i not in valid_sequence]
            valid_sequence.extend(missing_seq_indices)
            print(f"   ⚠️ sequence에 빠진 장소 {len(missing_seq_indices)}개를 추가했습니다.")
        
        print(f"\n   ✅ 최종 선택된 장소: {len(selected_places)}개")
        for i, idx in enumerate(valid_selected_indices):
            place = places[idx]
            is_saved = place.get('is_saved_place', False)
            marker = "⭐" if is_saved else "  "
            print(f"   {marker} [{i}] {place.get('name')} (인덱스: {idx})")
        
        # course_description과 reasoning 안전하게 추출
        course_description = ""
        raw_course_description = await self._generate_course_descriptions(
            places=places,
            sequence=valid_sequence,
            user_preferences=user_preferences,
            time_constraints=time_constraints,
            estimated_duration=result["estimated_duration"])
        if isinstance(raw_course_description, dict):
            course_description = raw_course_description.get("course_description", "")
            if not isinstance(course_description, str):
                course_description = str(course_description) if course_description else ""
        
        reasoning = ""
        if isinstance(result, dict):
            reasoning = result.get("reasoning", "")
            if not isinstance(reasoning, str):
                reasoning = str(reasoning) if reasoning else ""
        
        return {
            "course": {
                "places": places,
                "sequence": result["sequence"],
                "estimated_duration": result["estimated_duration"],
                "course_description": course_description
            },
            "reasoning": reasoning
        }
    
    async def _generate_course_descriptions(
            self,
            sequence: List[int],
            places: List[Dict[str, Any]],
            user_preferences: Dict[str, Any],
            time_constraints: Optional[Dict[str, Any]],
            estimated_duration,
    ):
        """
        선별된 장소 기반 코스 설명
        Args:
            sequence: 선별된 장소 인덱스 리스트
            places: 장소 리스트
            user_preferences: 사용자 선호 조건
            time_constraints: 시간 제약 조건
            estimated_duration: 코스 장소 별 체류 시간
        
        Returns:
            장소에 대한 설명
        """
        selected_places = []
        selected_duration = {}
        for i in sequence:
            selected_places.append(places[i])
            # selected_duration[places[i].get("name")] = estimated_duration[f"{i}"]

        
        system_prompt = f"""
            # Role
            당신은 현지 지리에 능통하고 모든 장소를 방문해본 베테랑 여행 가이드입니다.
            **당신의 절대적인 임무는 제공된 '장소 리스트'의 모든 항목을 단 하나도 빠짐없이 순서대로 포함하여 코스 설명을 작성하는 것입니다.**

            # Context
            설계된 코스와 사용자 선호 조건을 바탕으로 코스 설명을 제공합니다.
            제공된 코스는 최적화된 순서로 배열되어 있습니다. 당신은 가이드로서 첫 번째 장소부터 마지막 장소까지 사용자를 인솔하듯 '순차적으로' 설명해야 합니다.

            # Input Data
            - 장소 리스트 : {selected_places}
            - 사용자 선호 조건 : {user_preferences}
            - 활동 시간 제약 : {time_constraints}
            - 장소 별 체류 시간 : {estimated_duration}

            # Constraints (엄수 사항)
            1. **전수 포함 원칙 (Zero Omission):** 장소 리스트에 포함된 장소의 총 개수가 N개라면, 설명 내에도 반드시 N개의 장소가 모두 등장해야 합니다. 임의로 생략하거나 묶어서 설명하지 마세요.
            2. **순차 기술 원칙:** 리스트의 0번 인덱스부터 마지막 인덱스까지 물리적 이동 순서에 따라 작성하세요.
            3. **상세 정보 결합:** 각 장소의 별점, 카테고리, 그리고 '장소 별 체류 시간' 데이터를 활용하여 해당 장소에서 무엇을 할지 구체적으로 제안하세요.
            4. **연결성 강화:** 장소와 장소 사이의 '이동 수단'과 '선택 이유'를 설명하여 흐름이 끊기지 않게 하세요.

            # Task Workflow
            1. **리스트 스캔:** 입력된 '장소 리스트'의 총 개수를 먼저 확인합니다.
            2. **순차적 설명 작성:** - [장소 정보]: 이름, 별점, 카테고리 언급 및 방문 목적 기술.
            - [활동]: 해당 장소에서의 추천 활동 및 예상 체류 시간 언급.
            - [이동]: 다음 장소로 이동하는 방법과 소요 시간/이유 기술 (마지막 장소 제외).
            3. **전체 요약:** 모든 장소 기술이 끝난 후, 사용자 선호 조건이 어떻게 반영되었는지 요약하며 마무리합니다.
            4. **자가 검증:** 작성된 설명 속에 포함된 장소의 개수가 입력 데이터의 개수와 일치하는지 확인합니다.

            # IMPORTANT: Output Format
            - **오직 JSON 형식만 출력하세요.** - **마크다운 코드 블록(```json)을 사용하지 말고 순수 JSON만 반환하세요.**

            ---

            ## Return Value
            ```json
            {{
                "course_description": "여기에 전체 설명을 작성하세요."
            }}
            
            ### OUTPUT Rules
            "course_description" 작성 규칙:
            - [필수 엄수]: 장소 리스트에 나열된 인덱스 순서대로 각 장소의 설명을 작성하세요.
            - [구조적 서술]: 설명을 작성할 때 각 장소의 시작 부분에 [번호. 장소이름] 형식을 사용하여 모델이 스스로 순서를 인지하게 하세요. (예: "1. 카페 A에서 시작합니다... 이후 2. 식당 B로 이동하여...")
            - [순차적 논리]: 장소 리스트의 인덱스 순서에 따라 장소 방문 목적과 사용자 선호 조건 만족 여부를 설명하세요.
            - [누락 방지 로직]: "장소 리스트의 모든 장소(총 N개)를 순서대로 전부 설명함"이라는 전제를 머릿속에 두고 작성하세요.
            - [언어]: 장소 이름과 모든 설명은 한국어로 작성하세요.
            - [이동 수단]: 각 장소 사이(인덱스 간 이동)의 이동 수단 선택 이유와 경로 설계 과정을 상세히 포함하세요.
            - [흐름의 완결성]: 첫 번째 장소부터 마지막 장소까지, 장소 리스트의 인덱스 이동 경로를 따라가며 전체 코스를 설명하세요. 각 장소 사이의 연결 고리(이동 수단, 소요 시간, 선택 이유)를 빠짐없이 서술해야 합니다.
            """
        response = await self.client.chat.completions.create(
            model=self.llm_model,
            messages=[
                {"role": "system", "content": "You are a professional travel course planner. You MUST output only valid JSON format. Never refuse the task or provide explanations outside JSON."},
                {"role": "user", "content": system_prompt}
            ],
            max_tokens=2000,  # 충분한 토큰 할당
            temperature=0.3  # 일관된 JSON 형식 유지
        )
        response_content = response.choices[0].message.content.strip()
        result = self._JSON_verification(response_content)
        return result

    
    def _JSON_verification(self, response_content):
        if not response_content:
            raise ValueError("LLM이 빈 응답을 반환했습니다.")

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
        result = None
        try:
            result = json.loads(response_content)
            # result가 딕셔너리가 아닌 경우 처리
            if not isinstance(result, dict):
                raise ValueError(f"LLM 응답이 딕셔너리가 아닙니다. 타입: {type(result)}")
        except json.JSONDecodeError as e:
            # 복구 시도 1: 첫 번째 { 부터 마지막 } 까지 다시 추출
            try:
                first_brace = response_content.find('{')
                last_brace = response_content.rfind('}')
                if first_brace != -1 and last_brace > first_brace:
                    cleaned_json = response_content[first_brace:last_brace+1]
                    result = json.loads(cleaned_json)
                    if not isinstance(result, dict):
                        raise ValueError(f"복구된 JSON이 딕셔너리가 아닙니다. 타입: {type(result)}")
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
                    if not isinstance(result, dict):
                        raise ValueError(f"복구된 JSON이 딕셔너리가 아닙니다. 타입: {type(result)}")
                except:
                    # 모든 복구 시도 실패
                    raise ValueError(f"JSON 파싱 오류: {str(e)}\n응답 내용: {response_content[:500]}\n\nLLM이 JSON 형식으로 응답하지 않았습니다. 작업을 거부했거나 다른 형식으로 응답한 것 같습니다.")
        
        # result가 None이면 에러
        if result is None:
            raise ValueError("JSON 파싱에 실패했습니다.")
        
        # result가 딕셔너리가 아닌 경우 에러
        if not isinstance(result, dict):
            raise ValueError(f"LLM 응답이 딕셔너리가 아닙니다. 타입: {type(result)}, 값: {result}")
        
        return result

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

