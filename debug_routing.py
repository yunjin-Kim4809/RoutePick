import asyncio
import os
from dotenv import load_dotenv

# 1. 다른 무엇보다 .env 로드를 가장 먼저 합니다!
load_dotenv()

from agents.routing_agent import RoutingAgent
from config.config import Config

async def debug_routing():
    print("=" * 60)
    print("🗺️ [RoutePick] Routing Agent 강제 디버깅 모드")
    print("=" * 60)

    # 🔍 [체크] 실제로 환경 변수에서 키를 읽어오는지 직접 확인
    env_key = os.getenv("GOOGLE_MAPS_API_KEY")
    if env_key:
        print(f"✅ .env 로드 확인: {env_key[:10]}... (키 존재함)")
    else:
        print("❌ .env 로드 실패: GOOGLE_MAPS_API_KEY를 찾을 수 없습니다.")
        return

    config = Config.get_agent_config()
    config["api_key"] = os.getenv("GOOGLE_MAPS_API_KEY") 
    agent = RoutingAgent(config=config)

    # 테스트 데이터 (주소만 있음)
    test_places = [
    {
        "name": "Pizzeria O",
        "category": "식당",
        "rating": 4.8,
        "trust_score": 5.0,
        "address": "86 Dongsung-gil, Jongno District, Seoul, South Korea",
        "source_url": "https://www.diningcode.com/list.dc?query=%ED%98%9C%ED%99%94",
        "map_url": "https://www.google.com/maps/search/?api=1&query=Pizzeria+O+서울+혜화"
    },
    {
        "name": "REAL SHOT",
        "category": "활동",
        "rating": 4.3,
        "trust_score": 4.4,
        "address": "10 Jong-ro 12-gil, Jongno District, Seoul, South Korea",
        "source_url": "https://www.instagram.com/p/C53ALY9hIyl/",
        "map_url": "https://www.google.com/maps/search/?api=1&query=REAL+SHOT+서울+혜화"
    },
    {
        "name": "크레마노 경복궁점",
        "category": "카페",
        "rating": 5.0,
        "trust_score": 5.0,
        "address": "6 Tongui-dong, Jongno District, Seoul, South Korea",
        "source_url": "https://www.instagram.com/reel/DSMrfxkDz9i/",
        "map_url": "https://www.google.com/maps/search/?api=1&query=크레마노+경복궁점+서울+혜화"
    },
    {
        "name": "혜화시장",
        "category": "기타",
        "rating": 4.2,
        "trust_score": 4.4,
        "address": "27-1 Myeongnyun 2(i)-ga, Jongno District, Seoul, South Korea",
        "source_url": "https://www.diningcode.com/list.dc?query=%ED%98%9C%ED%99%94+%EB%B6%84%EC%9C%84%EA%B8%B0%EC%A2%8B%EC%9D%80%EC%B9%B4%ED%8E%98",
        "map_url": "https://www.google.com/maps/search/?api=1&query=혜화시장+서울+혜화"
    },
    {
        "name": "Hyehwa Art Center",
        "category": "관광지",
        "rating": 4.5,
        "trust_score": 4.7,
        "address": "156 Daehak-ro, Jongno District, Seoul, South Korea",
        "source_url": "https://www.instagram.com/p/ChtBhPiuDfM/",
        "map_url": "https://www.google.com/maps/search/?api=1&query=Hyehwa+Art+Center+서울+혜화"
    },
    {
        "name": "메종아카이",
        "category": "식당",
        "rating": 5.0,
        "trust_score": 5.0,
        "address": "South Korea, Seoul, Jongno District, Daemyeong-gil, 34 2층",
        "source_url": "https://www.diningcode.com/list.dc?query=%ED%98%9C%ED%99%94",
        "map_url": "https://www.google.com/maps/search/?api=1&query=메종아카이+서울+혜화"
    },
    {
        "name": "세우아트센터",
        "category": "활동",
        "rating": 4.3,
        "trust_score": 4.3,
        "address": "49 Daehak-ro 12-gil, Jongno District, Seoul, South Korea",
        "source_url": "https://blog.naver.com/kshjbe/223873927572",
        "map_url": "https://www.google.com/maps/search/?api=1&query=세우아트센터+서울+혜화"
    },
    {
        "name": "Cafe Chieut",
        "category": "카페",
        "rating": 4.8,
        "trust_score": 4.9,
        "address": "18 Dongsung 4na-gil, Jongno District, Seoul, South Korea",
        "source_url": "https://kr.trip.com/moments/detail/seoul-234-132096855/",
        "map_url": "https://www.google.com/maps/search/?api=1&query=Cafe+Chieut+서울+혜화"
    },
    {
        "name": "Yurae",
        "category": "식당",
        "rating": 5.0,
        "trust_score": 5.0,
        "address": "266 Jong-ro, Jongno District, Seoul, South Korea",
        "source_url": "https://meanmin.tistory.com/97",
        "map_url": "https://www.google.com/maps/search/?api=1&query=Yurae+서울+혜화"
    },
    {
        "name": "Meerkat Park",
        "category": "활동",
        "rating": 3.7,
        "trust_score": 3.85,
        "address": "1-113 6층, Dongsung-dong, Jongno District, Seoul, South Korea",
        "source_url": "https://m.blog.naver.com/tiffany0711/222703684516",
        "map_url": "https://www.google.com/maps/search/?api=1&query=Meerkat+Park+서울+혜화"
    },
    {
        "name": "Coffee Hanyakbang Hyehwa Branch",
        "category": "카페",
        "rating": 4.6,
        "trust_score": 4.7,
        "address": "9 Dongsung 2-gil, Jongno District, Seoul, South Korea",
        "source_url": "https://www.diningcode.com/list.dc?query=%ED%98%9C%ED%99%94",
        "map_url": "https://www.google.com/maps/search/?api=1&query=Coffee+Hanyakbang+Hyehwa+Branch+서울+혜화"
    },
    {
        "name": "Sundae Silrok",
        "category": "식당",
        "rating": 4.5,
        "trust_score": 4.75,
        "address": "South Korea, Seoul, Jongno District, Dongsung-gil, 113 1층",
        "source_url": "https://m.blog.naver.com/seulpaces/222762217258",
        "map_url": "https://www.google.com/maps/search/?api=1&query=Sundae+Silrok+서울+혜화"
    },
    {
        "name": "Seohwa Coffee",
        "category": "카페",
        "rating": 4.5,
        "trust_score": 4.6,
        "address": "8 Daehak-ro 9ga-gil, Jongno District, Seoul, South Korea",
        "source_url": "https://www.diningcode.com/list.dc?query=%ED%98%9C%ED%99%94",
        "map_url": "https://www.google.com/maps/search/?api=1&query=Seohwa+Coffee+서울+혜화"
    },
    {
        "name": "Hidden Sushi",
        "category": "식당",
        "rating": 4.6,
        "trust_score": 4.7,
        "address": "27 Daemyeong-gil, Myeongnyun 4(sa)-ga, Jongno District, Seoul, South Korea",
        "source_url": "https://www.diningcode.com/list.dc?query=%ED%98%9C%ED%99%94+%EB%B6%84%EC%9C%84%EA%B8%B0%EC%A2%8B%EC%9D%80%EC%B9%B4%ED%8E%98",
        "map_url": "https://www.google.com/maps/search/?api=1&query=Hidden+Sushi+서울+혜화"
    },
    {
        "name": "Chillin",
        "category": "카페",
        "rating": 4.5,
        "trust_score": 4.6,
        "address": "South Korea, Seoul, Jongno District, 혜화동 Daehak-ro 11-gil, 41-8 1층",
        "source_url": "https://www.instagram.com/p/C53ALY9hIyl/",
        "map_url": "https://www.google.com/maps/search/?api=1&query=Chillin+서울+혜화"
    }
    ]

    print(f"\n🔍 [Audit] 팩트체크 시작...")
    result = await agent.execute({"places": test_places, "mode": "walking", "optimize_waypoints": True})

    if result["success"]:
        print("\n" + "="*50)
        print("✅ 1. 좌표 변환 검증 (Geocoding)")
        print("="*50)
        for p in result['optimized_route']:
            coords = p.get('coordinates', '❌ 누락')
            print(f"📍 {p['name']}: {coords}")
            # 만약 좌표가 (0.0, 0.0)이거나 '❌ 누락'이면 지오코딩 실패인 겁니다.

        print("\n" + "="*50)
        print("✅ 2. 구간별 상세 경로 검증 (Directions)")
        print("="*50)
        directions = result.get('directions', [])
        for i, d in enumerate(directions, 1):
            print(f"🚩 구간 {i}: {d['from']} ➔ {d['to']}")
            print(f"   📏 거리: {d['distance_text']} ({d['distance']}m)")
            print(f"   ⏱️ 시간: {d['duration_text']} ({d['duration']}초)")
            # 꿀팁: steps가 있다면 실제 경로 안내 데이터가 있는 겁니다.
            print(f"   👣 상세 안내(Step) 수: {len(d.get('steps', []))}개")

        print("\n" + "="*50)
        print("✅ 3. 최종 요약")
        print("="*50)
        print(f"⏱️ 총 소요 시간: {result['total_duration'] // 60}분")
        print(f"📏 총 이동 거리: {result['total_distance'] / 1000:.2f}km")
    else:
        print(f"❌ 실패: {result.get('error')}")

if __name__ == "__main__":
    asyncio.run(debug_routing())