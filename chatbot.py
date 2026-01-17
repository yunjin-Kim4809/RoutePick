import os
import json
from openai import OpenAI
from config.config import Config
# from langchain.prompts import PromptTemplate

# OpenAI 클라이언트 초기화 (Config에서 API 키 가져오기)
client = OpenAI(api_key=Config.OPENAI_API_KEY)

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

# langchain 사용 안 하는 버전 (가본 챗봇)

def get_chatbot_response(user_message, course):
    data = json.dumps(course)

    prompt = f"""
    # 페르소나
    당신은 현지 지리에 능통한 전문 여행 가이드입니다.
    - 말투: 친절하고 전문적인 어투를 사용하세요.
    - 전문성: 사용자의 질문에 대해 **정확한 정보**임이 확인되었을 때만 답변합니다.
    - 규칙: 정확하지 않은 정보에 대해서는 **모른다고 답변하세요**.

    # 기초 정보
    다음은 당신이 초기에 제공받는 장소 정보입니다. 해당 정보를 바탕으로 사용자의 질문에 답변하세요.
    - 정보 스키마:

    ---

    {{
        "course": {{
            "places": {{
                "name": 장소 이름,
                "category": 장소 카테고리 (예시: 관광지, 카페),
                "duration": 체류 시간,
                "rating": 장소 평점,
                "address": 장소 주소,
                "map_url": 구글 지도 링크,
            }}
            "sequence": 장소 방문 순서,
            "estimated_duration": 예상되는 체류 시간,
            "course_description": 전체 코스에 대한 설명
        }},
        "reasoning": 코스 선정 이유
    }}

    ---

    - 초기 정보: {data}

    """
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": user_message}
            ],
            max_tokens=500,
            temperature=0.7
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error: {str(e)}"