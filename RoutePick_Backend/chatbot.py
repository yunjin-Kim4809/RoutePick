import os
import json
from openai import OpenAI
from config.config import Config
from typing import List, Dict, Optional
# from langchain.prompts import PromptTemplate

# OpenAI 클라이언트 초기화 (Config에서 API 키 가져오기)
client = OpenAI(api_key=Config.OPENAI_API_KEY)

# 대화 히스토리 저장 (task_id별로 관리)
chat_histories: Dict[str, List[Dict[str, str]]] = {}

"""
TODO:
- langchain을 이용한 agent를 사용하는 챗봇 구현
- 전달받은 초기 정보 실시간 업데이트 기능 (웹사이트에 동적으로 반영)
"""

langchainPrompt = """
# Persona
당신은 현지 지리에 능통한 전문 여행 가이드입니다.
- 말투: 친절하고 전문적인 어투를 사용하세요.
- 전문성: 사용자의 질문에 대해 **정확한 정보**임이 확인되었을 때만 답변합니다.
- 규칙: 정확하지 않은 정보에 대해서는 **모른다고 답변하세요**.
# Initial Message
처음 대화 시작 시 다음의 메세지를 사용하고, 이후 답변에서는 사용하지 마세요:
"안녕하세요! 찾아주셔서 감사합니다. 무엇을 도와드릴까요?"

Answer the following questions as best you can. You have access to the following tools:
{tools}

Use the following format:
Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: the final answer to the original input question

Begin!

Chat History: {chat_history}
Question: {input}
Thought: {agent_scratchpad}
"""

# prompt = PromptTemplate.from_template(langchainPrompt)

# langchain 사용 안 하는 버전 (개선된 interactive 챗봇)

def get_chatbot_response(user_message: str, course: Dict, task_id: str = None) -> str:
    """
    개선된 챗봇 응답 생성
    - 대화 히스토리 관리
    - 맥락 이해 개선
    - 더 자연스러운 대화
    """
    # 대화 히스토리 초기화 또는 가져오기
    if task_id and task_id not in chat_histories:
        chat_histories[task_id] = []
    
    # 코스 정보 포맷팅
    course_info = format_course_info(course)
    
    # 시스템 프롬프트
    system_prompt = f"""
    # 페르소나
    당신은 현지 지리에 능통한 전문 여행 가이드 "RoutePick AI"입니다.
    
    # 말투 및 스타일
    - 친절하고 따뜻한 말투를 사용하세요. "~해요", "~입니다" 같은 존댓말을 사용하세요.
    - 사용자의 질문에 대해 적극적으로 도와주는 태도를 보이세요.
    - 적절한 이모지를 사용하여 친근함을 표현하세요 (예: 😊, 🗺️, ⭐, 📍, 🍽️ 등).
    - 긴 답변은 문단을 나누어 읽기 쉽게 작성하세요.
    
    # 전문성
    - 제공된 코스 정보를 바탕으로 정확한 정보만 답변하세요.
    - 정확하지 않은 정보에 대해서는 솔직하게 모른다고 답변하세요.
    - 코스 정보에 없는 내용은 추측하지 마세요.
    
    # 대화 방식
    - 사용자의 이전 질문과 맥락을 고려하여 자연스러운 대화를 이어가세요.
    - 사용자가 코스에 대해 궁금해하는 부분을 예상하고 도움이 되는 정보를 제공하세요.
    - 질문이 모호할 경우, 명확히 하기 위한 질문을 던질 수 있습니다.
    
    # 코스 정보
    {course_info}
    
    # 주의사항
    - 항상 제공된 코스 정보를 우선적으로 참고하세요.
    - 사용자가 코스를 수정하거나 변경을 요청하면, 현재 코스 정보를 바탕으로 답변하세요.
    - 코스에 포함된 장소에 대한 구체적인 정보(주소, 평점, 체류 시간 등)를 제공할 수 있습니다.
    
    # 장소 업데이트 기능
    사용자가 장소를 추가하거나 제거하고 싶어할 때, 응답 끝에 특별한 JSON 형식으로 표시하세요:
    
    - 장소 추가 요청: 사용자가 "OO 장소 추가해줘", "OO도 포함시켜줘" 같은 요청을 할 때
    - 장소 제거 요청: 사용자가 "OO 장소 빼줘", "OO 제거해줘" 같은 요청을 할 때
    
    장소 변경이 필요한 경우, 응답 끝에 다음 형식으로 추가하세요:
    
    [COURSE_UPDATE]
    {{
        "action": "add" 또는 "remove",
        "place_name": "장소 이름",
        "index": 제거할 경우 sequence 인덱스 (0부터 시작)
    }}
    [/COURSE_UPDATE]
    
    예시:
    - "경복궁 추가해줘" → [COURSE_UPDATE]{{"action": "add", "place_name": "경복궁"}}[/COURSE_UPDATE]
    - "첫 번째 장소 빼줘" → [COURSE_UPDATE]{{"action": "remove", "index": 0}}[/COURSE_UPDATE]
    
    주의: 장소 추가 시에는 장소 이름만 제공하면 됩니다. 시스템이 자동으로 검색하여 추가합니다.
    """
    
    # 대화 히스토리 구성
    messages = [{"role": "system", "content": system_prompt}]
    
    # 이전 대화 히스토리 추가 (최근 10개만)
    if task_id and task_id in chat_histories:
        recent_history = chat_histories[task_id][-10:]
        for msg in recent_history:
            messages.append(msg)
    
    # 현재 사용자 메시지 추가
    messages.append({"role": "user", "content": user_message})
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            max_tokens=800,  # 더 긴 답변 허용
            temperature=0.8  # 더 자연스러운 대화
        )
        
        bot_response = response.choices[0].message.content
        
        # 대화 히스토리 저장
        if task_id:
            if task_id not in chat_histories:
                chat_histories[task_id] = []
            chat_histories[task_id].append({"role": "user", "content": user_message})
            chat_histories[task_id].append({"role": "assistant", "content": bot_response})
        
        return bot_response
    except Exception as e:
        error_msg = f"죄송합니다. 일시적인 오류가 발생했습니다. 다시 시도해주세요. 😔"
        print(f"챗봇 오류: {str(e)}")
        return error_msg


def parse_course_update(bot_response: str) -> Optional[Dict]:
    """챗봇 응답에서 코스 업데이트 정보 추출"""
    import re
    import json
    
    # [COURSE_UPDATE]...[/COURSE_UPDATE] 패턴 찾기
    pattern = r'\[COURSE_UPDATE\](.*?)\[/COURSE_UPDATE\]'
    match = re.search(pattern, bot_response, re.DOTALL)
    
    if match:
        try:
            update_data = json.loads(match.group(1).strip())
            return update_data
        except json.JSONDecodeError:
            return None
    return None


def format_course_info(course: Dict) -> str:
    """코스 정보를 프롬프트에 적합한 형식으로 포맷팅"""
    if not course:
        return "코스 정보가 없습니다."
    
    places = course.get("places", [])
    sequence = course.get("sequence", [])
    estimated_duration = course.get("estimated_duration", {})
    course_description = course.get("course_description", "")
    reasoning = course.get("reasoning", "")
    location = course.get("location", "")
    
    info = "=== 코스 정보 ===\n\n"
    
    if course_description:
        info += f"📝 코스 설명:\n{course_description}\n\n"
    
    if location:
        info += f"📍 지역: {location}\n\n"
    
    if places and sequence:
        info += "📍 방문 순서 및 장소 정보:\n"
        for idx, place_idx in enumerate(sequence, 1):
            if place_idx < len(places):
                place = places[place_idx]
                duration = estimated_duration.get(str(place_idx), estimated_duration.get(place_idx, "정보 없음"))
                
                info += f"\n{idx}. {place.get('name', '알 수 없음')}\n"
                info += f"   - 카테고리: {place.get('category', 'N/A')}\n"
                info += f"   - 체류 시간: {duration}분\n"
                info += f"   - 평점: {place.get('rating', 'N/A')}\n"
                info += f"   - 주소: {place.get('address', '주소 정보 없음')}\n"
                if place.get('map_url'):
                    info += f"   - 지도 링크: {place.get('map_url')}\n"
    
    if reasoning:
        info += f"\n💡 코스 선정 이유:\n{reasoning}\n"
    
    return info


def clear_chat_history(task_id: str):
    """특정 task_id의 대화 히스토리 초기화"""
    if task_id in chat_histories:
        del chat_histories[task_id]