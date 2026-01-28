"""
Routing Agent
Google Maps Tool과 T Map Tool을 사용하여 경로를 최적화합니다.
한국 내에서는 T Map API를 우선 사용합니다.
"""
# [신규] 필요한 라이브러리 import
from typing import Any, Dict, List, Optional 
from .base_agent import BaseAgent
from tools.google_maps_tool import GoogleMapsTool
from tools.tmap_tool import TMapTool


class RoutingAgent(BaseAgent):
    """경로 최적화 Agent - Google Maps Tool과 T Map Tool을 사용하여 동선 최적화"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Args:
            config: Agent 설정
        """
        super().__init__(name="RoutingAgent", config=config)
        self.maps_tool = GoogleMapsTool(config=config)
        self.tmap_tool = TMapTool(config=config)
    
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
        preferred_modes = input_data.get("preferred_modes")  # 대안 교통수단 리스트
        user_transportation = input_data.get("user_transportation")  # 원본 입력값
        departure_time = input_data.get("departure_time")  # 출발 일시 (ISO 문자열 등)
        
        # 한국 내에서 도보/자동차 경로인 경우 T Map API 우선 사용
        # 단, preferred_modes에 transit이 포함되어 있으면 T Map API 사용 안 함 (T Map은 대중교통 미지원)
        use_tmap = False
        tmap_error = None
        
        # preferred_modes에 transit이 포함되어 있으면 T Map API 사용 안 함
        has_transit = preferred_modes and 'transit' in preferred_modes
        
        if mode in ["walking", "driving"] and not has_transit:
            # 장소 좌표가 한국 영역 내에 있는지 확인
            is_korea = self._is_in_korea(places)
            if is_korea:
                use_tmap = True
                print(f"🗺️ 한국 내 경로 감지: T Map API 사용 ({mode})")
            else:
                print(f"⚠️ 한국 영역 외 경로 또는 좌표 정보 부족: Google Maps API 사용 ({mode})")
        elif has_transit:
            print(f"🚇 대중교통 포함: Google Maps API 사용 (T Map API는 대중교통 미지원)")
        
        if use_tmap:
            # T Map API 사용 (도보/자동차만 지원)
            tmap_mode = "walking" if mode == "walking" else "driving"
            try:
                result = await self.tmap_tool.execute(
                    places=places,
                    origin=origin,
                    destination=destination,
                    mode=tmap_mode,
                    optimize_waypoints=optimize_waypoints
                )
                
                # T Map API가 실패한 경우 처리
                if not result.get("success"):
                    error_msg = result.get("error", "T Map API 호출 실패")
                    print(f"❌ T Map API 실패: {error_msg}")
                    
                    # T Map API 키가 없거나 서비스 구독이 안 된 경우
                    # 또는 모든 구간이 실패한 경우 Google Maps로 폴백
                    if "API 키" in error_msg or "키가 설정되지 않았습니다" in error_msg:
                        # API 키 문제는 Google Maps로 폴백 (무한 루프 방지)
                        print(f"⚠️ T Map API 키 문제 감지, Google Maps API로 폴백합니다.")
                        use_tmap = False
                    elif "모든 구간" in error_msg or "서비스 제공 지역" in error_msg:
                        # 서비스 제공 지역이 아니거나 모든 구간 실패 시 Google Maps로 폴백
                        print(f"⚠️ T Map 서비스 제공 지역이 아니거나 모든 구간 실패, Google Maps API로 폴백합니다.")
                        use_tmap = False
                    else:
                        # 일부 구간만 실패한 경우는 결과를 그대로 반환 (에러 포함)
                        # 하지만 모든 구간이 실패했으면 Google Maps로 폴백
                        directions = result.get("directions", [])
                        all_failed = len(directions) > 0 and all(
                            d.get("error") or (not d.get("steps") and d.get("duration", 0) == 0)
                            for d in directions
                        )
                        if all_failed:
                            print(f"⚠️ T Map API 모든 구간 실패, Google Maps API로 폴백합니다.")
                            use_tmap = False
                        else:
                            # 일부 구간은 성공했으므로 결과 반환
                            pass
            except Exception as e:
                error_msg = str(e)
                print(f"❌ T Map API 예외 발생: {error_msg}")
                print(f"⚠️ T Map API 예외 발생, Google Maps API로 폴백합니다.")
                use_tmap = False
        
        if not use_tmap:
            # Google Maps API 사용 (대중교통 또는 한국 외 지역 또는 T Map 실패 시)
            print(f"🗺️ Google Maps API 사용 ({mode})")
            result = await self.maps_tool.execute(
                places=places,
                origin=origin,
                destination=destination,
                mode=mode,
                optimize_waypoints=optimize_waypoints,
                preferred_modes=preferred_modes,  # 대안 교통수단 전달
                user_transportation=user_transportation,  # 원본 입력값 전달
                departure_time=departure_time,  # 출발 일시 전달 (대중교통 소요 시간 계산용)
            )
        else:
            # T Map API 결과가 이미 result에 있음
            pass
        
        # 결과 검증: 모든 구간이 실패했는지 확인
        directions = result.get("directions", [])
        if directions:
            all_failed = all(
                d.get("error") or (not d.get("steps") and d.get("duration", 0) == 0)
                for d in directions
            )
            
            if all_failed and len(directions) > 0:
                # 모든 구간이 실패한 경우 명확한 에러 메시지 반환 (무한 루프 방지)
                error_messages = [d.get("error", "알 수 없는 오류") for d in directions if d.get("error")]
                error_summary = "; ".join(error_messages[:3])
                if len(error_messages) > 3:
                    error_summary += f" 외 {len(error_messages) - 3}개 구간 실패"
                
                return {
                    "success": False,
                    "optimized_route": result.get("optimized_route", places),
                    "total_duration": 0,
                    "total_distance": 0,
                    "directions": directions,
                    "agent_name": self.name,
                    "error": f"모든 구간의 경로 계산에 실패했습니다. {error_summary}"
                }
        
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
        valid_modes = ["driving", "walking", "transit"]  # 자전거 제외
        if mode not in valid_modes:
            return False
        
        return True
    
    def _is_in_korea(self, places: List[Dict[str, Any]]) -> bool:
        """
        장소들이 한국 영역 내에 있는지 확인
        
        Args:
            places: 장소 리스트
            
        Returns:
            한국 영역 내에 있으면 True (좌표가 없는 장소가 있어도 좌표가 있는 장소가 모두 한국이면 True)
        """
        if not places:
            return False
        
        # 한국 영역 경계 (대략적인 범위)
        KOREA_BOUNDS = {
            "min_lat": 33.0,  # 제주도 남쪽
            "max_lat": 38.6,  # DMZ 북쪽
            "min_lng": 124.5,  # 서해
            "max_lng": 132.0   # 동해
        }
        
        has_valid_coords = False
        korea_count = 0
        non_korea_count = 0
        
        for place in places:
            coords = place.get("coordinates")
            if not coords:
                continue
            
            lat = coords.get("lat")
            lng = coords.get("lng")
            
            if lat is None or lng is None:
                continue
            
            has_valid_coords = True
            
            # 한국 영역 확인
            if (KOREA_BOUNDS["min_lat"] <= lat <= KOREA_BOUNDS["max_lat"] and
                KOREA_BOUNDS["min_lng"] <= lng <= KOREA_BOUNDS["max_lng"]):
                korea_count += 1
            else:
                non_korea_count += 1
                # 한국 밖 장소가 하나라도 있으면 False
                print(f"⚠️ 한국 영역 외 장소 발견: {place.get('name', 'Unknown')} ({lat}, {lng})")
                return False
        
        # 좌표가 있는 장소가 하나도 없으면 False (확인 불가)
        if not has_valid_coords:
            print(f"⚠️ 좌표 정보가 있는 장소가 없어 한국 영역 확인 불가")
            return False
        
        # 모든 좌표가 있는 장소가 한국 영역 내에 있으면 True
        if korea_count > 0 and non_korea_count == 0:
            print(f"✅ 한국 영역 확인: {korea_count}개 장소 모두 한국 내")
            return True
        
        return False


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

        # [최종 수정] 이동수단에 따른 고정 반경(eps) 설정 (자전거 제외)
        if user_transportation == "도보":
            eps_km = 1.3 # 반경 1.3km
        else: # 자동차, 지하철, 버스 등 (자전거 제외)
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