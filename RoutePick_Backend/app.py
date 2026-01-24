import asyncio
import threading
import json
import os
from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_cors import CORS
from chatbot import get_chatbot_response, clear_chat_history, parse_course_update  # chatbot.py가 course 객체를 인자로 받도록 수정 필요
from agents import SearchAgent, PlanningAgent
from config.config import Config
import uuid
import googlemaps

app = Flask(__name__)
app.secret_key = 'string_secret_key'
CORS(app)

# 여러 사용자의 작업 상태와 결과를 저장하는 '개인 사물함'
agent_tasks = {}

async def execute_Agents(task_id, input_data):
    global agent_tasks
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
        
        print(f"\n✅ 검색 완료: {len(places)}개의 장소를 찾았습니다.\n")
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
        print("🧠 [Step 2] PlanningAgent: 코스 제작 중...")
        print()
        
        planning_agent = PlanningAgent(config=config)
        
        # 사용자 선호도 구성
        user_preferences = {
            "theme": input_data["theme"],
            "group_size": input_data.get("group_size", "1명"),
            "visit_date": input_data.get("visit_date") or "오늘",
            "visit_time": input_data.get("visit_time") or "오후",
            "transportation": input_data.get("transportation") or "도보"
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
            
            for idx, place_idx in enumerate(sequence, 1):
                if place_idx < len(places_list):
                    place = places_list[place_idx]
                    duration = estimated_duration.get(str(place_idx), "정보 없음")
                    
                    print(f"\n{idx}. {place.get('name', '알 수 없음')}")
                    print(f"   - 카테고리: {place.get('category', 'N/A')}")
                    print(f"   - 체류 시간: {duration}분")
                    
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
        agent_tasks[task_id].update({"done": True, "success": True, "course": final_course})

    except Exception as e:
        print(f"\n❌ [{task_id}] 에이전트 실행 중 오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()
        agent_tasks[task_id].update({"done": True, "success": False, "error": str(e)})

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
        "transportation": ", ".join(data.get("transportation", []) + ([data.get("customTransport")] if data.get("customTransport") else []))
    }
    
    agent_tasks[task_id] = {"done": False, "success": False, "course": None}
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
        "error": task_status.get("error")
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
    
    task = agent_tasks.get(task_id)
    if not task or not task.get('success'):
        return jsonify({"error": "유효하지 않은 taskId입니다."}), 404
    
    course = task.get('course', {})
    places = course.get('places', [])
    sequence = course.get('sequence', [])
    transportation = course.get('transportation', '도보')
    
    if not places or not sequence:
        return jsonify({"error": "코스 정보가 없습니다."}), 400
    
    # 이동 수단을 Google Maps API 모드로 변환
    mode_mapping = {
        '도보': 'walking',
        '자동차': 'driving',
        '지하철': 'transit',
        '버스': 'transit',
        '자전거': 'bicycling'
    }
    
    # transportation 문자열에서 이동 수단 추출
    transport_mode = 'walking'  # 기본값
    for key, value in mode_mapping.items():
        if key in transportation:
            transport_mode = value
            break
    
    # sequence 순서대로 장소 재배열
    ordered_places = []
    for place_idx in sequence:
        if place_idx < len(places):
            ordered_places.append(places[place_idx])
    
    if len(ordered_places) < 2:
        return jsonify({"error": "경로 안내를 생성할 장소가 부족합니다."}), 400
    
    # 기본 경로 안내 메시지 생성 함수 (API 실패 시에도 사용)
    def create_basic_guide():
        """기본 경로 안내 메시지 생성 (Google Maps API 없이)"""
        guide_text = f"🗺️ <strong>상세 경로 안내 ({transportation})</strong>\n\n"
        for i in range(len(ordered_places) - 1):
            from_place = ordered_places[i]
            to_place = ordered_places[i + 1]
            from_name = from_place.get('name', '알 수 없음')
            to_name = to_place.get('name', '알 수 없음')
            from_addr = from_place.get('address', '')
            to_addr = to_place.get('address', '')
            
            guide_text += f"<strong>{i+1}. {from_name} → {to_name}</strong>\n"
            
            if transportation and '버스' in transportation:
                guide_text += f"   🚌 <strong>버스 안내:</strong>\n"
                guide_text += f"      • {from_name}에서 가장 가까운 버스 정류장으로 이동하세요.\n"
                guide_text += f"      • {to_name} 방면 버스를 이용하세요.\n"
                if from_addr:
                    guide_text += f"      • 출발지 주소: {from_addr}\n"
                if to_addr:
                    guide_text += f"      • 도착지 주소: {to_addr}\n"
            elif transportation and '지하철' in transportation:
                guide_text += f"   🚇 <strong>지하철 안내:</strong>\n"
                guide_text += f"      • {from_name}에서 가장 가까운 지하철역으로 이동하세요.\n"
                guide_text += f"      • {to_name} 방면 지하철을 이용하세요.\n"
                if from_addr:
                    guide_text += f"      • 출발지 주소: {from_addr}\n"
                if to_addr:
                    guide_text += f"      • 도착지 주소: {to_addr}\n"
            elif transportation and '자동차' in transportation:
                guide_text += f"   🚗 <strong>자동차 안내:</strong>\n"
                guide_text += f"      • {from_name}에서 {to_name}로 자동차로 이동하세요.\n"
                if from_addr:
                    guide_text += f"      • 출발지 주소: {from_addr}\n"
                if to_addr:
                    guide_text += f"      • 도착지 주소: {to_addr}\n"
            else:
                guide_text += f"   🚶 <strong>도보 안내:</strong>\n"
                guide_text += f"      • {from_name}에서 {to_name}로 도보로 이동하세요.\n"
                if from_addr:
                    guide_text += f"      • 출발지 주소: {from_addr}\n"
                if to_addr:
                    guide_text += f"      • 도착지 주소: {to_addr}\n"
            
            guide_text += "\n"
        return guide_text
    
    try:
        # Google Maps API를 사용한 상세 경로 안내 시도
        try:
            config = Config.get_agent_config()
            
            # Google Maps API 키 확인
            if not config.get("google_maps_api_key"):
                print("⚠️ Google Maps API 키가 없습니다. 기본 경로 안내를 제공합니다.")
                return jsonify({"guide": create_basic_guide()})
            
            routing_agent = RoutingAgent(config=config)
            
            routing_input = {
                "places": ordered_places,
                "mode": transport_mode,
                "optimize_waypoints": False  # sequence 순서 유지
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
                return jsonify({"guide": create_basic_guide()})
            
            directions = route_result.get("directions", [])
            
            if not directions:
                print("⚠️ 경로 안내 정보가 비어있습니다. 기본 안내를 제공합니다.")
                return jsonify({"guide": create_basic_guide()})
            
            # 경로 안내 텍스트 생성
            guide_text = f"🗺️ <strong>상세 경로 안내 ({transportation})</strong>\n\n"
            
            for i, direction in enumerate(directions, 1):
                from_place = direction.get("from", "출발지")
                to_place = direction.get("to", "도착지")
                duration_text = direction.get("duration_text", "")
                distance_text = direction.get("distance_text", "")
                mode = direction.get("mode", transport_mode)
                steps = direction.get("steps", [])
                
                guide_text += f"<strong>{i}. {from_place} → {to_place}</strong>\n"
                guide_text += f"   ⏱ 소요 시간: {duration_text}\n"
                guide_text += f"   📏 거리: {distance_text}\n"
                
                # 이동 수단별 상세 안내
                if mode == "transit" and steps:
                    # 대중교통 상세 안내
                    guide_text += f"   🚌 <strong>대중교통 안내:</strong>\n"
                    for step in steps[:5]:  # 상위 5개 단계만 표시
                        instruction = clean_html_tags(step.get("instruction", ""))
                        if instruction:
                            guide_text += f"      • {instruction}\n"
                elif mode == "walking":
                    guide_text += f"   🚶 <strong>도보 안내:</strong>\n"
                    if steps:
                        for step in steps[:3]:  # 상위 3개 단계만 표시
                            instruction = clean_html_tags(step.get("instruction", ""))
                            if instruction:
                                guide_text += f"      • {instruction}\n"
                    else:
                        guide_text += f"      • {from_place}에서 {to_place}로 도보로 이동하세요.\n"
                elif mode == "driving":
                    guide_text += f"   🚗 <strong>자동차 안내:</strong>\n"
                    if steps:
                        for step in steps[:3]:  # 상위 3개 단계만 표시
                            instruction = clean_html_tags(step.get("instruction", ""))
                            if instruction:
                                guide_text += f"      • {instruction}\n"
                    else:
                        guide_text += f"      • {from_place}에서 {to_place}로 자동차로 이동하세요.\n"
                
                guide_text += "\n"
            
            return jsonify({"guide": guide_text})
            
        except Exception as api_error:
            # Google Maps API 호출 실패 시 기본 안내 제공
            print(f"⚠️ Google Maps API 호출 실패: {api_error}")
            return jsonify({"guide": create_basic_guide()})
        
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        print(f"❌ 경로 안내 생성 중 오류 발생:")
        print(error_detail)
        # 오류 발생 시에도 기본 안내 제공
        try:
            basic_guide = create_basic_guide()
            return jsonify({"guide": basic_guide})
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
        
        # Places API로 검색
        places_result = gmaps.places(query=query)
        
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
        
        return jsonify({'places': places})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

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

# 기존의 단계별 입력 방식은 이제 사용되지 않으므로 주석 처리하거나 삭제 가능
# @app.route('/', methods=['GET', 'POST']) ...

if __name__ == '__main__':
    app.run(debug=True, port=5000)