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
        # [추가] Step 2: RoutingAgent 실행 (지리적 정보 보강)
        # ============================================================
        
        # ------------------------------------------------------------
        print("\n🗺️ [Step 2] RoutingAgent: 지리적 정보 분석 및 좌표 확보 중...")
        config = Config.get_agent_config()


        # 키 매핑 보장 로직 추가
        # ------------------------------------------------------------
        # Config는 'google_maps_api_key'라는 이름으로 키를 주는데,
        # GoogleMapsTool은 'api_key'라는 이름을 찾습니다. 이 통로를 맞춰주는 겁니다.
        if config.get("google_maps_api_key"):
            config["api_key"] = config.get("google_maps_api_key")
        # ------------------------------------------------------------

        routing_agent = RoutingAgent(config=config)

        # [수정] 한글 입력을 구글 API용 영문 상수로 변환
        mode_mapping = {
            "도보": "walking",
            "자동차": "driving",
            "지하철": "transit",
            "버스": "transit",
            "자전거": "bicycling"
        }
        transport_mode = mode_mapping.get(user_data["transportation"], "walking") # 기본값 도보

        routing_input = {
            "places": places,
            "mode": transport_mode, # ⬅️ 번역된 영문 전달
            "optimize_waypoints": False 
        }

        route_info_result = await routing_agent.execute(routing_input)
        
        # [수정] 아래 로직으로 교체하세요. 'or' 연산자가 아니라 if-else로 확실히!
        enriched_places = route_info_result.get("optimized_route", [])
        
        # 만약 루팅 결과가 비어있으면 원본 장소 리스트(Step 1 결과)로 복구!
        if not enriched_places:
            print("⚠️  루팅 에이전트가 결과를 반환하지 못했습니다. 원본 데이터를 사용합니다.")
            enriched_places = places
        else:
            print(f"✅ 지리 정보 보강 완료. ({len(enriched_places)}개 장소)")
            
        # ------------------------------------------------------------

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
        
        # [수정] 검색된 원본 'places' 대신 루팅을 거친 'enriched_places'를 넘김
        planning_input = {
            "places": enriched_places, 
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
        # [Step 4] 선정된 장소들에 대해 실제 이동 시간/거리를 한 번 더 루팅 
        # [Step 4] 최종 결과 출력 및 동선 확정
        # ============================================================
        print()
        print("=" * 70)
        print("✨ RoutePick: 당신만을 위한 맞춤형 코스 제작 완료!")
        print("=" * 70)
        
        course = course_result.get("course", {})
        places_list = course.get("places", []) # 플래너가 선택한 3~4개 장소
        estimated_duration = course.get("estimated_duration", {})
        
        # [최종 루팅] 선택된 장소들에 대해 실제 이동 시간과 최적 순서를 구글 맵에 다시 물어봅니다.
        # transport_mode는 위에서 한글->영문 변환된 변수를 사용합니다.
        final_routing_input = {
            "places": places_list,
            "mode": transport_mode, 
            "optimize_waypoints": True # 최종 코스이므로 구글이 최단 동선으로 재배열함
        }
        final_route = await routing_agent.execute(final_routing_input)
        
        optimized_places = final_route.get("optimized_route", places_list)
        directions = final_route.get("directions", [])

        # 1. 코스 개요 출력
        if course.get("course_description"):
            print("\n📝 코스 스토리텔링")
            print("-" * 70)
            print(course["course_description"])
            print()

        # 2. 상세 일정 출력
        if optimized_places:
            print("📍 실제 구글 맵 경로 기반 방문 일정")
            print("-" * 70)
            
            for idx, place in enumerate(optimized_places, 1):
                # 루팅으로 인해 순서가 바뀌었으므로, 원래 플래너가 설정한 체류 시간을 이름으로 매칭합니다.
                original_idx = -1
                for i, p in enumerate(places_list):
                    if p.get('name') == place.get('name'):
                        original_idx = i
                        break
                
                # 해당 장소의 체류 시간 가져오기 (기본값 60분)
                stay_time = estimated_duration.get(str(original_idx), "60")
                
                print(f"\n{idx}. {place.get('name', '알 수 없음')}")
                print(f"   📌 카테고리: {place.get('category', 'N/A')} | ⭐ 평점: {place.get('rating', 'N/A')}")
                print(f"   ⏱️  장소 체류 시간: {stay_time}분")
                print(f"   📍 주소: {place.get('address', '주소 정보 없음')}")
                
                # 홍겸님이 마이닝한 추천 근거 URL 출력
                if place.get('source_url'):
                    print(f"   🔗 상세 추천 근거: {place['source_url']}")
                
                # [중요] 다음 장소까지의 실제 이동 시간 출력 (Directions API 결과 반영)
                if idx <= len(directions):
                    d = directions[idx-1]
                    print(f"\n   🚗 [이동] 다음 장소까지 약 {d.get('duration_text')} ({d.get('distance_text')}) 소요")
            
            print()

        # 3. 선정 이유 (PlanningAgent의 논리)
        reasoning = course_result.get("reasoning")
        if reasoning:
            print("💡 AI 가이드의 선정 이유")
            print("-" * 70)
            print(reasoning)
            print()
        
        # 4. 전체 여정 요약 (총 이동시간/거리)
        if final_route.get("success"):
            print("=" * 70)
            print(f"📊 [코스 요약] 순수 이동 시간: {final_route.get('total_duration') // 60}분 | 총 거리: {final_route.get('total_distance') / 1000:.1f}km")
            print(f"🚶 이동 수단: {user_data['transportation']}")
            print("=" * 70)

        print("\n✅ 모든 코스 설계가 완료되었습니다. 즐거운 여행 되세요!")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  사용자에 의해 중단되었습니다.")
    except Exception as e:
        print(f"\n❌ 오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())

