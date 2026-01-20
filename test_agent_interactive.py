"""
RoutePick Agent 인터랙티브 테스트 스크립트
사용자 입력을 받아 Agent를 테스트합니다.
"""

import asyncio
import os
from dotenv import load_dotenv
from agents.search_agent import SearchAgent
from agents.planning_agent import PlanningAgent
# [추가] RoutingAgent 임포트
from agents.routing_agent import RoutingAgent
from config.config import Config

# .env 파일에서 환경 변수 로드
load_dotenv()


def get_user_input(prompt: str, required: bool = False, default: str = None) -> str:
    """
    사용자 입력을 받는 함수
    
    Args:
        prompt: 입력 프롬프트
        required: 필수 입력 여부
        default: 기본값
    
    Returns:
        사용자 입력값
    """
    while True:
        if default:
            full_prompt = f"{prompt} (기본값: {default})"
        else:
            full_prompt = f"{prompt}" if not required else f"{prompt} (필수) *"
        
        value = input(f"{full_prompt}: ").strip()
        
        if value:
            return value
        elif default:
            return default
        elif not required:
            return ""
        else:
            print("⚠️  이 항목은 필수입니다. 다시 입력해주세요.")


def validate_and_collect_input() -> dict:
    """
    사용자 입력을 수집하고 검증하는 함수
    누락된 필수 정보가 있으면 재질문
    
    Returns:
        수집된 입력 데이터
    """
    print("=" * 70)
    print("🚀 RoutePick Agent 테스트")
    print("=" * 70)
    print()
    print("여행 코스를 설계하기 위해 다음 정보를 입력해주세요.")
    print()
    
    # 필수 정보 수집
    theme = get_user_input("📌 여행 테마", required=True)
    location = get_user_input("📍 지역 (예: 서울, 부산)", required=True)
    
    # 선택 정보 수집
    print()
    print("다음 정보는 선택사항입니다. Enter를 누르면 건너뛸 수 있습니다.")
    print()
    
    group_size_str = get_user_input("👥 여행 인원 (숫자)", required=False, default="2")
    visit_date = get_user_input("📅 방문 일자 (예: 2024-12-25)", required=False, default="")
    visit_time = get_user_input("⏰ 방문 시간 (예: 오후, 저녁)", required=False, default="오후")
    transportation = get_user_input("🚶 이동 수단 (도보, 지하철, 버스, 자동차)", required=False, default="도보")
    
    # 인원을 숫자로 변환
    try:
        group_size = int(group_size_str) if group_size_str else 2
    except ValueError:
        print("⚠️  인원은 숫자여야 합니다. 기본값 2명으로 설정합니다.")
        group_size = 2
    
    # 입력 데이터 구성
    input_data = {
        "theme": theme,
        "location": location,
        "group_size": group_size,
        "visit_date": visit_date,
        "visit_time": visit_time,
        "transportation": transportation
    }
    
    return input_data


def print_collected_info(data: dict):
    """수집된 정보를 출력하는 함수"""
    print()
    print("=" * 70)
    print("📋 수집된 정보 확인")
    print("=" * 70)
    print(f"  테마: {data['theme']}")
    print(f"  지역: {data['location']}")
    print(f"  인원: {data['group_size']}명")
    print(f"  방문 일자: {data['visit_date'] or '(미지정)'}")
    print(f"  방문 시간: {data['visit_time'] or '(미지정)'}")
    print(f"  이동 수단: {data['transportation'] or '(미지정)'}")
    print("=" * 70)
    print()


async def main():
    """메인 실행 함수"""
    
    # 설정 검증
    print("🔍 설정 확인 중...")
    if not Config.validate():
        print("\n❌ 필수 API 키가 설정되지 않았습니다.")
        print("📝 .env 파일을 확인하고 다음 키를 설정해주세요:")
        print("   - TAVILY_API_KEY")
        print("   - GOOGLE_MAPS_API_KEY")
        print("   - OPENAI_API_KEY")
        return
    
    print("✅ 설정 확인 완료\n")
    
    # 사용자 입력 수집
    user_data = validate_and_collect_input()
    
    # 입력 확인
    print_collected_info(user_data)
    
    confirm = input("위 정보로 진행하시겠습니까? (y/n): ").strip().lower()
    if confirm not in ['y', 'yes', '예', 'ㅇ']:
        print("❌ 취소되었습니다.")
        return
    
    print()
    print("=" * 70)
    print("🔄 Agent 실행 시작")
    print("=" * 70)
    print()
    
    # Agent 설정
    config = Config.get_agent_config()
    
    try:
        # ============================================================
        # Step 1: SearchAgent 실행 (Tavily 검색)
        # ============================================================
        print("📡 [Step 1] SearchAgent: 장소 검색 중...")
        print()
        
        search_agent = SearchAgent(config=config)
        search_input = {
            "theme": user_data["theme"],
            "location": user_data["location"]
        }
        
        # SearchAgent 입력 검증 및 누락 정보 확인
        if not search_agent.validate_input(search_input):
            print("❌ 필수 정보가 누락되었습니다.")
            missing_info = []
            
            if not search_input.get("theme"):
                missing_info.append("테마")
            if not search_input.get("location"):
                missing_info.append("지역")
            
            if missing_info:
                print(f"⚠️  다음 정보를 입력해주세요: {', '.join(missing_info)}")
                print()
                
                # 누락된 정보 재입력 받기
                if not search_input.get("theme"):
                    search_input["theme"] = get_user_input("📌 여행 테마", required=True)
                if not search_input.get("location"):
                    search_input["location"] = get_user_input("📍 지역", required=True)
                
                # 재검증
                if not search_agent.validate_input(search_input):
                    print("❌ 검증 실패: 필수 정보가 여전히 누락되었습니다.")
                    return
        
        search_result = await search_agent.execute(search_input)
        
        if not search_result.get("success"):
            print(f"❌ 장소 검색 실패: {search_result.get('error', '알 수 없는 오류')}")
            return
        
        places = search_result.get("candidate_pool", [])
        print(f"\n✅ 검색 완료: {len(places)}개의 장소를 찾았습니다.")
        print()
        
        if not places:
            print("⚠️  검색된 장소가 없습니다. 다른 테마나 지역으로 시도해주세요.")
            return
        
        # 검색된 장소 미리보기
        print("📍 검색된 장소 미리보기 (상위 5개):")
        for i, place in enumerate(places[:5], 1):
            print(f"  {i}. {place.get('name')} ({place.get('category')}) - 평점: {place.get('rating', 'N/A')}")
        print()

        # ============================================================
        # [최종 수정] Step 2: RoutingAgent - 하이브리드 군집 분석
        # ============================================================
        
        config = Config.get_agent_config()
        # 키 매핑 보장 로직 추가
        # ------------------------------------------------------------
        # Config는 'google_maps_api_key'라는 이름으로 키를 주는데,
        # GoogleMapsTool은 'api_key'라는 이름을 찾습니다. 이 통로를 맞춰주는 겁니다.
        if config.get("google_maps_api_key"):
            config["api_key"] = config.get("google_maps_api_key")
        # ------------------------------------------------------------

        routing_agent = RoutingAgent(config=config)
        
        places_for_planning = places # 기본값은 전체 후보군

        # 이동 수단과 지역 "구체성"에 따라 군집화 여부 결정
        should_cluster = False
        location_input = user_data["location"]
        
        # 1. '도보' 이동은 무조건 군집 분석 실행  
        if user_data["transportation"] == "도보":
            should_cluster = True
            print("\n- '도보' 이동이므로, 밀집 지역을 찾기 위해 군집 분석을 실행합니다.")
        
        # 2. 도보가 아닐 경우, 마지막 단어로 판단
        else:
            location_parts = location_input.split()
            if location_parts: # 입력이 비어있지 않다면
                last_word = location_parts[-1]
                
                # 광역 지역 이름 리스트
                large_areas = ["서울", "부산", "인천", "대구", "대전", "광주", "울산", "제주", "제주도", 
                               "강원", "강원도", "경기", "경기도", "충청북도", "충북", "충청남도", "충남",
                               "전라북도", "전북", "전라남도", "전남", "경상북도", "경북", "경상남도", "경남"]
                
                # 마지막 단어가 광역 지역 이름이고, 전체 단어가 1개일 때만 군집 분석 실행
                if len(location_parts) == 1 and last_word in large_areas:
                    should_cluster = True
                    print(f"\n- '{location_input}'은(는) 넓은 지역으로 판단되어, 핵심 권역을 찾기 위해 군집 분석을 실행합니다.")
        
        if should_cluster:
            clustered_places = routing_agent.cluster_places(places, user_data["transportation"])
            
            if len(clustered_places) < 5 and len(places) > len(clustered_places):
                print("   - 군집 내 장소 수가 너무 적어, 원본 후보군에서 상위 장소를 추가합니다.")
                clustered_places.extend(p for p in places if p not in clustered_places)
                final_places = []
                seen = set()
                for p in clustered_places:
                    if p['name'] not in seen:
                        final_places.append(p)
                        seen.add(p['name'])
                places_for_planning = final_places[:15]
            else:
                places_for_planning = clustered_places
        else:
            print(f"\n🗺️ [Step 2] 군집 분석 건너뛰기: '{location_input}'은(는) 구체적인 지역으로 간주합니다.")
            places_for_planning = places

        print(f"   -> PlanningAgent에게 {len(places_for_planning)}개의 후보 장소를 전달합니다.")

        # ============================================================
        # Step 3: PlanningAgent 실행 (코스 제작)
        # ============================================================
        print("🧠 [Step 3] PlanningAgent: 코스 제작 중...")
        print()
        
        planning_agent = PlanningAgent(config=config)
        
        # 사용자 선호도 구성
        user_preferences = {
            "theme": user_data["theme"],
            "group_size": user_data["group_size"],
            "visit_date": user_data["visit_date"] or "2024-12-25",
            "visit_time": user_data["visit_time"] or "오후",
            "transportation": user_data["transportation"] or "도보"
        }
        
        # 시간 제약 (선택사항)
        time_constraints = None
        if user_data.get("visit_time"):
            time_constraints = {
                "start_time": "14:00" if "오후" in user_data["visit_time"] else "10:00",
                "end_time": "20:00",
                "total_duration": 360  # 6시간
            }
        
        # 검색된 원본 'places' 대신 군집을 거친 places_for_planning
        planning_input = {
            "places": places_for_planning, 
            "user_preferences": user_preferences,
            "time_constraints": time_constraints
        }
        
        # PlanningAgent 입력 검증 및 누락 정보 확인
        if not planning_agent.validate_input(planning_input):
            print("❌ 필수 정보가 누락되었습니다.")
            missing_info = []
            
            if not planning_input.get("places"):
                missing_info.append("장소 리스트")
            if not planning_input.get("user_preferences", {}).get("theme"):
                missing_info.append("테마")
            
            if missing_info:
                print(f"⚠️  다음 정보가 누락되었습니다: {', '.join(missing_info)}")
                
                # 장소가 없으면 검색 단계로 돌아가기
                if not planning_input.get("places"):
                    print("❌ 장소 검색 결과가 없습니다. 코스를 제작할 수 없습니다.")
                    return
                
                # 테마가 없으면 재입력
                if not planning_input.get("user_preferences", {}).get("theme"):
                    print()
                    theme = get_user_input("📌 여행 테마 (필수)", required=True)
                    planning_input["user_preferences"]["theme"] = theme
                
                # 재검증
                if not planning_agent.validate_input(planning_input):
                    print("❌ 검증 실패: 필수 정보가 여전히 누락되었습니다.")
                    return
        
        course_result = await planning_agent.execute(planning_input)
        
        if not course_result.get("success"):
            print(f"❌ 코스 제작 실패: {course_result.get('error', '알 수 없는 오류')}")
            return

        # ============================================================
        # [수정] Step 4: 두 가지 버전의 경로 계산
        # ============================================================
        course = course_result.get("course", {})
        places_list_logical = course.get("places", []) # PlanningAgent가 정한 "논리적 순서"
        
        if not places_list_logical:
            print("❌ PlanningAgent가 코스를 생성하지 못했습니다.")
            return

        estimated_duration = course.get("estimated_duration", {})
        
        mode_mapping = {"도보": "walking", "자동차": "driving", "지하철": "transit", "버스": "transit"}
        transport_mode = mode_mapping.get(user_data["transportation"], "walking")

        # --- 경로 A: PlanningAgent의 "논리적 순서" 기반 경로 정보 계산 ---
        print("\n🚗 [Step 4-A] '논리적 순서' 코스의 실제 이동 시간 계산 중...")
        logical_route_input = {
            "places": places_list_logical,
            "mode": transport_mode,
            "optimize_waypoints": False # 순서 변경 안 함
        }
        logical_route = await routing_agent.execute(logical_route_input)

        # --- 경로 B: RoutingAgent의 "물리적 최적화" 순서 기반 경로 정보 계산 ---
        print("🚗 [Step 4-B] '동선 최적화' 코스의 실제 이동 시간 계산 중...")
        optimized_route_input = {
            "places": places_list_logical,
            "mode": transport_mode,
            "optimize_waypoints": True # 순서 최적화 함
        }
        optimized_route = await routing_agent.execute(optimized_route_input)

        # ============================================================
        # Step 5: 최종 결과 출력 (두 가지 코스 비교 제안)
        # ============================================================
        print("\n" + "=" * 70)
        print("✨ RoutePick: 당신을 위한 두 가지 맞춤형 코스를 제안합니다!")
        print("=" * 70)

        # --- 코스 A: 감성/논리 중심 코스 ---

        # print("\n\n--- 💡 코스 A: AI 추천 감성 코스 ---")
        # if course.get("course_description"):
        #     print("\n📝 코스 스토리텔링")
        #     print("-" * 70)
        #     print(course["course_description"])
        #     print()

        print("📍 AI 추천 방문 순서") 
        print("-" * 70)
        
        places_A = logical_route.get("optimized_route", places_list_logical)
        directions_A = logical_route.get("directions", [])
        for idx, place in enumerate(places_A, 1):
            # 논리적 순서는 인덱스가 순차적이므로, original_idx가 필요 없음
            stay_time = estimated_duration.get(str(idx-1), "60")
            
            print(f"\n{idx}. {place.get('name', '알 수 없음')}")
            print(f"   📌 카테고리: {place.get('category', 'N/A')} | ⭐ 평점: {place.get('rating', 'N/A')}")
            print(f"   ⏱️  예상 체류 시간: {stay_time}분")
            print(f"   📍 주소: {place.get('address', '주소 정보 없음')}")
            if place.get('source_url'): print(f"   🔗 상세 추천 근거: {place['source_url']}")
            if place.get('map_url'): print(f"   🗺️  위치 확인 (지도): {place['map_url']}")                    
            if idx < len(places_A) and idx <= len(directions_A):
                d = directions_A[idx-1]
                print(f"\n   🚗 [다음 장소로 이동] 약 {d.get('duration_text')} 소요 ({d.get('distance_text')})")
        
        # --- 코스 B: 효율/동선 중심 코스 ---
        print("\n\n--- 🏃‍♂️ 코스 B: 구글맵 추천 최단 동선 코스 ---")
        print("\n📝 (이 코스는 이동 시간을 최소화하는 데 중점을 둡니다)")
        
        print("\n📍 최적화된 방문 순서") 
        print("-" * 70)
        
        places_B = optimized_route.get("optimized_route", [])
        if not places_B: # 최적화 실패 시 코스 A와 동일하게 표시
            print("   ⚠️ 동선 최적화에 실패하여 코스 A와 동일한 순서로 표시됩니다.")
            places_B = places_A
        
        directions_B = optimized_route.get("directions", [])
        for idx, place in enumerate(places_B, 1):
            # 순서가 바뀌었으므로 이름으로 원래 인덱스를 찾아 체류 시간 매칭
            original_idx = -1
            for i, p in enumerate(places_list_logical):
                if p.get('name') == place.get('name'): original_idx = i; break
            stay_time = estimated_duration.get(str(original_idx), "60")
            
            print(f"\n{idx}. {place.get('name', '알 수 없음')}")
            print(f"   📌 카테고리: {place.get('category', 'N/A')} | ⭐ 평점: {place.get('rating', 'N/A')}")
            print(f"   ⏱️  예상 체류 시간: {stay_time}분")
            print(f"   📍 주소: {place.get('address', '주소 정보 없음')}")
            if place.get('source_url'): print(f"   🔗 상세 추천 근거: {place['source_url']}")
            if place.get('map_url'): print(f"   🗺️  위치 확인 (지도): {place['map_url']}")                    
            if idx < len(places_B) and idx <= len(directions_B):
                d = directions_B[idx-1]
                print(f"\n   🚗 [다음 장소로 이동] 약 {d.get('duration_text')} 소요 ({d.get('distance_text')})")

        print()

        # --- 최종 요약 비교 ---
        print("\n" + "=" * 70)
        print("📊 [두 코스 요약 비교]")
        print("-" * 70)
        print(f"💡 코스 A (감성 중심): 총 이동 시간 {logical_route.get('total_duration', 0) // 60}분, 총 거리 {logical_route.get('total_distance', 0) / 1000:.1f}km")
        print(f"🏃‍♂️ 코스 B (효율 중심): 총 이동 시간 {optimized_route.get('total_duration', 0) // 60}분, 총 거리 {optimized_route.get('total_distance', 0) / 1000:.1f}km")
        print("-" * 70)

        # # --- 공통 정보 (선정 이유) ---
        # if course_result.get("reasoning"):
        #     print("\n💡 AI 가이드의 장소 선정 이유 (공통)")
        #     print("-" * 70)
        #     print(course_result.get("reasoning"))
        #     print()

        print("\n✅ 모든 코스 설계가 완료되었습니다. 마음에 드는 코스를 선택해 즐거운 여행 되세요!")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  사용자에 의해 중단되었습니다.")
    except Exception as e:
        print(f"\n❌ 오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())

