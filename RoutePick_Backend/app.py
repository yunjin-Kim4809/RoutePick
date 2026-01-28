import asyncio
import threading
import json
import os
from flask import Flask, render_template, request, jsonify, redirect, url_for, send_file
from flask_cors import CORS
from chatbot import get_chatbot_response, clear_chat_history, parse_course_update  # chatbot.py가 course 객체를 인자로 받도록 수정 필요
from agents import SearchAgent, PlanningAgent
from config.config import Config
import uuid
import googlemaps
    
from PIL import Image, ImageDraw, ImageFont
import io # 메모리 상에서 이미지를 다루기 위함

app = Flask(__name__)
app.secret_key = 'string_secret_key'
CORS(app)

# 여러 사용자의 작업 상태와 결과를 저장하는 '개인 사물함'
agent_tasks = {}

async def execute_Agents(task_id, input_data):
    global agent_tasks
    config = Config.get_agent_config()

    try:
        # 1. 검색 단계 시작 알림
        agent_tasks[task_id]["message"] = f"🔍 '{input_data['location']}' 지역의 '{input_data['theme']}' 테마를 분석 중입니다..."
        print(f"[{task_id}] 검색 시작")

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
            raise Exception(f"장소 검색 실패: {search_result.get('error', '알 수 없는 오류')}")

        places = search_result.get("candidate_pool", [])
        
        # 저장된 장소를 테마와 위치가 맞는 경우에만 우선적으로 추가
        saved_places = load_saved_places()
        theme = input_data.get("theme", "").lower()
        location = input_data.get("location", "").lower()
        
        if saved_places:
            saved_place_ids = {p.get('place_id') for p in saved_places if p.get('place_id')}
            existing_place_ids = {p.get('place_id') for p in places if p.get('place_id')}
            
            # 이미 검색 결과에 포함된 저장된 장소에도 플래그 추가
            for place in places:
                if place.get('place_id') in saved_place_ids:
                    place['is_saved_place'] = True
            
            # 저장된 장소 중 테마/위치가 맞는 것만 필터링
            filtered_saved_places = []
            for saved_place in saved_places:
                saved_id = saved_place.get('place_id')
                if saved_id and saved_id not in existing_place_ids:
                    # 테마 매칭: 카테고리나 이름이 테마와 관련이 있는지 확인
                    category = saved_place.get('category', '').lower()
                    name = saved_place.get('name', '').lower()
                    address = saved_place.get('address', '').lower()
                    
                    # 위치 매칭: 더 정확한 위치 매칭 로직
                    location_match = False
                    if location:
                        location_lower = location.lower()
                        address_lower = address.lower()
                        
                        # 위치 키워드 추출 (구 단위, 동 단위 등)
                        location_keywords = location_lower.split()
                        
                        # 1. 전체 위치 문자열이 주소에 포함되어 있는지 확인
                        if location_lower in address_lower:
                            location_match = True
                        # 2. 위치 키워드 중 하나라도 주소에 포함되어 있는지 확인 (2글자 이상)
                        elif any(len(kw) > 1 and kw in address_lower for kw in location_keywords):
                            location_match = True
                        # 3. 특수 케이스: '서울' -> '서울특별시', '강남' -> '강남구' 등
                        else:
                            # '서울' 검색 시 '서울특별시' 포함 확인
                            if '서울' in location_lower and '서울' in address_lower:
                                location_match = True
                            # '강남' 검색 시 '강남구' 포함 확인
                            elif '강남' in location_lower and '강남' in address_lower:
                                location_match = True
                            # 기타 주요 지역명 매칭
                            elif any(kw in address_lower for kw in location_keywords if len(kw) >= 2):
                                location_match = True
                    else:
                        location_match = True  # 위치가 지정되지 않았으면 모든 장소 허용
                    
                    # 카테고리 정규화 (영어 -> 한글 변환)
                    category_normalized = normalize_category(category)
                    
                    # 테마 매칭: 더 유연한 매칭 로직
                    theme_match = False
                    if theme:
                        # 테마 키워드 추출 (더 넓은 범위)
                        theme_keywords = ['관광', '데이트', '맛집', '카페', '쇼핑', '문화', '역사', '자연', '실내', '야외', 
                                         '커플', '음식', '식당', '레스토랑', '전시', '박물관', '공원', '힐링', '휴식']
                        theme_lower = theme.lower()
                        theme_related = any(keyword in theme_lower for keyword in theme_keywords)
                        
                        # 카테고리 기반 매칭 (정규화된 카테고리 사용)
                        if theme_related:
                            # 데이트/커플 테마: 식당, 카페, 관광지, 활동 모두 허용
                            if '데이트' in theme_lower or '커플' in theme_lower:
                                theme_match = category_normalized in ['식당', '카페', '관광지', '활동', '쇼핑']
                            # 맛집/음식 테마: 식당, 카페 허용
                            elif '맛집' in theme_lower or '음식' in theme_lower or '식당' in theme_lower:
                                theme_match = category_normalized in ['식당', '카페']
                            # 쇼핑 테마
                            elif '쇼핑' in theme_lower:
                                theme_match = category_normalized == '쇼핑'
                            # 관광/문화/역사 테마: 관광지, 활동 허용
                            elif any(kw in theme_lower for kw in ['관광', '문화', '역사', '박물관', '전시']):
                                theme_match = category_normalized in ['관광지', '활동']
                            # 실내 테마: 실내 장소 허용
                            elif '실내' in theme_lower:
                                theme_match = category_normalized in ['식당', '카페', '활동', '쇼핑', '관광지']
                            # 일반적인 테마는 모두 허용 (더 관대하게)
                            else:
                                theme_match = True
                        else:
                            # 특정 키워드가 없어도 카테고리가 일반적인 경우 허용
                            theme_match = True
                    else:
                        theme_match = True  # 테마가 없으면 모두 허용
                    
                    # 정규화된 카테고리로 업데이트
                    if category_normalized != category:
                        saved_place['category'] = category_normalized
                    
                    # 테마와 위치가 모두 맞으면 추가
                    if theme_match and location_match:
                        formatted_place = {
                            'name': saved_place.get('name', ''),
                            'address': saved_place.get('address', ''),
                            'place_id': saved_id,
                            'rating': saved_place.get('rating', 0),
                            'category': saved_place.get('category', category_normalized),  # 정규화된 카테고리 사용
                            'coordinates': {
                                'lat': saved_place.get('lat'),
                                'lng': saved_place.get('lng')
                            } if saved_place.get('lat') and saved_place.get('lng') else None,
                            'is_saved_place': True,  # 저장된 장소 플래그 추가
                            'trust_score': 5.0  # 저장된 장소는 높은 신뢰도 부여
                        }
                        filtered_saved_places.append(formatted_place)
                        print(f"   ✅ 저장된 장소 매칭 성공: {saved_place.get('name')} (카테고리: {category_normalized}, 테마: {theme_match}, 위치: {location_match})")
                    else:
                        print(f"   ⚠️ 저장된 장소 매칭 실패: {saved_place.get('name')} (카테고리: {category_normalized}, 테마: {theme_match}, 위치: {location_match})")
            
            # 필터링된 저장된 장소를 맨 앞에 추가 (최우선순위)
            if filtered_saved_places:
                places = filtered_saved_places + places
                print(f"\n⭐ 저장된 장소 {len(filtered_saved_places)}개를 최우선순위로 추가했습니다 (테마/위치 매칭).\n")
                print(f"   저장된 장소 목록:")
                for sp in filtered_saved_places:
                    print(f"   - {sp.get('name')} ({sp.get('category')})")
                print()
        
        if not places:
            raise Exception("검색된 장소가 없습니다. 다른 테마나 지역으로 시도해주세요.")
        
        # 2. 검색 완료 알림 
        agent_tasks[task_id]["message"] = f"✅ 검색 완료: 검색 에이전트로부터 추천 장소를 전달받았습니다!"
        print(f"\n✅ 검색 완료: search_agent로부터 장소를 전달 받았습니다.\n")

        # 잠시 대기 (사용자가 메시지를 읽을 시간을 줌)
        await asyncio.sleep(1.5)

        # yield f"\n✅ 검색 완료: {len(places)}개의 장소를 찾았습니다."
        """
        TODO
        html page에 동적으로 중간 과정 메세지 출력.
        queue, yield 사용.
        """

        # 검색된 장소 미리보기
        print("📍 검색된 장소 미리보기 (상위 5개):")
        for i, place in enumerate(places[:5], 1):
            print(f"  {i}. {place.get('name')} ({place.get('category')}) - 평점: {place.get('rating', 'N/A')}")
        print()
        
        # ============================================================
        # Step 2: PlanningAgent 실행 (코스 제작)
        # ============================================================
        # 3. 코스 제작 단계 시작 알림
        agent_tasks[task_id]["message"] = "🧠 [Planning] 최적의 동선과 방문 순서를 계산하고 있습니다..."        
        print("🧠 [Step 2] PlanningAgent: 코스 제작 중...")
        print()
        
        planning_agent = PlanningAgent(config=config)
        
        # 사용자 선호도 구성
        user_preferences = {
            "theme": input_data["theme"],
            "location": input_data.get("location", ""),  # 지역 정보 추가 (날씨 조회용)
            "group_size": input_data.get("group_size", "1명"),
            "visit_date": input_data.get("visit_date") or "오늘",
            "visit_time": input_data.get("visit_time") or "오후",
            "transportation": input_data.get("transportation") or "도보",
            "budget": input_data.get("budget")  # 예산 정보 추가
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
            raise Exception(f"코스 제작 실패: {course_result.get('error', '알 수 없는 오류')}")
        
        # ============================================================
        # 결과 출력
        # ============================================================
        # 4. 마무리 단계 알림
        agent_tasks[task_id]["message"] = "✨ 코스 제작 완료! 최종 결과를 정리 중입니다."      
        
        final_course = course_result.get("course", {})
        if input_data.get("location"):
            final_course["location"] = input_data["location"]
        if course_result.get("reasoning"):
            final_course["reasoning"] = course_result.get("reasoning")
        # transportation 정보 저장
        if input_data.get("transportation"):
            final_course["transportation"] = input_data["transportation"]
        
        print(f"\n✨ [{task_id}] 코스 제작 완료! 터미널에서 결과 확인:")
        print("=" * 70)
        
        # 코스 설명
        if final_course.get("course_description"):
            print("📝 코스 설명")
            print("-" * 70)
            print(final_course["course_description"])
            print()
        
        # 방문 순서
        sequence = final_course.get("sequence", [])
        places_list = final_course.get("places", [])
        estimated_duration = final_course.get("estimated_duration", {})
        
        if sequence and places_list:
            print("📍 방문 순서")
            print("-" * 70)
            
            weather_info = final_course.get("weather_info", {})
            
            for idx, place_idx in enumerate(sequence, 1):
                if place_idx < len(places_list):
                    place = places_list[place_idx]
                    duration = estimated_duration.get(str(place_idx), "정보 없음")
                    
                    print(f"\n{idx}. {place.get('name', '알 수 없음')}")
                    print(f"   - 카테고리: {place.get('category', 'N/A')}")
                    print(f"   - 체류 시간: {duration}분")
                    
                    # 날씨 정보 출력
                    if place_idx in weather_info:
                        weather = weather_info[place_idx]
                        if weather.get("temperature") is not None:
                            print(f"   - 날씨: {weather.get('temperature')}°C, {weather.get('condition', '정보 없음')}")
                            if weather.get("humidity") is not None:
                                print(f"   - 습도: {weather.get('humidity')}%")
                    
            print()

        # 선정 이유
        reasoning = course_result.get("reasoning")
        if reasoning:
            print("💡 선정 이유")
            print("-" * 70)
            print(reasoning)
            print()
            
        print("=" * 70)

        # 최종 결과를 사용자 사물함에 저장
        agent_tasks[task_id].update({"done": True, "success": True, "course": final_course, "message": "완료되었습니다."})

    except Exception as e:
        print(f"\n❌ [{task_id}] 에이전트 실행 중 오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()
        agent_tasks[task_id].update({"done": True, "success": False, "error": str(e), "message": f"오류 발생: {str(e)}"})
        
def run_agent_task_with_id(task_id, input_data):
    asyncio.run(execute_Agents(task_id, input_data))

@app.route('/api/create-trip', methods=['POST'])
def create_trip():
    data = request.json
    task_id = str(uuid.uuid4())
    
    input_data_from_react = {
        "theme": data.get("theme"), "location": data.get("location"),
        "group_size": data.get("groupSize"),
        "visit_date": f"{data.get('startDate')} ~ {data.get('endDate')}" if data.get('endDate') and data.get('startDate') != data.get('endDate') else data.get('startDate'),
        "visit_time": data.get("visitTime"),
        "transportation": ", ".join(data.get("transportation", []) + ([data.get("customTransport")] if data.get("customTransport") else [])),
        "budget": data.get("budget")  # 예산 정보 추가
    }
    
    agent_tasks[task_id] = {
        "done": False,
        "success": False,
        "course": None,
        "message": "🚀 여행 생성 작업을 시작합니다...",
        # 나중에 경로 계산 시 사용할 방문 일시 정보도 함께 저장
        "visit_date": input_data_from_react.get("visit_date"),
        "visit_time": input_data_from_react.get("visit_time"),
    }
    threading.Thread(target=run_agent_task_with_id, args=(task_id, input_data_from_react)).start()
    
    print(f"🚀 [{task_id}] 신규 작업 시작.")
    return jsonify({"taskId": task_id, "status": "processing"})

@app.route("/status/<task_id>")
def status(task_id):
    task_status = agent_tasks.get(task_id, {})
    # course 데이터는 용량이 크므로 상태 체크 시에는 제외하고 보냄
    return jsonify({
        "done": task_status.get("done", False),
        "success": task_status.get("success", False),
        "error": task_status.get("error"),
        "message": task_status.get("message", "로딩 중...") # 현재 진행 상황 메시지
    })

@app.route('/chat-map/<task_id>')
def chat_page(task_id):
    task = agent_tasks.get(task_id)
    if task and task.get('success'):
        course_data = task.get('course')
        return render_template('chat.html', course=course_data, task_id=task_id, google_maps_api_key=Config.GOOGLE_MAPS_API_KEY)
    else:
        error_message = task.get('error', '알 수 없는 오류') if task else '유효하지 않은 접근입니다.'
        # TODO: 더 나은 에러 페이지를 보여줄 수 있음
        return f"여행 경로 생성에 실패했습니다: {error_message}", 404

# --- 채팅 API: 이제 task_id를 받아 해당 코스에 대해 채팅하도록 수정 ---
@app.route('/api/chat', methods=['POST'])
def chat():
    
    data = request.json
    user_message = data.get("message")
    task_id = data.get("taskId") # 프론트엔드에서 taskId를 함께 보내줘야 함

    if not all([user_message, task_id]):
        return jsonify({"response": "메시지 또는 taskId가 누락되었습니다."}), 400
    
    task = agent_tasks.get(task_id)
    if not task or not task.get('success'):
        return jsonify({"response": "유효하지 않은 taskId입니다."}), 400

    current_course = task.get('course')
    bot_response = get_chatbot_response(user_message, current_course, task_id)
    
    # 코스 업데이트 정보 파싱
    update_info = parse_course_update(bot_response)
    course_updated = False
    updated_course = None
    
    if update_info:
        action = update_info.get('action')
        
        if action == 'add':
            # 장소 추가
            place_name = update_info.get('place_name')
            if place_name:
                try:
                    # Google Maps API로 장소 검색
                    gmaps = googlemaps.Client(key=Config.GOOGLE_MAPS_API_KEY)
                    location = current_course.get('location', '서울')
                    query = f"{location} {place_name}"
                    
                    places_result = gmaps.places(query=query)
                    if places_result.get('results'):
                        result = places_result['results'][0]
                        place_id = result.get('place_id')
                        
                        # 상세 정보 가져오기
                        if place_id:
                            fields = ['name', 'rating', 'formatted_address', 'photo', 'geometry/location']
                            details = gmaps.place(place_id, fields=fields)
                            if details and details.get('result'):
                                place_data = details['result']
                                
                                # 새 장소 정보 구성
                                new_place = {
                                    'name': place_data.get('name', place_name),
                                    'address': place_data.get('formatted_address', ''),
                                    'place_id': place_id,
                                    'rating': place_data.get('rating', 0),
                                    'category': '관광지',  # 기본값
                                    'coordinates': None
                                }
                                
                                if 'geometry' in place_data and 'location' in place_data['geometry']:
                                    loc = place_data['geometry']['location']
                                    new_place['coordinates'] = {'lat': loc['lat'], 'lng': loc['lng']}
                                
                                # 장소 추가 (직접 로직 호출)
                                current_course = task.get('course', {})
                                places = current_course.get('places', [])
                                sequence = current_course.get('sequence', [])
                                
                                new_index = len(places)
                                places.append(new_place)
                                insert_index = len(sequence)
                                sequence.insert(insert_index, new_index)
                                
                                current_course['places'] = places
                                current_course['sequence'] = sequence
                                task['course'] = current_course
                                updated_course = current_course
                                course_updated = True
                except Exception as e:
                    print(f"장소 추가 중 오류: {str(e)}")
        
        elif action == 'remove':
            # 장소 제거
            index = update_info.get('index')
            if index is not None:
                try:
                    # 장소 제거 (직접 로직 호출)
                    current_course = task.get('course', {})
                    places = current_course.get('places', [])
                    sequence = current_course.get('sequence', [])
                    
                    if index < len(sequence):
                        removed_place_idx = sequence[index]
                        sequence.pop(index)
                        places.pop(removed_place_idx)
                        sequence = [idx - 1 if idx > removed_place_idx else idx for idx in sequence]
                        
                        current_course['places'] = places
                        current_course['sequence'] = sequence
                        task['course'] = current_course
                        updated_course = current_course
                        course_updated = True
                except Exception as e:
                    print(f"장소 제거 중 오류: {str(e)}")
    
    # 응답에서 업데이트 태그 제거
    import re
    clean_response = re.sub(r'\[COURSE_UPDATE\].*?\[/COURSE_UPDATE\]', '', bot_response, flags=re.DOTALL).strip()
    
    return jsonify({
        "response": clean_response,
        "course_updated": course_updated,
        "course": updated_course if course_updated else None
    })

# --- 기타 API (필요 시 수정) ---
@app.route('/api/locations/<task_id>', methods=['GET'])
def get_locations(task_id):
    task = agent_tasks.get(task_id)
    if not task or not task.get('success'):
        return jsonify({"error": "유효하지 않은 taskId입니다."}), 404
    return jsonify(task.get('course', {}))

# --- 코스 업데이트 API ---
@app.route('/api/update-course/<task_id>', methods=['POST'])
def update_course(task_id):
    """챗봇을 통해 코스 업데이트"""
    task = agent_tasks.get(task_id)
    if not task or not task.get('success'):
        return jsonify({"error": "유효하지 않은 taskId입니다."}), 404
    
    data = request.json
    update_type = data.get('type')  # 'add', 'remove', 'replace'
    place_info = data.get('place')
    place_index = data.get('index')  # 제거할 장소의 인덱스
    
    current_course = task.get('course', {})
    places = current_course.get('places', [])
    sequence = current_course.get('sequence', [])
    
    try:
        if update_type == 'add':
            # 장소 추가
            if place_info:
                # 새 장소를 places에 추가
                new_index = len(places)
                places.append(place_info)
                # sequence에 추가 (맨 끝에 추가하거나 지정된 위치에)
                insert_index = data.get('insert_index', len(sequence))
                sequence.insert(insert_index, new_index)
                
                current_course['places'] = places
                current_course['sequence'] = sequence
                task['course'] = current_course
                
                return jsonify({
                    "success": True,
                    "message": "장소가 추가되었습니다.",
                    "course": current_course
                })
        
        elif update_type == 'remove':
            # 장소 제거
            if place_index is not None and place_index < len(sequence):
                # sequence에서 제거할 인덱스 찾기
                removed_place_idx = sequence[place_index]
                # sequence에서 제거
                sequence.pop(place_index)
                # places에서도 제거하고 sequence 인덱스 조정
                places.pop(removed_place_idx)
                # sequence의 인덱스들을 조정 (제거된 인덱스보다 큰 것들은 -1)
                sequence = [idx - 1 if idx > removed_place_idx else idx for idx in sequence]
                
                current_course['places'] = places
                current_course['sequence'] = sequence
                task['course'] = current_course
                
                return jsonify({
                    "success": True,
                    "message": "장소가 제거되었습니다.",
                    "course": current_course
                })
        
        elif update_type == 'replace':
            # 전체 코스 교체
            if 'course' in data:
                task['course'] = data['course']
                return jsonify({
                    "success": True,
                    "message": "코스가 업데이트되었습니다.",
                    "course": task['course']
                })
        
        return jsonify({"error": "잘못된 업데이트 타입입니다."}), 400
        
    except Exception as e:
        return jsonify({"error": f"코스 업데이트 중 오류: {str(e)}"}), 500

# --- 경로 안내 API ---
@app.route('/api/route-guide/<task_id>', methods=['POST'])
def get_route_guide(task_id):
    """경로 안내 생성 API"""
    import asyncio
    import re
    from agents import RoutingAgent
    from config.config import Config
    
    def clean_html_tags(text):
        """HTML 태그 제거"""
        return re.sub(r'<[^>]+>', '', text) if text else ""
    
    def build_guide_from_raw_steps(raw_steps):
        """원본 directions step을 사람이 읽기 쉬운 안내로 변환"""
        lines = []
        if not raw_steps:
            return lines
        
        for step in raw_steps:
            travel_mode = (step.get("travel_mode") or "").upper()
            distance_text = (step.get("distance", {}) or {}).get("text", "")
            duration_text = (step.get("duration", {}) or {}).get("text", "")
            instruction = clean_html_tags(step.get("html_instructions", ""))
            
            if travel_mode == "TRANSIT":
                transit_details = step.get("transit_details", {}) or {}
                line = transit_details.get("line", {}) or {}
                vehicle = line.get("vehicle", {}) or {}
                vehicle_type = (vehicle.get("type") or "").lower()
                line_short = line.get("short_name") or ""
                line_name = line.get("name") or ""
                dep_stop = (transit_details.get("departure_stop", {}) or {}).get("name", "")
                arr_stop = (transit_details.get("arrival_stop", {}) or {}).get("name", "")
                num_stops = transit_details.get("num_stops", 0)
                dep_time = (transit_details.get("departure_time", {}) or {}).get("text", "")
                arr_time = (transit_details.get("arrival_time", {}) or {}).get("text", "")
                
                if "bus" in vehicle_type or "버스" in line_name or "버스" in line_short:
                    label = line_short or line_name or "버스"
                    lines.append(f"🚌 {label} 버스 이용")
                elif "subway" in vehicle_type or "지하철" in line_name or "호선" in line_short:
                    label = line_short or line_name or "지하철"
                    lines.append(f"🚇 지하철 {label} 이용")
                else:
                    label = line_short or line_name or "대중교통"
                    lines.append(f"🚃 {label} 이용")
                
                if dep_stop:
                    lines.append(f"  • 승차: {dep_stop}")
                if arr_stop:
                    lines.append(f"  • 하차: {arr_stop}")
                if num_stops:
                    lines.append(f"  • {num_stops}개 정류장/역 이동")
                if dep_time:
                    lines.append(f"  • 출발 시간: {dep_time}")
                if arr_time:
                    lines.append(f"  • 도착 시간: {arr_time}")
            
            elif travel_mode == "WALKING":
                if duration_text or distance_text:
                    lines.append(f"🚶 도보 이동: {duration_text} ({distance_text})".strip())
                elif instruction:
                    lines.append(f"🚶 도보 이동")
                if instruction:
                    lines.append(f"  • {instruction}")
            else:
                if instruction:
                    line = f"• {instruction}"
                    if distance_text:
                        line += f" ({distance_text})"
                    if duration_text:
                        line += f" - {duration_text}"
                    lines.append(line)
        
        return [line for line in lines if line.strip()]
    
    task = agent_tasks.get(task_id)
    if not task or not task.get('success'):
        return jsonify({"error": "유효하지 않은 taskId입니다."}), 404
    
    course = task.get('course', {})
    places = course.get('places', [])
    sequence = course.get('sequence', [])
    transportation = course.get('transportation', '도보')
    visit_date = course.get('visit_date') or task.get('visit_date')
    visit_time_segment = task.get('visit_time') or '오후'
    
    if not places or not sequence:
        return jsonify({"error": "코스 정보가 없습니다."}), 400
    
    # 이동 수단을 Google Maps API 모드로 변환 (자전거 제외)
    mode_mapping = {
        '도보': 'walking',
        '자동차': 'driving',
        '지하철': 'transit',
        '버스': 'transit'
    }
    
    # transportation 문자열에서 이동 수단 추출 (우선순위: 대중교통 > 자동차 > 도보)
    # 사용자가 입력한 교통수단을 우선적으로 사용 (자전거는 완전히 제외)
    transport_mode = 'walking'  # 기본값
    preferred_modes = []
    transit_keywords = ['지하철', '버스', '대중교통', '대중 교통']
    
    # 사용자가 입력한 교통수단 우선순위대로 추출 (자전거 제외)
    if any(keyword in transportation for keyword in transit_keywords):
        preferred_modes.append('transit')
    if '자동차' in transportation:
        preferred_modes.append('driving')
    if '도보' in transportation:
        preferred_modes.append('walking')
    # 자전거는 완전히 제외됨
    
    # 사용자가 입력한 교통수단이 있으면 첫 번째 것을 사용
    # 단, 대중교통(transit)이 포함되어 있으면 무조건 transit을 primary로 설정
    if preferred_modes:
        # transit이 포함되어 있으면 transit을 우선 사용 (T Map API는 대중교통 미지원)
        if 'transit' in preferred_modes:
            transport_mode = 'transit'
            print(f"🚇 대중교통 포함 감지: transit 모드로 설정 (T Map API는 대중교통 미지원)")
        else:
            transport_mode = preferred_modes[0]
    else:
        # 입력이 없으면 기본값 사용 (자전거는 제외)
        transport_mode = 'walking'
    
    # sequence 순서대로 장소 재배열
    ordered_places = []
    for place_idx in sequence:
        if place_idx < len(places):
            ordered_places.append(places[place_idx])
    
    if len(ordered_places) < 2:
        return jsonify({"error": "경로 안내를 생성할 장소가 부족합니다."}), 400
    
    # 사용자가 입력한 시작일/시간을 기반으로 출발 일시(대중교통 기준)를 계산
    # visit_date 예시: "2026-02-01" 또는 "2026-02-01 ~ 2026-02-02"
    # visit_time_segment 예시: "오전", "오후", "저녁", "하루종일", "기타(08:00 - 12:00)"
    departure_time_str = None
    try:
        if visit_date:
            # 날짜 범위인 경우 첫 번째 날짜 사용
            first_date = visit_date.split("~")[0].strip()
            # 시간대에 따른 기본 시작 시간 설정
            if "기타" in str(visit_time_segment):
                # "기타(08:00 - 12:00)" 형식에서 첫 번째 시각 추출
                import re
                m = re.search(r"(\d{2}:\d{2})", str(visit_time_segment))
                start_hm = m.group(1) if m else "10:00"
            elif "오전" in str(visit_time_segment):
                start_hm = "10:00"
            elif "저녁" in str(visit_time_segment):
                start_hm = "18:00"
            elif "하루종일" in str(visit_time_segment):
                start_hm = "09:00"
            else:  # 기본: 오후
                start_hm = "14:00"
            departure_time_str = f"{first_date} {start_hm}"
    except Exception:
        departure_time_str = None

    # 기본 경로 안내 메시지 및 직선 경로 좌표 생성 함수 (API 실패 시에도 사용)
    def create_basic_guide():
        """
        기본 경로 안내 메시지와 단순 직선 경로 좌표를 생성합니다.
        Google Maps Directions API를 사용할 수 없을 때 사용되며,
        텍스트 안내와 함께 지도에 그릴 수 있는 최소한의 경로 정보(route_paths)를 제공합니다.
        """
        guide_text = f"🗺️ <strong>상세 경로 안내 ({transportation})</strong>\n\n"
        guide_text += f"<em>💡 Google Maps API를 사용한 상세 경로 정보를 가져올 수 없어 기본 안내를 제공합니다. 정확한 경로는 네비게이션 앱을 사용하시기 바랍니다.</em>\n\n"
        
        route_paths = []  # 각 구간별 직선 경로 좌표 정보
        
        for i in range(len(ordered_places) - 1):
            from_place = ordered_places[i]
            to_place = ordered_places[i + 1]
            from_name = from_place.get('name', '알 수 없음')
            to_name = to_place.get('name', '알 수 없음')
            from_addr = from_place.get('address', '')
            to_addr = to_place.get('address', '')
            
            # 좌표가 있으면 대략적인 거리 계산 및 직선 경로 좌표 생성 시도
            estimated_distance = ""
            path_coords = []
            if from_place.get('coordinates') and to_place.get('coordinates'):
                try:
                    from_coords = from_place['coordinates']
                    to_coords = to_place['coordinates']
                    import math
                    lat1, lon1 = float(from_coords.get('lat', 0)), float(from_coords.get('lng', 0))
                    lat2, lon2 = float(to_coords.get('lat', 0)), float(to_coords.get('lng', 0))
                    if lat1 and lon1 and lat2 and lon2:
                        R = 6371000  # 지구 반지름 (미터)
                        phi1 = math.radians(lat1)
                        phi2 = math.radians(lat2)
                        delta_phi = math.radians(lat2 - lat1)
                        delta_lambda = math.radians(lon2 - lon1)
                        a = math.sin(delta_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
                        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
                        distance_m = R * c
                        if distance_m < 1000:
                            estimated_distance = f" (약 {int(distance_m)}m)"
                        else:
                            estimated_distance = f" (약 {distance_m/1000:.1f}km)"
                        
                        # 직선 경로 좌표 (출발지 → 도착지)
                        path_coords = [
                            {"lat": lat1, "lng": lon1},
                            {"lat": lat2, "lng": lon2},
                        ]
                except:
                    pass
            
            guide_text += f"<strong>{i+1}. {from_name} → {to_name}{estimated_distance}</strong>\n"
            
            if transportation and '버스' in transportation:
                guide_text += f"   🚌 <strong>버스 안내:</strong>\n"
                guide_text += f"      • {from_name}에서 가장 가까운 버스 정류장으로 이동하세요.\n"
                if from_addr:
                    guide_text += f"      • 출발지 주소: {from_addr}\n"
                guide_text += f"      • {to_name} 방면 버스를 이용하세요. (네이버 지도나 카카오맵에서 정확한 버스 번호 확인 가능)\n"
                if to_addr:
                    guide_text += f"      • 도착지 주소: {to_addr}\n"
                guide_text += f"      • 💡 팁: 버스 정류장에서 실시간 도착 정보를 확인하세요.\n"
            elif transportation and '지하철' in transportation:
                guide_text += f"   🚇 <strong>지하철 안내:</strong>\n"
                guide_text += f"      • {from_name}에서 가장 가까운 지하철역으로 이동하세요.\n"
                if from_addr:
                    guide_text += f"      • 출발지 주소: {from_addr}\n"
                guide_text += f"      • {to_name} 방면 지하철을 이용하세요. (네이버 지도나 카카오맵에서 정확한 노선 확인 가능)\n"
                if to_addr:
                    guide_text += f"      • 도착지 주소: {to_addr}\n"
                guide_text += f"      • 💡 팁: 환승이 필요한 경우 역 내 안내판을 확인하세요.\n"
            elif transportation and ('대중교통' in transportation or '대중 교통' in transportation):
                guide_text += f"   🚌 <strong>대중교통 안내:</strong>\n"
                guide_text += f"      • {from_name}에서 가장 가까운 버스 정류장 또는 지하철역으로 이동하세요.\n"
                if from_addr:
                    guide_text += f"      • 출발지 주소: {from_addr}\n"
                guide_text += f"      • {to_name} 방향으로 가는 버스나 지하철을 이용하세요.\n"
                if to_addr:
                    guide_text += f"      • 도착지 주소: {to_addr}\n"
                guide_text += f"      • 💡 팁: 실시간 노선/도착 정보는 네이버 지도나 카카오맵에서 확인하세요.\n"
            elif transportation and '자동차' in transportation:
                guide_text += f"   🚗 <strong>자동차 안내:</strong>\n"
                guide_text += f"      • {from_name}에서 {to_name}로 자동차로 이동하세요.\n"
                if from_addr:
                    guide_text += f"      • 출발지 주소: {from_addr}\n"
                if to_addr:
                    guide_text += f"      • 도착지 주소: {to_addr}\n"
                guide_text += f"      • 💡 팁: 네비게이션 앱(네이버 지도, 카카오맵, 구글 맵)을 사용하여 실시간 교통 정보를 확인하세요.\n"
                if estimated_distance:
                    guide_text += f"      • 예상 거리: {estimated_distance.strip('()')}\n"
            else:
                guide_text += f"   🚶 <strong>도보 안내:</strong>\n"
                guide_text += f"      • {from_name}에서 {to_name}로 도보로 이동하세요.\n"
                if from_addr:
                    guide_text += f"      • 출발지 주소: {from_addr}\n"
                if to_addr:
                    guide_text += f"      • 도착지 주소: {to_addr}\n"
                if estimated_distance:
                    # 도보 시간 추정 (평균 시속 4km/h 기준)
                    try:
                        distance_km = float(estimated_distance.replace('(약 ', '').replace('km)', '').replace('m)', ''))
                        if 'm' in estimated_distance:
                            distance_km = distance_km / 1000
                        walking_minutes = int((distance_km / 4) * 60)
                        if walking_minutes > 0:
                            guide_text += f"      • 예상 소요 시간: 약 {walking_minutes}분\n"
                    except:
                        pass
                guide_text += f"      • 💡 팁: 보행자 전용 도로나 인도를 이용하세요.\n"
            
            guide_text += "\n"
            
            # 직선 경로 좌표가 있다면 route_paths에 추가
            if path_coords:
                route_paths.append([
                    {
                        "path": path_coords
                    }
                ])
        
        return guide_text, route_paths
    
    try:
        # Google Maps API를 사용한 상세 경로 안내 시도
        try:
            config = Config.get_agent_config()
            
            # Google Maps API 키 확인
            if not config.get("google_maps_api_key"):
                print("⚠️ Google Maps API 키가 없습니다. 기본 경로 안내를 제공합니다.")
                basic_guide, basic_paths = create_basic_guide()
                return jsonify({"guide": basic_guide, "route_paths": basic_paths})
            
            routing_agent = RoutingAgent(config=config)
            
            # 사용자가 입력한 교통수단 리스트 (우선순위 순서, 자전거 완전히 제외)
            user_transport_modes = preferred_modes if preferred_modes else [transport_mode]
            # 자전거 완전히 제외
            user_transport_modes = [m for m in user_transport_modes if m != 'bicycling']
            
            # 첫 번째 우선 교통수단 사용
            primary_mode = user_transport_modes[0] if user_transport_modes else 'walking'
            
            routing_input = {
                "places": ordered_places,
                "mode": primary_mode,
                "optimize_waypoints": False,  # sequence 순서 유지
                "preferred_modes": user_transport_modes,  # 대안 교통수단 리스트
                "user_transportation": transportation,  # 원본 입력값
                "departure_time": departure_time_str,  # 사용자가 입력한 시작일/시간 기반 출발 일시
            }
            
            # 비동기 실행
            async def run_routing():
                return await routing_agent.execute(routing_input)
            
            # 이벤트 루프 처리
            try:
                # 새 이벤트 루프 생성 시도
                route_result = asyncio.run(run_routing())
            except RuntimeError as e:
                if "asyncio.run() cannot be called from a running event loop" in str(e):
                    # 기존 이벤트 루프 사용
                    try:
                        loop = asyncio.get_event_loop()
                    except RuntimeError:
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                    route_result = loop.run_until_complete(routing_agent.execute(routing_input))
                else:
                    raise
            
            # 결과 확인
            if not route_result.get("success"):
                error_msg = route_result.get("error", "알 수 없는 오류")
                print(f"⚠️ 경로 정보 가져오기 실패: {error_msg}")
                # 기본 안내 제공
                return jsonify({"guide": create_basic_guide(), "route_paths": []})
            
            directions = route_result.get("directions", [])
            
            if not directions:
                print("⚠️ 경로 안내 정보가 비어있습니다. 기본 안내를 제공합니다.")
                return jsonify({"guide": create_basic_guide(), "route_paths": []})
            
            # directions에 에러가 있는지 확인 (일부 구간만 에러가 있어도 나머지는 상세 안내 제공)
            has_any_valid_directions = any(
                d.get("steps") and len(d.get("steps", [])) > 0
                for d in directions
            )
            
            # 모든 구간이 에러이거나 steps가 비어있을 때만 기본 안내 제공
            if not has_any_valid_directions:
                print(f"⚠️ 모든 구간의 경로 안내에 문제가 있습니다. 기본 안내를 제공합니다.")
                # 모든 구간이 실패했을 때만 기본 안내 제공
                basic_guide, basic_paths = create_basic_guide()
                return jsonify({"guide": basic_guide, "route_paths": basic_paths})
            
            # 경로 안내 텍스트 생성 및 경로 좌표 정보 수집
            guide_text = f"🗺️ <strong>상세 경로 안내 ({transportation})</strong>\n\n"
            route_paths = []  # 각 구간별 경로 좌표 정보
            
            for i, direction in enumerate(directions, 1):
                from_place = direction.get("from", "출발지")
                to_place = direction.get("to", "도착지")
                from_addr = direction.get("from_address", "")
                to_addr = direction.get("to_address", "")
                duration_text = direction.get("duration_text", "")
                distance_text = direction.get("distance_text", "")
                mode = direction.get("mode", transport_mode)
                steps = direction.get("steps", [])
                error = direction.get("error")
                
                # 디버깅: direction 데이터 확인
                print(f"\n=== 구간 {i} 데이터 확인 ===")
                print(f"from: {from_place}, to: {to_place}")
                print(f"mode: {mode}, steps 개수: {len(steps)}, error: {error}")
                if steps and len(steps) > 0:
                    first_step = steps[0]
                    print(f"첫 번째 step 키들: {list(first_step.keys())}")
                    if "formatted_instruction" in first_step:
                        print(f"첫 번째 step formatted_instruction: {first_step['formatted_instruction'][:100]}...")
                    else:
                        print(f"⚠️ 첫 번째 step에 formatted_instruction이 없습니다!")
                
                guide_text += f"<strong>{i}. {from_place} → {to_place}</strong>\n"
                
                # steps가 비어있으면 기본 안내만 제공 (더 상세하게)
                if not steps or len(steps) == 0:
                    print(f"⚠️ 구간 {i}의 steps가 비어있습니다. 기본 안내를 제공합니다.")
                    
                    # 에러 메시지가 있으면 표시
                    if error:
                        guide_text += f"      ⚠️ 경로 정보를 가져오는 중 문제가 발생했습니다: {error}\n"
                    
                    # 이동 수단별 상세 안내
                    if transportation and '버스' in transportation:
                        guide_text += f"   🚌 <strong>버스 안내:</strong>\n"
                        guide_text += f"      • {from_place}에서 가장 가까운 버스 정류장으로 이동하세요.\n"
                        if from_addr:
                            guide_text += f"      • 출발지 주소: {from_addr}\n"
                        guide_text += f"      • {to_place} 방면 버스를 이용하세요. (네이버 지도나 카카오맵에서 정확한 버스 번호 확인 가능)\n"
                        if to_addr:
                            guide_text += f"      • 도착지 주소: {to_addr}\n"
                        guide_text += f"      • 💡 팁: 버스 정류장에서 실시간 도착 정보를 확인하세요.\n"
                    elif transportation and '지하철' in transportation:
                        guide_text += f"   🚇 <strong>지하철 안내:</strong>\n"
                        guide_text += f"      • {from_place}에서 가장 가까운 지하철역으로 이동하세요.\n"
                        if from_addr:
                            guide_text += f"      • 출발지 주소: {from_addr}\n"
                        guide_text += f"      • {to_place} 방면 지하철을 이용하세요. (네이버 지도나 카카오맵에서 정확한 노선 확인 가능)\n"
                        if to_addr:
                            guide_text += f"      • 도착지 주소: {to_addr}\n"
                        guide_text += f"      • 💡 팁: 환승이 필요한 경우 역 내 안내판을 확인하세요.\n"
                    elif transportation and ('대중교통' in transportation or '대중 교통' in transportation):
                        guide_text += f"   🚌 <strong>대중교통 안내:</strong>\n"
                        guide_text += f"      • {from_place}에서 가장 가까운 버스 정류장 또는 지하철역으로 이동하세요.\n"
                        if from_addr:
                            guide_text += f"      • 출발지 주소: {from_addr}\n"
                        guide_text += f"      • {to_place} 방향으로 가는 버스나 지하철을 이용하세요.\n"
                        if to_addr:
                            guide_text += f"      • 도착지 주소: {to_addr}\n"
                        guide_text += f"      • 💡 팁: 실시간 노선/도착 정보는 네이버 지도나 카카오맵에서 확인하세요.\n"
                    elif transportation and '자동차' in transportation:
                        guide_text += f"   🚗 <strong>자동차 안내:</strong>\n"
                        guide_text += f"      • {from_place}에서 {to_place}로 자동차로 이동하세요.\n"
                        if from_addr:
                            guide_text += f"      • 출발지 주소: {from_addr}\n"
                        if to_addr:
                            guide_text += f"      • 도착지 주소: {to_addr}\n"
                        guide_text += f"      • 💡 팁: 네비게이션 앱을 사용하여 실시간 교통 정보를 확인하세요.\n"
                    else:
                        guide_text += f"   🚶 <strong>도보 안내:</strong>\n"
                        guide_text += f"      • {from_place}에서 {to_place}로 도보로 이동하세요.\n"
                        if from_addr:
                            guide_text += f"      • 출발지 주소: {from_addr}\n"
                        if to_addr:
                            guide_text += f"      • 도착지 주소: {to_addr}\n"
                        guide_text += f"      • 💡 팁: 보행자 전용 도로나 인도를 이용하세요.\n"
                    
                    guide_text += "\n"
                    continue  # 다음 구간으로
                
                # 정상적인 경우 상세 안내 제공 (error가 있어도 steps가 있으면 우선 사용)
                if error:
                    guide_text += f"   ⚠️ 일부 안내 정보에 제한이 있을 수 있습니다: {error}\n"
                if from_addr:
                    guide_text += f"   📍 출발지: {from_addr}\n"
                if to_addr:
                    guide_text += f"   📍 도착지: {to_addr}\n"
                guide_text += f"   ⏱ 소요 시간: {duration_text}\n"
                guide_text += f"   📏 거리: {distance_text}\n"
                
                # 사용된 교통수단 표시
                mode_display = {
                    "transit": "🚌 대중교통",
                    "driving": "🚗 자동차",
                    "walking": "🚶 도보"
                }
                actual_mode = mode_display.get(mode, f"이동 수단: {mode}")
                guide_text += f"   {actual_mode}\n"
                
                # 각 구간별 경로 좌표 정보 수집
                segment_paths = []
                for step in steps:
                    step_path = step.get("path", [])
                    if step_path and len(step_path) > 0:  # path가 있고 비어있지 않은 경우만
                        step_travel_mode = step.get("travel_mode", mode).upper()
                        step_transit_details = step.get("transit_details")
                        segment_paths.append({
                            "path": step_path,
                            "travel_mode": step_travel_mode,
                            "transit_details": step_transit_details
                        })
                
                # T Map API에서 반환한 route_coordinates가 있으면 우선 사용 (더 상세한 경로)
                route_coordinates = direction.get("route_coordinates", [])
                if route_coordinates and len(route_coordinates) > 0:
                    # route_coordinates를 하나의 경로로 추가
                    segment_paths.append({
                        "path": route_coordinates,
                        "travel_mode": mode.upper(),
                        "transit_details": None
                    })
                
                route_paths.append(segment_paths)
                
                # 디버깅: 경로 좌표 정보 로그
                total_coords_in_segment = sum(len(sp.get("path", [])) for sp in segment_paths)
                print(f"구간 {i} 경로 좌표 수집: {len(segment_paths)}개 step, 총 {total_coords_in_segment}개 좌표")
                
                # 이동 수단별 상세 안내
                # 원본 directions JSON(raw_steps)을 우선적으로 사용
                raw_steps = direction.get("raw_steps") or (direction.get("raw_leg", {}) or {}).get("steps", [])
                raw_lines = build_guide_from_raw_steps(raw_steps) if raw_steps else []
                
                if raw_lines:
                    guide_text += f"   📍 <strong>상세 이동 안내:</strong>\n"
                    for line in raw_lines:
                        guide_text += f"      {line}\n"
                    guide_text += "\n"
                else:
                    # formatted_instruction을 우선적으로 사용 (터미널에 출력된 상세 정보 활용)
                    has_formatted_instructions = any(step.get("formatted_instruction") for step in steps) if steps else False
                    
                    # formatted_instruction이 있으면 무조건 그것을 사용 (가장 상세한 정보)
                    if has_formatted_instructions:
                        guide_text += f"   📍 <strong>상세 이동 안내:</strong>\n"
                        # 모든 step의 formatted_instruction을 사용
                        for step_idx, step in enumerate(steps):
                            formatted_instruction = step.get("formatted_instruction")
                            if formatted_instruction:
                                print(f"  ✅ 구간 {i}, step {step_idx} formatted_instruction 사용")
                                # formatted_instruction의 모든 줄을 그대로 사용 (버스 번호, 정류장, 시간 등 모든 정보 포함)
                                transit_info_lines = formatted_instruction.split('\n')
                                for line in transit_info_lines:
                                    if line.strip():  # 빈 줄 제외
                                        guide_text += f"      {line.strip()}\n"
                            else:
                                # formatted_instruction이 없는 step은 기본 instruction 사용
                                instruction = clean_html_tags(step.get("instruction", ""))
                                distance_text_step = step.get("distance_text", "") or (step.get("distance", {}).get("text", "") if isinstance(step.get("distance"), dict) else "")
                                duration_text_step = step.get("duration_text", "") or (step.get("duration", {}).get("text", "") if isinstance(step.get("duration"), dict) else "")
                                if instruction:
                                    step_info = f"      • {instruction}"
                                    if distance_text_step:
                                        step_info += f" ({distance_text_step})"
                                    if duration_text_step:
                                        step_info += f" - {duration_text_step}"
                                    guide_text += f"{step_info}\n"
                        guide_text += "\n"
                    # formatted_instruction이 없을 때만 폴백 로직 사용
                    elif mode == "transit" and steps:
                        # mode가 transit이거나 steps에 transit 정보가 있으면 상세 안내
                        has_transit = (mode == "transit" or 
                                       any(step.get("travel_mode", "").upper() == "TRANSIT" for step in steps) or
                                       any(step.get("transit_details") for step in steps))
                        
                        if has_transit:
                            # 대중교통 상세 안내 (지하철 노선, 버스 번호 등)
                            guide_text += f"   🚌 <strong>대중교통 상세 안내:</strong>\n"
                            
                            transit_steps = []
                            max_transit_steps = 5  # 최대 5개 step만 처리 (context 길이 제한)
                            
                            for step_idx, step in enumerate(steps[:max_transit_steps]):  # 최대 5개만 처리
                                # formatted_instruction은 이미 위에서 처리했으므로 여기서는 건너뜀
                                transit_summary = step.get("transit_summary")
                                transit_detail = step.get("transit_details")
                                travel_mode = step.get("travel_mode", "").upper()
                                
                                # formatted_instruction이 있으면 이미 처리했으므로 건너뜀
                                if step.get("formatted_instruction"):
                                    continue
                            
                            # transit_summary가 있으면 사용
                            if transit_summary:
                                transit_type = transit_summary.get("type", "")
                                line_number = transit_summary.get("line_number", "")
                                departure_stop = transit_summary.get("departure_stop", "")
                                arrival_stop = transit_summary.get("arrival_stop", "")
                                num_stops = transit_summary.get("num_stops", 0)
                                
                                if transit_type == "bus" and line_number:
                                    transit_info = f"🚌 {line_number}번 버스 이용"
                                    if departure_stop:
                                        transit_info += f"\n      - 승차 정류장: {departure_stop}"
                                    if arrival_stop:
                                        transit_info += f"\n      - 하차 정류장: {arrival_stop}"
                                    if num_stops > 0:
                                        transit_info += f"\n      - {num_stops}개 정류장 이동"
                                    transit_steps.append(transit_info)
                                elif transit_type == "subway" and line_number:
                                    transit_info = f"🚇 지하철 {line_number} 이용"
                                    if departure_stop:
                                        transit_info += f"\n      - 승차역: {departure_stop}"
                                    if arrival_stop:
                                        transit_info += f"\n      - 하차역: {arrival_stop}"
                                    if num_stops > 0:
                                        transit_info += f"\n      - {num_stops}개 역 이동"
                                    transit_steps.append(transit_info)
                            
                            # 기존 로직 (폴백)
                            elif transit_detail:
                                import re
                                # 대중교통 상세 정보 추출
                                line = transit_detail.get("line", {}) or {}
                                vehicle = line.get("vehicle", {}) or {}
                                vehicle_type = vehicle.get("type", "").lower() if vehicle.get("type") else ""
                                
                                departure_stop = transit_detail.get("departure_stop", {}) or {}
                                arrival_stop = transit_detail.get("arrival_stop", {}) or {}
                                departure_stop_name = departure_stop.get("name", "") if isinstance(departure_stop, dict) else ""
                                arrival_stop_name = arrival_stop.get("name", "") if isinstance(arrival_stop, dict) else ""
                                num_stops = transit_detail.get("num_stops", 0)
                                
                                line_name = line.get("name", "") or ""
                                line_short_name = line.get("short_name", "") or ""
                                
                                # 출발/도착 시간 정보
                                departure_time_obj = transit_detail.get("departure_time", {}) or {}
                                arrival_time_obj = transit_detail.get("arrival_time", {}) or {}
                                departure_time = departure_time_obj.get("text", "") if isinstance(departure_time_obj, dict) else ""
                                arrival_time = arrival_time_obj.get("text", "") if isinstance(arrival_time_obj, dict) else ""
                                
                                # 지하철인 경우 판단 (더 관대한 조건)
                                is_subway = (
                                    vehicle_type == "subway" or 
                                    "subway" in vehicle_type or 
                                    "지하철" in line_name or 
                                    "호선" in line_name or 
                                    "호선" in line_short_name or
                                    "line" in line_name.lower() or
                                    "line" in line_short_name.lower()
                                )
                                
                                # 버스인 경우 판단 (더 관대한 조건)
                                is_bus = (
                                    vehicle_type == "bus" or 
                                    "bus" in vehicle_type or 
                                    "버스" in line_name or
                                    "버스" in line_short_name or
                                    (not is_subway and line_short_name and re.search(r'\d+', line_short_name))  # 숫자가 포함된 경우 버스로 간주
                                )
                                
                                if is_subway:
                                    # 노선명 추출 (예: "2호선", "Line 2" 등)
                                    subway_line = line_short_name or line_name
                                    # "Line 2" -> "2호선" 변환 시도
                                    if "line" in subway_line.lower():
                                        line_num_match = re.search(r'(\d+)', subway_line)
                                        if line_num_match:
                                            subway_line = f"{line_num_match.group(1)}호선"
                                    
                                    transit_info = f"🚇 <strong>지하철 {subway_line}</strong>"
                                    if departure_stop_name:
                                        transit_info += f"\n      - 출발역: {departure_stop_name}"
                                    if arrival_stop_name:
                                        transit_info += f"\n      - 도착역: {arrival_stop_name}"
                                    if num_stops > 0:
                                        transit_info += f"\n      - {num_stops}개 역 이동"
                                    if departure_time:
                                        transit_info += f"\n      - 출발 시간: {departure_time}"
                                    if arrival_time:
                                        transit_info += f"\n      - 도착 시간: {arrival_time}"
                                    
                                    transit_steps.append(transit_info)
                                
                                elif is_bus:
                                    # 버스 번호 추출
                                    bus_number = line_short_name or line_name
                                    if not bus_number:
                                        bus_number = "버스"
                                    else:
                                        # 버스 번호 정리 (예: "버스 123" -> "123번", "Bus 123" -> "123번")
                                        bus_num_match = re.search(r'(\d+)', bus_number)
                                        if bus_num_match:
                                            bus_number = f"{bus_num_match.group(1)}번"
                                        elif "버스" not in bus_number:
                                            bus_number = f"{bus_number}번"
                                    
                                    transit_info = f"🚌 <strong>{bus_number} 버스</strong>"
                                    if departure_stop_name:
                                        transit_info += f"\n      - 승차 정류장: {departure_stop_name}"
                                    if arrival_stop_name:
                                        transit_info += f"\n      - 하차 정류장: {arrival_stop_name}"
                                    if num_stops > 0:
                                        transit_info += f"\n      - {num_stops}개 정류장 이동"
                                    if departure_time:
                                        transit_info += f"\n      - 출발 시간: {departure_time}"
                                    if arrival_time:
                                        transit_info += f"\n      - 도착 시간: {arrival_time}"
                                    
                                    transit_steps.append(transit_info)
                                
                                # 기타 대중교통 (transit_detail이 있지만 버스/지하철이 아닌 경우)
                                elif line_name or line_short_name:
                                    transit_info = f"🚃 <strong>{line_name or line_short_name}</strong>"
                                    if departure_stop_name:
                                        transit_info += f"\n      - 출발: {departure_stop_name}"
                                    if arrival_stop_name:
                                        transit_info += f"\n      - 도착: {arrival_stop_name}"
                                    if num_stops > 0:
                                        transit_info += f"\n      - {num_stops}개 정거장 이동"
                                    if departure_time:
                                        transit_info += f"\n      - 출발 시간: {departure_time}"
                                    if arrival_time:
                                        transit_info += f"\n      - 도착 시간: {arrival_time}"
                                    transit_steps.append(transit_info)
                                
                                # transit_detail이 있지만 정보가 부족한 경우
                                elif departure_stop_name or arrival_stop_name:
                                    transit_info = "🚌 <strong>대중교통 이용</strong>"
                                    if departure_stop_name:
                                        transit_info += f"\n      - 출발: {departure_stop_name}"
                                    if arrival_stop_name:
                                        transit_info += f"\n      - 도착: {arrival_stop_name}"
                                    transit_steps.append(transit_info)
                            
                            # 대중교통 step이지만 transit_details가 없는 경우 (도보 이동 등)
                            elif travel_mode == "transit" or (step.get("instruction") and ("버스" in step.get("instruction", "") or "지하철" in step.get("instruction", "") or "지하철역" in step.get("instruction", "") or "정류장" in step.get("instruction", ""))):
                                instruction = clean_html_tags(step.get("instruction", ""))
                                distance_text = step.get("distance_text", "") or (step.get("distance", {}).get("text", "") if isinstance(step.get("distance"), dict) else "")
                                duration_text = step.get("duration_text", "") or (step.get("duration", {}).get("text", "") if isinstance(step.get("duration"), dict) else "")
                                
                                if instruction:
                                    step_info = f"      • {instruction}"
                                    if distance_text:
                                        step_info += f" ({distance_text})"
                                    if duration_text:
                                        step_info += f" - {duration_text}"
                                    transit_steps.append(step_info)
                    
                        # 상세 정보가 있으면 표시, 없으면 일반 안내
                        if transit_steps:
                            # 최대 10개까지 표시 (이미지에 보이는 상세 안내 포함)
                            for transit_info in transit_steps[:10]:
                                # 줄바꿈 처리
                                if isinstance(transit_info, str):
                                    # 모든 상세 정보를 보여주기 위해 줄 제한 제거
                                    transit_info_lines = transit_info.split('\n')
                                    for line in transit_info_lines:
                                        if line.strip():  # 빈 줄 제외
                                            guide_text += f"      {line.strip()}\n"
                                else:
                                    guide_text += f"      {str(transit_info)}\n"
                        else:
                            # 폴백: transit_details가 없는 경우 디버깅 및 일반 안내
                            # 디버깅: transit_details가 있는 step이 있는지 확인
                            has_transit_details = any(step.get("transit_details") for step in steps)
                            has_formatted = any(step.get("formatted_instruction") for step in steps)
                            
                            print(f"  ⚠️ 구간 {i} transit_steps가 비어있음. has_transit_details={has_transit_details}, has_formatted={has_formatted}")
                            
                            if has_formatted:
                                # formatted_instruction이 있으면 강제로 사용
                                guide_text += f"   📍 <strong>상세 이동 안내:</strong>\n"
                                for step_idx, step in enumerate(steps[:5]):  # 최대 5개까지
                                    formatted_instruction = step.get("formatted_instruction")
                                    if formatted_instruction:
                                        transit_info_lines = formatted_instruction.split('\n')
                                        # 모든 정보 표시
                                        for line in transit_info_lines:
                                            if line.strip():
                                                guide_text += f"      {line.strip()}\n"
                            elif has_transit_details:
                                # transit_details는 있지만 파싱에 실패한 경우 - instruction에서 유용한 정보 추출
                                guide_text += f"   🚌 <strong>대중교통 안내:</strong>\n"
                                
                                # 모든 step의 instruction을 확인하여 유용한 정보 추출
                                useful_steps = []
                                for step in steps[:10]:  # 최대 10개 step 확인
                                    instruction = clean_html_tags(step.get("instruction", ""))
                                    distance_text = step.get("distance_text", "") or (step.get("distance", {}).get("text", "") if isinstance(step.get("distance"), dict) else "")
                                    duration_text = step.get("duration_text", "") or (step.get("duration", {}).get("text", "") if isinstance(step.get("duration"), dict) else "")
                                    
                                    if instruction:
                                        # 버스 번호, 지하철 노선, 정류장/역 이름 등 유용한 정보 추출
                                        import re
                                        # 버스 번호 추출 (예: "123번", "버스 456")
                                        bus_match = re.search(r'(\d+)\s*번', instruction)
                                        # 지하철 노선 추출 (예: "2호선", "Line 2")
                                        subway_match = re.search(r'(\d+)\s*호선|Line\s*(\d+)', instruction, re.IGNORECASE)
                                        # 정류장/역 이름 추출
                                        stop_match = re.search(r'([가-힣]+역|[가-힣]+정류장|[가-힣]+역사)', instruction)
                                        
                                        step_info = instruction
                                        if bus_match:
                                            bus_num = bus_match.group(1)
                                            step_info = f"🚌 {bus_num}번 버스: {instruction}"
                                        elif subway_match:
                                            line_num = subway_match.group(1) or subway_match.group(2)
                                            step_info = f"🚇 {line_num}호선: {instruction}"
                                        
                                        if distance_text:
                                            step_info += f" ({distance_text})"
                                        if duration_text:
                                            step_info += f" - {duration_text}"
                                        
                                        useful_steps.append(step_info)
                                
                                if useful_steps:
                                    # 유용한 정보가 있으면 표시 (최대 5개)
                                    for step_info in useful_steps[:5]:
                                        guide_text += f"      {step_info}\n"
                                else:
                                    # 유용한 정보가 없으면 기본 안내
                                    guide_text += f"      • {from_place}에서 {to_place}로 대중교통을 이용하세요.\n"
                                    if duration_text:
                                        guide_text += f"      • 예상 소요 시간: {duration_text}\n"
                                    if distance_text:
                                        guide_text += f"      • 거리: {distance_text}\n"
                    elif mode == "walking":
                        guide_text += f"   🚶 <strong>도보 안내:</strong>\n"
                        if steps:
                            # 포맷팅된 instruction이 있으면 우선 사용 (더 많은 step 표시)
                            formatted_steps = []
                            displayed_count = 0
                            max_steps = 8  # 최대 8개 step 표시 (더 상세한 안내)
                            
                            for step in steps:
                                if displayed_count >= max_steps:
                                    break
                                
                                formatted_instruction = step.get("formatted_instruction")
                                instruction = clean_html_tags(step.get("instruction", ""))
                                distance_text = step.get("distance_text", "") or (step.get("distance", {}).get("text", "") if isinstance(step.get("distance"), dict) else "")
                                duration_text = step.get("duration_text", "") or (step.get("duration", {}).get("text", "") if isinstance(step.get("duration"), dict) else "")
                                
                                if formatted_instruction:
                                    # formatted_instruction의 모든 줄 사용 (너무 길지 않은 경우)
                                    lines = formatted_instruction.split('\n')
                                    for line in lines:
                                        if line.strip() and displayed_count < max_steps:
                                            step_info = f"      {line.strip()}"
                                            if distance_text and displayed_count == 0:  # 첫 번째 step에만 거리 정보 추가
                                                step_info += f" ({distance_text})"
                                            formatted_steps.append(step_info)
                                            displayed_count += 1
                                elif instruction:
                                    # instruction이 있으면 상세 정보 포함
                                    step_info = f"      • {instruction}"
                                    if distance_text:
                                        step_info += f" ({distance_text})"
                                    if duration_text:
                                        step_info += f" - {duration_text}"
                                    formatted_steps.append(step_info)
                                    displayed_count += 1
                            
                            if formatted_steps:
                                # 모든 formatted_steps 표시
                                for step_info in formatted_steps:
                                    guide_text += f"{step_info}\n"
                            else:
                                # steps가 있지만 정보가 없는 경우
                                guide_text += f"      • {from_place}에서 {to_place}로 도보로 이동하세요.\n"
                                if duration_text:
                                    guide_text += f"      • 예상 소요 시간: {duration_text}\n"
                                if distance_text:
                                    guide_text += f"      • 거리: {distance_text}\n"
                        else:
                            guide_text += f"      • {from_place}에서 {to_place}로 도보로 이동하세요.\n"
                    elif mode == "driving":
                        guide_text += f"   🚗 <strong>자동차 안내:</strong>\n"
                        if steps:
                            # 자동차 안내는 주요 경로 정보를 더 많이 표시 (최대 5개 step)
                            displayed_count = 0
                            max_steps = 5  # 최대 5개 step 표시
                            
                            for step in steps:
                                if displayed_count >= max_steps:
                                    break
                                
                                formatted_instruction = step.get("formatted_instruction")
                                instruction = clean_html_tags(step.get("instruction", ""))
                                distance_text = step.get("distance_text", "") or (step.get("distance", {}).get("text", "") if isinstance(step.get("distance"), dict) else "")
                                
                                # 주요 경로 정보만 표시 (고속도로 진입, 주요 교차로, 목적지 근처 등)
                                if formatted_instruction:
                                    # formatted_instruction 사용
                                    lines = formatted_instruction.split('\n')
                                    for line in lines[:2]:  # 각 step당 최대 2줄
                                        if line.strip() and displayed_count < max_steps:
                                            guide_text += f"      {line.strip()}\n"
                                            displayed_count += 1
                                elif instruction:
                                    # 중요한 instruction만 필터링 (고속도로, 톨게이트, 주요 도로명 등)
                                    important_keywords = ['고속도로', '톨게이트', 'IC', 'JC', '교차로', '로터리', '대교', '터널', '목적지', '도착']
                                    is_important = any(keyword in instruction for keyword in important_keywords)
                                    
                                    # 중요한 정보이거나 첫 번째/마지막 step이면 표시
                                    if is_important or displayed_count == 0 or displayed_count >= max_steps - 1:
                                        step_info = f"      • {instruction}"
                                        if distance_text and displayed_count == 0:  # 첫 번째 step에만 거리 정보
                                            step_info += f" ({distance_text})"
                                        guide_text += f"{step_info}\n"
                                        displayed_count += 1
                            
                            # step이 없거나 부족한 경우 기본 안내
                            if displayed_count == 0:
                                guide_text += f"      • {from_place}에서 {to_place}로 자동차로 이동하세요.\n"
                                if duration_text:
                                    guide_text += f"      • 예상 소요 시간: {duration_text}\n"
                                if distance_text:
                                    guide_text += f"      • 거리: {distance_text}\n"
                                guide_text += f"      • 💡 팁: 네비게이션 앱을 사용하여 실시간 교통 정보를 확인하세요.\n"
                        else:
                            guide_text += f"      • {from_place}에서 {to_place}로 자동차로 이동하세요.\n"
                            if duration_text:
                                guide_text += f"      • 예상 소요 시간: {duration_text}\n"
                            if distance_text:
                                guide_text += f"      • 거리: {distance_text}\n"
                
                guide_text += "\n"
            
            # 경로 좌표 정보와 함께 반환
            total_paths = sum(len(segment) for segment in route_paths)
            total_coords = sum(
                sum(len(step.get("path", [])) for step in segment)
                for segment in route_paths
            )
            print(f"✅ 경로 안내 생성 완료: {len(route_paths)}개 구간, {total_paths}개 step, 총 {total_coords}개 좌표")
            
            return jsonify({
                "guide": guide_text,
                "route_paths": route_paths  # 각 구간별 step 경로 좌표 정보
            })
            
        except Exception as api_error:
            # Google Maps API 호출 실패 시 기본 안내 제공
            print(f"⚠️ Google Maps API 호출 실패: {api_error}")
            return jsonify({"guide": create_basic_guide(), "route_paths": []})
        
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        print(f"❌ 경로 안내 생성 중 오류 발생:")
        print(error_detail)
        # 오류 발생 시에도 기본 안내 제공
        try:
            basic_guide = create_basic_guide()
            return jsonify({"guide": basic_guide, "route_paths": []})
        except:
            # 기본 안내 생성도 실패한 경우
            return jsonify({"error": f"경로 안내 생성 중 오류: {str(e)}"}), 500

# 저장된 장소 파일 경로
SAVED_PLACES_FILE = 'saved_places.json'

def load_saved_places():
    """저장된 장소 목록 불러오기"""
    if os.path.exists(SAVED_PLACES_FILE):
        try:
            with open(SAVED_PLACES_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return []
    return []

def normalize_category(category):
    """카테고리를 한글로 정규화"""
    if not category:
        return '기타'
    
    category_lower = category.lower()
    category_mapping = {
        'tourist_attraction': '관광지',
        'restaurant': '식당',
        'cafe': '카페',
        'shopping_mall': '쇼핑',
        'lodging': '숙소',
        'activity': '활동',
        '관광지': '관광지',
        '식당': '식당',
        '카페': '카페',
        '쇼핑': '쇼핑',
        '숙소': '숙소',
        '활동': '활동'
    }
    
    # 정확한 매칭
    if category in category_mapping:
        return category_mapping[category]
    
    # 부분 매칭 (영어 카테고리)
    for eng_cat, kor_cat in category_mapping.items():
        if eng_cat in category_lower or category_lower in eng_cat:
            return kor_cat
    
    return category  # 매칭되지 않으면 원본 반환

def save_places(places):
    """장소 목록 저장 (카테고리 정규화 포함)"""
    # 카테고리를 한글로 정규화
    normalized_places = []
    for place in places:
        normalized_place = place.copy()
        normalized_place['category'] = normalize_category(place.get('category', ''))
        normalized_places.append(normalized_place)
    
    with open(SAVED_PLACES_FILE, 'w', encoding='utf-8') as f:
        json.dump(normalized_places, f, ensure_ascii=False, indent=2)

@app.route('/api/search-place', methods=['POST'])
def search_place():
    """장소 검색 API"""
    try:
        data = request.json
        query = data.get('query', '').strip()
        
        if not query:
            return jsonify({'error': '검색어를 입력해주세요.'}), 400
        
        # Google Maps API 클라이언트 초기화
        gmaps = googlemaps.Client(key=Config.GOOGLE_MAPS_API_KEY)
        
        # Places API로 검색 (텍스트 검색)
        # find_place 또는 places 메서드 사용
        places_result = None
        error_msg = None
        
        try:
            # 방법 1: find_place 사용 (더 정확한 텍스트 검색)
            find_result = gmaps.find_place(input=query, input_type='textquery', fields=['place_id', 'name', 'formatted_address', 'geometry', 'rating', 'types'])
            if find_result.get('status') == 'OK' and find_result.get('candidates'):
                # find_place 결과를 places 형식으로 변환
                candidates = find_result.get('candidates', [])
                places_result = {'results': []}
                
                # 각 후보에 대해 상세 정보 가져오기
                for candidate in candidates[:10]:  # 최대 10개
                    place_id = candidate.get('place_id')
                    if place_id:
                        try:
                            # Place Details API로 상세 정보 가져오기
                            details = gmaps.place(place_id, fields=['name', 'formatted_address', 'geometry', 'rating', 'types', 'place_id'])
                            if details.get('result'):
                                places_result['results'].append(details['result'])
                        except Exception as e:
                            print(f"⚠️ Place Details API 호출 실패 (place_id: {place_id}): {e}")
                            # 상세 정보 없이 기본 정보만 사용
                            places_result['results'].append(candidate)
        except Exception as e:
            error_msg = f"find_place 실패: {str(e)}"
            print(f"⚠️ {error_msg}")
        
        # 방법 2: find_place가 실패하면 places 메서드 사용 (폴백)
        if not places_result or not places_result.get('results'):
            try:
                # places 메서드는 query 파라미터를 사용
                places_result = gmaps.places(query=query)
            except Exception as e:
                error_msg = f"places 검색 실패: {str(e)}"
                print(f"⚠️ {error_msg}")
                return jsonify({'error': f'장소 검색에 실패했습니다: {error_msg}'}), 500
        
        # API 응답 상태 확인
        if places_result.get('status') and places_result.get('status') != 'OK':
            status = places_result.get('status')
            error_message = places_result.get('error_message', '알 수 없는 오류')
            print(f"⚠️ Google Places API 오류: {status} - {error_message}")
            return jsonify({'error': f'장소 검색에 실패했습니다: {status} - {error_message}'}), 500
        
        if not places_result.get('results'):
            return jsonify({'places': []})
        
        # 결과 포맷팅
        places = []
        for result in places_result['results'][:10]:  # 최대 10개
            place_data = {
                'name': result.get('name', ''),
                'address': result.get('formatted_address', ''),
                'place_id': result.get('place_id', ''),
                'rating': result.get('rating', 0),
                'category': result.get('types', [''])[0] if result.get('types') else '',
            }
            
            # 좌표 정보 추가
            if 'geometry' in result and 'location' in result['geometry']:
                loc = result['geometry']['location']
                place_data['lat'] = loc.get('lat')
                place_data['lng'] = loc.get('lng')
            
            places.append(place_data)
        
        print(f"✅ 장소 검색 성공: '{query}' -> {len(places)}개 결과")
        return jsonify({'places': places})
    except Exception as e:
        error_detail = str(e)
        print(f"❌ 장소 검색 API 오류: {error_detail}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'장소 검색 중 오류가 발생했습니다: {error_detail}'}), 500

@app.route('/api/save-place', methods=['POST'])
def save_place():
    """장소 저장 API"""
    try:
        data = request.json
        place_id = data.get('place_id')
        
        if not place_id:
            return jsonify({'error': 'place_id가 필요합니다.'}), 400
        
        saved_places = load_saved_places()
        
        # 이미 저장된 장소인지 확인
        if any(p.get('place_id') == place_id for p in saved_places):
            return jsonify({'error': '이미 저장된 장소입니다.'}), 400
        
        # 장소 정보 저장 (카테고리 정규화)
        raw_category = data.get('category', '')
        normalized_category = normalize_category(raw_category)
        
        place_data = {
            'name': data.get('name', ''),
            'address': data.get('address', ''),
            'place_id': place_id,
            'rating': data.get('rating', 0),
            'category': normalized_category,  # 정규화된 카테고리 저장
            'lat': data.get('lat'),
            'lng': data.get('lng')
        }
        
        saved_places.append(place_data)
        save_places(saved_places)
        
        print(f"✅ 장소 저장 완료: {place_data['name']} (카테고리: {raw_category} -> {normalized_category})")
        
        return jsonify({'success': True, 'message': '장소가 저장되었습니다.'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/saved-places', methods=['GET'])
def get_saved_places():
    """저장된 장소 목록 조회 API"""
    try:
        places = load_saved_places()
        return jsonify({'places': places})
    except Exception as e:
        return jsonify({'error': str(e), 'places': []}), 500

@app.route('/api/saved-places/<place_id>', methods=['DELETE'])
def delete_saved_place(place_id):
    """저장된 장소 삭제 API"""
    try:
        saved_places = load_saved_places()
        saved_places = [p for p in saved_places if p.get('place_id') != place_id]
        save_places(saved_places)
        return jsonify({'success': True, 'message': '장소가 삭제되었습니다.'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# (text_wrap 헬퍼 함수는 이전과 동일하게 유지)
def text_wrap(text, font, max_width, draw):
    lines = []
    words = text.split(' ')
    current_line = ''
    for word in words:
        word_width = draw.textlength(word, font)
        if word_width > max_width:
            temp_word = ''
            for char in word:
                if draw.textlength(temp_word + char, font) > max_width:
                    lines.append(temp_word)
                    temp_word = char
                else:
                    temp_word += char
            if temp_word: lines.append(temp_word)
            continue
        if draw.textlength(current_line + ' ' + word, font) <= max_width:
            current_line += ' ' + word
        else:
            lines.append(current_line.strip())
            current_line = word
    if current_line: lines.append(current_line.strip())
    return lines


@app.route('/api/generate-card/<task_id>')
def generate_travel_card(task_id):
    course_data = agent_tasks.get(task_id, {}).get('course')
    if not course_data:
        return "코스 정보를 찾을 수 없습니다.", 404

    try:
        # --- 기본 설정 ---
        IMG_WIDTH = 1080
        PADDING = 90 # 여백을 조금 더 줍니다.
        
        template = Image.open("static/images/card_template.png")
        draw = ImageDraw.Draw(template)

        font_path = "static/fonts/GowunDodum-Regular.ttf"
        
        # --- [수정] 템플릿에 맞게 폰트 크기 및 간격 재조정 ---
        title_font = ImageFont.truetype(font_path, size=90)
        subtitle_font = ImageFont.truetype(font_path, size=55)
        
        sequence = course_data.get('sequence', [])
        num_places = len(sequence)
        
        if num_places > 6:
            place_font_size = 44
            line_height_ratio = 1.4
            item_gap = 20  # [수정] 장소 간 간격을 더 좁게
        else:
            place_font_size = 50
            line_height_ratio = 1.5
            item_gap = 30  # [수정] 장소 간 간격을 더 좁게

        place_font = ImageFont.truetype(font_path, size=place_font_size)
        line_height = place_font.getbbox("A")[3] * line_height_ratio

        # --- 텍스트 그리기 ---
        
        # 1. 타이틀 (위치를 살짝 위로 조정)
        location = course_data.get("location", "")
        theme = course_data.get("theme", "추천 코스")
        draw.text((PADDING, 180), location, font=title_font, fill="#333333")
        draw.text((PADDING, 300), theme, font=subtitle_font, fill="#555555")

        # 2. 코스 목록 (시작 위치 조정)
        y_position = 480 # 타이틀과 간격을 더 줍니다.
        places = course_data.get('places', [])
        
        number_x = PADDING
        text_x = number_x + 70
        max_text_width = IMG_WIDTH - text_x - PADDING
        
        for i, place_idx in enumerate(sequence):
            # [수정] 템플릿 하단 로고와 겹치지 않도록 안전 여백 확보
            if y_position > template.height - 300:
                draw.text((number_x, y_position), "...", font=place_font, fill="#888888")
                break

            if place_idx < len(places):
                place_name = places[place_idx]['name']
                draw.text((number_x, y_position), f"{i+1}.", font=place_font, fill="#111111")
                
                wrapped_lines = text_wrap(place_name, place_font, max_text_width, draw)
                
                temp_y = y_position
                for line in wrapped_lines:
                    draw.text((text_x, temp_y), line, font=place_font, fill="#111111")
                    temp_y += line_height
                
                y_position = temp_y if len(wrapped_lines) > 1 else y_position + line_height
                y_position += item_gap

        # --- 이미지 파일로 변환 및 전송 ---
        img_io = io.BytesIO()
        template.save(img_io, 'PNG', quality=95)
        img_io.seek(0)

        return send_file(
            img_io,
            mimetype='image/png',
            as_attachment=True,
            download_name=f'RoutePick_{location}.png'
        )

    except FileNotFoundError:
        return "이미지 생성에 필요한 파일(폰트/템플릿)을 찾을 수 없습니다.", 500
    except Exception as e:
        print(f"이미지 생성 오류: {e}")
        return "이미지를 생성하는 중 오류가 발생했습니다.", 500
    
# 기존의 단계별 입력 방식은 이제 사용되지 않으므로 주석 처리하거나 삭제 가능
# @app.route('/', methods=['GET', 'POST']) ...

@app.route('/')
def index():
    """메인 페이지"""
    return render_template('index.html')

if __name__ == '__main__':
    try:
        print("=" * 50)
        print("RoutePick 서버를 시작합니다...")
        print("=" * 50)
        app.run(debug=True, port=5000, host='0.0.0.0')
    except OSError as e:
        if "Address already in use" in str(e) or "포트가 이미 사용 중" in str(e):
            print(f"\n오류: 포트 5000이 이미 사용 중입니다.")
            print("다른 포트를 사용하거나 기존 프로세스를 종료해주세요.")
        else:
            print(f"\n오류 발생: {e}")
            import traceback
            traceback.print_exc()
    except Exception as e:
        print(f"\n예상치 못한 오류 발생: {e}")
        import traceback
        traceback.print_exc()