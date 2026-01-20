import asyncio
import os
import json
from dotenv import load_dotenv

load_dotenv()

from agents.search_agent import SearchAgent
from config.config import Config



async def main():
    print("🎨 [RoutePick] Search Agent 전략 검색 디버깅 시작...")
    
    # 1. 설정 로드
    config = Config.get_agent_config()
    agent = SearchAgent(config=config)
    
    # 2. 테스트 데이터 (예시)
    user_input = {
        # "theme": "비 오는 날 성수동 실내 데이트",
        # "location": "서울 성수동"
        "theme": "여자친구와의 감성적인 데이트",
        "location": "강릉"
    }
    
    # 3. 실행
    result = await agent.execute(user_input)
    
    if result["success"]:
        print(f"\n" + "="*60)
        print(f"🎨 [RoutePick AI 비서: 분석 및 설계 보고서]")
        print(f"="*60)
        
        # 1. 테마 분석 결과
        print(f"\n💬 [Step 1: AI의 테마 분석 결과]")
        print(f"👉 \"{result.get('action_analysis')}\"")

        # 2. 검색 전략 및 판단 근거 출력 (데이터 저장 확인)
        intent = result.get("user_intent", {})
        structure = intent.get("course_structure", [])
        
        print(f"\n🧭 [Step 2: 맞춤형 코스 탐색 설계]")
        for step in structure:
            cat = step.get('category', '장소')
            query = step.get('search_query', '검색 중')
            reason = step.get('reasoning', '판단 근거를 불러올 수 없습니다.') # 휘발 방지 확인
            
            print(f"   📍 [{cat}] 탐색: \"{query}\"")
            print(f"      └ 선정근거: {reason}") # 👈 이제 여기서 GPT의 생각이 출력됩니다.

        # === [결과 리스트 섹션] ===
        print(f"\n" + "="*60)
        print(f"🏠 [Step 3: 설계에 따라 엄선된 후보지 리스트]")
        print(f"="*60)
        
        candidates = result.get("candidate_pool", [])
        if not candidates:
            print("\n⚠️ 현재 조건에 맞는 최적의 장소를 찾는 데 실패했습니다. (평점/영업 여부 필터링)")
        
        for p in candidates:
            category = p.get('category', '추천 장소')
            name = p.get('name', '이름 없음')
            rating = p.get('rating', 'N/A')
            trust_score = p.get('trust_score', 'N/A')
            address = p.get('address', '주소 정보 없음')
            
            # 링크 두 종류 준비
            source_link = p.get('source_url', '정보 없음')
            map_link = p.get('map_url', '링크 없음')

            print(f"\n[{category}] {name}")
            print(f"    ⭐ 평점: {rating} | 🛡️ 신뢰도 점수: {trust_score}")
            print(f"    📍 주소: {address}")
            print(f"    🔗 추천 근거(웹): {source_link}")
            print(f"    🗺️ 길찾기(지도): {map_link}")
            
        print(f"\n" + "="*60)
        print(f"✅ Search Agent 작업 완료. 다음 단계를 위해 위 후보군을 Planning Agent에게 전달합니다.")
        print(f"="*60)

    else:
        print(f"\n❌ [에러 발생]: {result.get('error')}")

if __name__ == "__main__":
    asyncio.run(main())