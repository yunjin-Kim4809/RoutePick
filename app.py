import asyncio
import threading
from flask import Flask, render_template, request, session, jsonify, redirect, url_for
from chatbot import get_chatbot_response
from agents import SearchAgent, PlanningAgent, RoutingAgent
from config.config import Config

app = Flask(__name__)
app.secret_key = 'string_secret_key'

messages = ["📌 여행 테마", "📍 지역", "👥 여행 인원 (숫자)", "📅 방문 일자", "⏰ 방문 시간", "🚶 이동 수단"]
input_data = {
        "theme": "theme",
        "location": "location",
        "group_size": "group_size",
        "visit_date": "visit_date",
        "visit_time": "visit_time",
        "transportation": "transportation"
    }

course = {}

agent_done = False

async def execute_Agents():
    config = Config.get_agent_config()
    try:
        search_agent = SearchAgent(config=config)
        search_input = {
            "theme": input_data["theme"],
            "location": input_data["location"]
        }
        # if not search_agent.validate_input(search_input):
        #     print("❌ 필수 정보가 누락되었습니다.")
        #     missing_info = []
            
        #     if not search_input.get("theme"):
        #         missing_info.append("테마")
        #     if not search_input.get("location"):
        #         missing_info.append("지역")
            
        #     if missing_info:
        #         print(f"⚠️  다음 정보를 입력해주세요: {', '.join(missing_info)}")
        #         print()
                
        #         # 누락된 정보 재입력 받기
        #         if not search_input.get("theme"):
        #             search_input["theme"] = get_user_input("📌 여행 테마", required=True)
        #         if not search_input.get("location"):
        #             search_input["location"] = get_user_input("📍 지역", required=True)
                
        #         # 재검증
        #         if not search_agent.validate_input(search_input):
        #             print("❌ 검증 실패: 필수 정보가 여전히 누락되었습니다.")
        #             return
        
        search_result = await search_agent.execute(search_input)
        
        if not search_result.get("success"):
            error_msg = f"❌ 장소 검색 실패: {search_result.get('error', '알 수 없는 오류')}"
            return False, error_msg
        
        places = search_result.get("candidate_pool", [])
        print(f"\n✅ 검색 완료: {len(places)}개의 장소를 찾았습니다.\n")
        # yield f"\n✅ 검색 완료: {len(places)}개의 장소를 찾았습니다."
        """
        TODO
        html page에 동적으로 중간 과정 메세지 출력.
        queue, yield 사용.
        """
        
        if not places:
            error_msg = "⚠️  검색된 장소가 없습니다. 다른 테마나 지역으로 시도해주세요."
            return False, error_msg
        
        # 검색된 장소 미리보기
        print("📍 검색된 장소 미리보기 (상위 5개):")
        for i, place in enumerate(places[:5], 1):
            print(f"  {i}. {place.get('name')} ({place.get('category')}) - 평점: {place.get('rating', 'N/A')}")
        print()
        
        # ============================================================
        # Step 2: PlanningAgent 실행 (코스 제작)
        # ============================================================
        print("🧠 [Step 2] PlanningAgent: 코스 제작 중...")
        print()
        
        planning_agent = PlanningAgent(config=config)
        
        # 사용자 선호도 구성
        user_preferences = {
            "theme": input_data["theme"],
            "group_size": input_data["group_size"],
            "visit_date": input_data["visit_date"] or "2024-12-25",
            "visit_time": input_data["visit_time"] or "오후",
            "transportation": input_data["transportation"] or "도보"
        }
        
        # 시간 제약 (선택사항)
        time_constraints = None
        if input_data.get("visit_time"):
            time_constraints = {
                "start_time": "14:00" if "오후" in input_data["visit_time"] else "10:00",
                "end_time": "20:00",
                "total_duration": 360  # 6시간
            }
        
        planning_input = {
            "places": places,
            "user_preferences": user_preferences,
            "time_constraints": time_constraints
        }
        
        # PlanningAgent 입력 검증 및 누락 정보 확인
        # if not planning_agent.validate_input(planning_input):
        #     print("❌ 필수 정보가 누락되었습니다.")
        #     missing_info = []
            
        #     if not planning_input.get("places"):
        #         missing_info.append("장소 리스트")
        #     if not planning_input.get("user_preferences", {}).get("theme"):
        #         missing_info.append("테마")
            
        #     if missing_info:
        #         print(f"⚠️  다음 정보가 누락되었습니다: {', '.join(missing_info)}")
                
        #         # 장소가 없으면 검색 단계로 돌아가기
        #         if not planning_input.get("places"):
        #             print("❌ 장소 검색 결과가 없습니다. 코스를 제작할 수 없습니다.")
        #             return
                
        #         # 테마가 없으면 재입력
        #         if not planning_input.get("user_preferences", {}).get("theme"):
        #             print()
        #             theme = get_user_input("📌 여행 테마 (필수)", required=True)
        #             planning_input["user_preferences"]["theme"] = theme
                
        #         # 재검증
        #         if not planning_agent.validate_input(planning_input):
        #             print("❌ 검증 실패: 필수 정보가 여전히 누락되었습니다.")
        #             return
        
        course_result = await planning_agent.execute(planning_input)
        
        if not course_result.get("success"):
            error_msg = f"❌ 코스 제작 실패: {course_result.get('error', '알 수 없는 오류')}"
            return False, error_msg
        
        # ============================================================
        # 결과 출력
        # ============================================================
        print()
        print("=" * 70)
        print("✨ 코스 제작 완료!")
        print("=" * 70)
        print()
        
        global course
        course = course_result.get("course", {})
        # location 정보 추가 (지오코딩에 사용)
        if input_data.get("location"):
            course["location"] = input_data["location"]
        
        # reasoning 정보도 course에 추가 (챗봇에서 사용)
        if course_result.get("reasoning"):
            course["reasoning"] = course_result.get("reasoning")
        
        # 코스 설명
        if course.get("course_description"):
            print("📝 코스 설명")
            print("-" * 70)
            print(course["course_description"])
            print()
        
        # 방문 순서
        sequence = course.get("sequence", [])
        places_list = course.get("places", [])
        estimated_duration = course.get("estimated_duration", {})
        
        if sequence and places_list:
            print("📍 방문 순서")
            print("-" * 70)
            
            for idx, place_idx in enumerate(sequence, 1):
                if place_idx < len(places_list):
                    place = places_list[place_idx]
                    duration = estimated_duration.get(str(place_idx), "정보 없음")
                    
                    print(f"\n{idx}. {place.get('name', '알 수 없음')}")
                    print(f"   📌 카테고리: {place.get('category', 'N/A')}")
                    print(f"   ⏱  체류 시간: {duration}분")
                    print(f"   ⭐ 평점: {place.get('rating', 'N/A')}")
                    print(f"   📍 주소: {place.get('address', '주소 정보 없음')}")
                    
                    if place.get('map_url'):
                        print(f"   🔗 지도: {place['map_url']}")
            
            print()
        
        # 선정 이유
        reasoning = course_result.get("reasoning")
        if reasoning:
            print("💡 선정 이유")
            print("-" * 70)
            print(reasoning)
            print()
        
        print("=" * 70)
        print("✅ 테스트 완료!")
        print("=" * 70)
        
    except KeyboardInterrupt:
        print("\n\n⚠️  사용자에 의해 중단되었습니다.")
    except Exception as e:
        print(f"\n❌ 오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()

def run_agent_task():
    global agent_done
    asyncio.run(execute_Agents())
    agent_done = True

@app.route('/', methods=['GET', 'POST'])
def index():
    if 'selections' not in session:
        session['selections'] = []

    if request.method == 'POST':
        user_input = request.form['choice']
        choice_source = request.form['source']
        # print(user_input, choice_source)
        if user_input is not None:
            # 입력값을 명시적으로 str()로 변환하여 저장
            val = str(user_input)
            
            temp_list = session['selections']
            temp_list.append(val)
            session['selections'] = temp_list

    current_step = len(session['selections'])
    finished = current_step >= len(messages)
    input_dataset = dict(zip(input_data.keys(), session['selections']))
    return render_template('index.html', 
                           step=current_step + 1,
                           messages = messages, 
                           finished=finished,
                           results=session['selections'])

@app.route("/status")
def status():
    return {"done": agent_done}

@app.route('/reset')
def reset():
    session.pop('selections', None)
    return redirect(url_for('index'))

@app.route('/call-agent')
def call_agents():
    # session에서 실제 입력값 가져와서 input_data 업데이트
    global input_data
    if 'selections' in session and len(session['selections']) >= len(messages):
        selections = session['selections']
        input_data = dict(zip(input_data.keys(), selections))
    
    session.pop('selections', None)
    threading.Thread(target=run_agent_task).start()
    return render_template('loading.html')

@app.route('/chat-map')
def chat_page():
    # .env 파일에서 Google Maps API 키 가져오기 (Config는 이미 상단에서 import됨)
    return render_template('chat.html',
                           course=course,
                           google_maps_api_key=Config.GOOGLE_MAPS_API_KEY)

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json
    user_message = data.get("message")
    
    if not user_message:
        return jsonify({"response": "메시지를 입력해주세요."}), 400
    
    # chatbot.py의 로직 호출
    global course
    bot_response = get_chatbot_response(user_message, course)
    
    return jsonify({"response": bot_response})

@app.route('/api/locations', methods=['GET'])
def get_locations():
    global course
    # 코스 정보에 reasoning도 포함하여 반환
    result = course.copy() if course else {}
    
    # reasoning이 별도로 저장되어 있다면 추가 (course_result에서 가져올 수도 있음)
    # 현재는 course 객체에 포함되어 있다고 가정
    
    return jsonify(result)

if __name__ == '__main__':
    app.run(debug=True)