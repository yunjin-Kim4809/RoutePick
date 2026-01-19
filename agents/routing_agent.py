"""
Routing Agent
Google Maps Tool을 사용하여 경로를 최적화합니다.
"""
# [신규] 필요한 라이브러리 import
from typing import Any, Dict, List, Optional 
from .base_agent import BaseAgent
from tools.google_maps_tool import GoogleMapsTool


class RoutingAgent(BaseAgent):
    """경로 최적화 Agent - Google Maps Tool을 사용하여 동선 최적화"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Args:
            config: Agent 설정
        """
        super().__init__(name="RoutingAgent", config=config)
        self.maps_tool = GoogleMapsTool(config=config)
    
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        경로 최적화 실행
        
        Args:
            input_data: {
                "places": List[Dict],  # 코스에 포함된 장소 리스트
                "origin": Optional[Dict],  # 출발지
                "destination": Optional[Dict],  # 도착지
                "mode": str,  # 이동 수단
                "optimize_waypoints": bool  # 경유지 최적화 여부
            }
            
        Returns:
            {
                "success": bool,
                "optimized_route": List[Dict],  # 최적화된 경로
                "total_duration": int,  # 총 소요 시간 (초)
                "total_distance": int,  # 총 거리 (미터)
                "directions": List[Dict],  # 각 구간별 경로 정보
                "agent_name": str,
                "error": Optional[str]
            }
        """
        if not self.validate_input(input_data):
            return {
                "success": False,
                "optimized_route": [],
                "total_duration": 0,
                "total_distance": 0,
                "directions": [],
                "agent_name": self.name,
                "error": "입력 데이터가 유효하지 않습니다."
            }
        
        places = input_data.get("places", [])
        origin = input_data.get("origin")
        destination = input_data.get("destination")
        mode = input_data.get("mode", "transit")
        optimize_waypoints = input_data.get("optimize_waypoints", True)
        
        # 경로 최적화 실행
        result = await self.maps_tool.execute(
            places=places,
            origin=origin,
            destination=destination,
            mode=mode,
            optimize_waypoints=optimize_waypoints
        )
        
        return {
            "success": result.get("success", False),
            "optimized_route": result.get("optimized_route", []),
            "total_duration": result.get("total_duration", 0),
            "total_distance": result.get("total_distance", 0),
            "directions": result.get("directions", []),
            "agent_name": self.name,
            "error": result.get("error")
        }
    
    def validate_input(self, input_data: Dict[str, Any]) -> bool:
        """
        입력 데이터 유효성 검증
        
        Args:
            input_data: 검증할 입력 데이터
            
        Returns:
            유효성 검증 결과
        """
        if not isinstance(input_data, dict):
            return False
        
        places = input_data.get("places")
        if not places or not isinstance(places, list):
            return False
        
        mode = input_data.get("mode", "transit")
        valid_modes = ["driving", "walking", "transit", "bicycling"]
        if mode not in valid_modes:
            return False
        
        return True


    def cluster_places(self, places: List[Dict], user_transportation: str) -> List[Dict]:
        """
        [최종 단순화] 이동수단에 따른 고정 반경으로 DBSCAN 군집화를 수행합니다.
        """
        from sklearn.cluster import DBSCAN # 지역 import
        import numpy as np # 지역 import

        print(f"\n🗺️ [Step 2] RoutingAgent: {len(places)}개 후보에 대한 군집 분석(DBSCAN) 실행 중...")
        
        if len(places) < 4:
            print("   - 후보 수가 적어 군집 분석을 건너뜁니다.")
            return places
        
        coords_with_indices = [(i, (p['coordinates']['lat'], p['coordinates']['lng'])) for i, p in enumerate(places) if p.get('coordinates')]
        if len(coords_with_indices) < 3: return places
        indices, coords = zip(*coords_with_indices)

        # [최종 수정] 이동수단에 따른 고정 반경(eps) 설정
        if user_transportation == "도보":
            eps_km = 1.3 # 반경 1.3km
        elif user_transportation == "자전거":
            eps_km = 3 # 반경 3km
        else: # 자동차, 지하철, 버스 등
            eps_km = 10.0 # 반경 10km
            
        min_samples = 3 # 군집을 이루는 최소 장소 수
        print(f"   - 이동수단 '{user_transportation}' 감지. 군집 반경을 {eps_km}km로 설정합니다.")
        
        kms_per_radian = 6371.0088
        epsilon = eps_km / kms_per_radian

        db = DBSCAN(eps=epsilon, min_samples=min_samples, algorithm='ball_tree', metric='haversine').fit(np.radians(coords))
        labels = db.labels_
        
        unique_labels = set(labels)
        if -1 in unique_labels: unique_labels.remove(-1)
        if not unique_labels:
            print("   ⚠️ 유의미한 군집을 찾지 못했습니다. 상위 15개 장소를 반환합니다.")
            return places[:15]

        # '매력도 점수' 로직은 그대로 유지 (다양성 확보)
        cluster_info = {}
        for label in unique_labels:
            member_indices = [indices[i] for i, l in enumerate(labels) if l == label]
            categories = {places[i]['category'] for i in member_indices}
            size, diversity = len(member_indices), len(categories)
            
            has_food = '식당' in categories
            has_cafe = '카페' in categories
            has_activity = any(c in ['활동', '관광지'] for c in categories)
            bonus = 1.5 if has_food and has_cafe and has_activity else 1.0
            score = size * (diversity ** 2) * bonus
            cluster_info[label] = {'score': score, 'indices': member_indices, 'size': size, 'diversity': diversity}
        
        best_cluster_label = max(cluster_info, key=lambda k: cluster_info[k]['score'])
        best_cluster = cluster_info[best_cluster_label]
        
        print(f"   ✅ 가장 매력적인 군집({best_cluster_label}번) 발견. (크기: {best_cluster['size']}개, 다양성: {best_cluster['diversity']})")
        
        clustered_places = [places[i] for i in best_cluster['indices']]
        return clustered_places