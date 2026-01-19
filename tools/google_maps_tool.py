"""
Google Maps 경로 최적화 Tool
선택된 장소들의 동선을 최적화하고 경로를 계산합니다.
"""

from typing import Any, Dict, List, Optional, Tuple
import os
import asyncio
import googlemaps
from .base_tool import BaseTool


class GoogleMapsTool(BaseTool):
    """Google Maps API를 사용한 경로 최적화 Tool"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Args:
            config: Tool 설정 (api_key 등)
        """
        super().__init__(
            name="google_maps_routing",
            description="장소들 간의 최적 경로를 계산하고 동선을 최적화합니다.",
            config=config or {}
        )
        self.api_key = self.config.get("api_key") or self.config.get("google_maps_api_key") or os.getenv("GOOGLE_MAPS_API_KEY")
        # API 키가 없어도 클라이언트는 None으로 유지 (나중에 설정 가능)
        self.client = None
        if self.api_key:
            try:
                self.client = googlemaps.Client(key=self.api_key)
                print(f"✅ Google Maps Client 초기화 성공")
            except Exception as e:
                print(f"❌ Google Maps Client 초기화 실패: {e}")
                self.client = None
        
        # Geocoding 캐시 (주소 -> 좌표 매핑)
        self._geocoding_cache: Dict[str, Tuple[float, float]] = {}
        # Directions API 재시도 설정
        self._max_retries = 3
        self._retry_delay = 1.0  # 초
    
    async def execute(
        self,
        places: List[Dict[str, Any]],
        origin: Optional[Dict[str, Any]] = None,
        destination: Optional[Dict[str, Any]] = None,
        mode: str = "transit",  # 'driving', 'walking', 'transit', 'bicycling'
        optimize_waypoints: bool = True,
        **kwargs
    ) -> Dict[str, Any]:
        """
        경로 최적화 실행
        
        Args:
            places: 장소 정보 리스트 (각 장소는 name, address, coordinates 등을 포함)
            origin: 출발지 (선택사항, 없으면 places의 첫 번째 항목)
            destination: 도착지 (선택사항, 없으면 places의 마지막 항목)
            mode: 이동 수단 ('driving', 'walking', 'transit', 'bicycling')
            optimize_waypoints: 경유지 순서 최적화 여부
            
        Returns:
            {
                "success": bool,
                "optimized_route": List[Dict],  # 최적화된 경로
                "total_duration": int,  # 총 소요 시간 (초)
                "total_distance": int,  # 총 거리 (미터)
                "directions": List[Dict],  # 각 구간별 경로 정보
                "error": Optional[str]
            }
        """
        try:
            if not self.validate_params(places=places):
                return {
                    "success": False,
                    "optimized_route": [],
                    "total_duration": 0,
                    "total_distance": 0,
                    "directions": [],
                    "error": "필수 파라미터가 누락되었습니다."
                }
            
            if not places:
                return {
                    "success": False,
                    "optimized_route": [],
                    "total_duration": 0,
                    "total_distance": 0,
                    "directions": [],
                    "error": "장소 리스트가 비어있습니다."
                }
            
            # API 키 확인
            if not self.api_key or not self.client:
                return {
                    "success": False,
                    "optimized_route": [],
                    "total_duration": 0,
                    "total_distance": 0,
                    "directions": [],
                    "error": "Google Maps API 키가 설정되지 않았습니다."
                }
            
            # 좌표 추출 (주소가 있으면 좌표로 변환)
            coordinates = await self._extract_coordinates(places)
            
            if optimize_waypoints and len(coordinates) > 2:
                # 경유지 최적화 (TSP 알고리즘 또는 Google Directions API 사용)
                optimized_order = await self._optimize_waypoint_order(
                    coordinates, origin, destination, mode
                )
            else:
                optimized_order = list(range(len(places)))
            
            # 최적화된 순서로 장소 재배열
            optimized_places = [places[i] for i in optimized_order]
            
            # 최적화된 경로로 Directions API 호출
            directions, total_duration, total_distance = await self._get_optimized_route_directions(
                optimized_places, origin, destination, mode
            )
            
            return {
                "success": True,
                "optimized_route": optimized_places,
                "total_duration": total_duration,
                "total_distance": total_distance,
                "directions": directions,
                "error": None
            }
            
        except Exception as e:
            # 실패하더라도 최소한의 데이터는 반환하여 시스템이 멈추지 않게 함
            print(f"⚠️  Google Maps API 실행 중 오류 발생 (무시하고 진행): {e}")
            return {
                "success": True,
                "optimized_route": places,
                "total_duration": 0,
                "total_distance": 0,
                "directions": [],
                "error": str(e)
            }
    
    def get_schema(self) -> Dict[str, Any]:
        """
        Tool 입력 스키마 반환
        
        Returns:
            스키마 딕셔너리
        """
        return {
            "type": "object",
            "properties": {
                "places": {
                    "type": "array",
                    "description": "장소 정보 리스트 (각 장소는 name, address, coordinates 포함)",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "address": {"type": "string"},
                            "coordinates": {
                                "type": "object",
                                "properties": {
                                    "lat": {"type": "number"},
                                    "lng": {"type": "number"}
                                }
                            }
                        }
                    }
                },
                "origin": {
                    "type": "object",
                    "description": "출발지 (선택사항)"
                },
                "destination": {
                    "type": "object",
                    "description": "도착지 (선택사항)"
                },
                "mode": {
                    "type": "string",
                    "enum": ["driving", "walking", "transit", "bicycling"],
                    "description": "이동 수단",
                    "default": "transit"
                },
                "optimize_waypoints": {
                    "type": "boolean",
                    "description": "경유지 순서 최적화 여부",
                    "default": True
                }
            },
            "required": ["places"]
        }
    
    async def _geocode_address(self, address: str) -> Optional[Tuple[float, float]]:
        """
        주소를 좌표로 변환 (캐싱 지원)
        
        Args:
            address: 주소 문자열
            
        Returns:
            (lat, lng) 튜플 또는 None
        """
        # 캐시 확인
        if address in self._geocoding_cache:
            return self._geocoding_cache[address]
        
        if not self.client:
            return None
        
        loop = asyncio.get_event_loop()
        try:
            # 동기 함수를 비동기로 실행
            geocode_result = await loop.run_in_executor(
                None,
                self.client.geocode,
                address
            )
            if geocode_result:
                loc = geocode_result[0]["geometry"]["location"]
                coord = (loc["lat"], loc["lng"])
                # 캐시에 저장
                self._geocoding_cache[address] = coord
                return coord
        except Exception as e:
            print(f"⚠️  Geocoding 실패: {address} - {e}")
        
        return None
    
    async def _extract_coordinates(self, places: List[Dict[str, Any]]) -> List[Tuple[float, float]]:
        """
        장소 리스트에서 좌표 추출 (주소가 있으면 Geocoding으로 변환, 병렬 처리)
        
        Args:
            places: 장소 정보 리스트
            
        Returns:
            (lat, lng) 튜플 리스트
        """
        coordinates = []
        
        # 좌표 추출 태스크 준비
        geocode_tasks = []
        for place in places:
            coords = place.get("coordinates")
            if coords and coords.get("lat") and coords.get("lng"):
                # 좌표가 이미 있는 경우
                coordinates.append((float(coords.get("lat")), float(coords.get("lng"))))
                geocode_tasks.append(None)  # None은 이미 좌표가 있음을 의미
            else:
                # 주소를 좌표로 변환 (Geocoding API 사용)
                address = place.get("address") or place.get("name")
                if address:
                    geocode_tasks.append(self._geocode_address(address))
                else:
                    geocode_tasks.append(None)
                    coordinates.append((0.0, 0.0))
        
        # 병렬로 Geocoding 실행 (이미 좌표가 있는 것은 None이므로 건너뜀)
        geocode_results = await asyncio.gather(*[task for task in geocode_tasks if task is not None], return_exceptions=True)
        
        # 결과 처리
        result_idx = 0
        for i, place in enumerate(places):
            if geocode_tasks[i] is None:
                # 이미 좌표가 있거나 주소가 없는 경우는 건너뜀
                if i >= len(coordinates):
                    coordinates.append((0.0, 0.0))
                continue
            
            # Geocoding 결과 처리
            if result_idx < len(geocode_results):
                result = geocode_results[result_idx]
                result_idx += 1
                
                if isinstance(result, Exception):
                    print(f"⚠️  Geocoding 오류: {place.get('name', 'Unknown')} - {result}")
                    if i >= len(coordinates):
                        coordinates.append((0.0, 0.0))
                    else:
                        coordinates[i] = (0.0, 0.0)
                elif result:
                    # 좌표를 place에 저장 (데이터 보강)
                    place["coordinates"] = {"lat": result[0], "lng": result[1]}
                    if i >= len(coordinates):
                        coordinates.append(result)
                    else:
                        coordinates[i] = result
                else:
                    # Geocoding 실패
                    if i >= len(coordinates):
                        coordinates.append((0.0, 0.0))
                    else:
                        coordinates[i] = (0.0, 0.0)
        
        return coordinates
    
    async def _optimize_waypoint_order(
        self,
        coordinates: List[Tuple[float, float]],
        origin: Optional[Dict[str, Any]],
        destination: Optional[Dict[str, Any]],
        mode: str
    ) -> List[int]:
        """
        경유지 순서 최적화 (TSP 문제 해결)
        Google Directions API의 optimize_waypoints 옵션 사용
        
        Args:
            coordinates: 좌표 리스트
            origin: 출발지
            destination: 도착지
            mode: 이동 수단
            
        Returns:
            최적화된 순서의 인덱스 리스트
        """
        if len(coordinates) <= 2:
            return list(range(len(coordinates)))
        
        try:
            # 출발지와 도착지 좌표 결정
            origin_coords = None
            dest_coords = None
            
            if origin:
                if origin.get("coordinates"):
                    origin_coords = (origin["coordinates"]["lat"], origin["coordinates"]["lng"])
                elif origin.get("address"):
                    loop = asyncio.get_event_loop()
                    geocode_result = await loop.run_in_executor(
                        None,
                        self.client.geocode,
                        origin["address"]
                    )
                    if geocode_result:
                        location = geocode_result[0]["geometry"]["location"]
                        origin_coords = (location["lat"], location["lng"])
            
            if destination:
                if destination.get("coordinates"):
                    dest_coords = (destination["coordinates"]["lat"], destination["coordinates"]["lng"])
                elif destination.get("address"):
                    loop = asyncio.get_event_loop()
                    geocode_result = await loop.run_in_executor(
                        None,
                        self.client.geocode,
                        destination["address"]
                    )
                    if geocode_result:
                        location = geocode_result[0]["geometry"]["location"]
                        dest_coords = (location["lat"], location["lng"])
            
            # 출발지와 도착지 좌표 결정 (없으면 첫 번째/마지막 좌표 사용)
            if not origin_coords:
                origin_coords = coordinates[0]
            
            if not dest_coords and len(coordinates) > 0:
                dest_coords = coordinates[-1]
            
            # waypoints는 origin과 destination을 제외한 좌표들
            waypoints_coords = []
            waypoint_indices = []  # waypoint의 원본 인덱스 추적
            
            for idx, coord in enumerate(coordinates):
                # origin과 같은 좌표인지 확인 (허용 오차 0.0001도, 약 11m)
                is_origin = origin_coords and abs(coord[0] - origin_coords[0]) < 0.0001 and abs(coord[1] - origin_coords[1]) < 0.0001
                is_dest = dest_coords and abs(coord[0] - dest_coords[0]) < 0.0001 and abs(coord[1] - dest_coords[1]) < 0.0001
                
                if not is_origin and not is_dest:
                    waypoints_coords.append(coord)
                    waypoint_indices.append(idx)
            
            # waypoints를 좌표 문자열로 변환
            waypoints = [f"{lat},{lng}" for lat, lng in waypoints_coords]
            
            # waypoint가 없거나 1개 이하면 최적화 불필요
            if len(waypoints) <= 1:
                return list(range(len(coordinates)))
            
            # Distance Matrix API를 사용한 최적화 시도 (실제 이동 수단 기반)
            if self.client and len(coordinates) <= 25:
                try:
                    optimized_order = await self._optimize_with_distance_matrix(
                        coordinates, origin_coords, dest_coords, mode
                    )
                    if optimized_order:
                        return optimized_order
                except Exception as e:
                    print(f"⚠️  Distance Matrix API 최적화 실패: {e}")
                    # 폴백: Directions API의 optimize_waypoints 사용
            
            # Directions API 호출 (optimize_waypoints=True) - 폴백
            loop = asyncio.get_event_loop()
            
            # lambda 대신 함수 정의로 변경 (클로저 문제 방지)
            origin_str = f"{origin_coords[0]},{origin_coords[1]}"
            dest_str = f"{dest_coords[0]},{dest_coords[1]}"
            
            def call_directions():
                return self.client.directions(
                    origin=origin_str,
                    destination=dest_str,
                    waypoints=waypoints,
                    optimize_waypoints=True,
                    mode=mode
                )
            
            directions_result = await loop.run_in_executor(None, call_directions)
            
            if not directions_result or len(directions_result) == 0:
                # API 호출 실패 시 Nearest Neighbor 알고리즘 사용
                return self._nearest_neighbor_optimization(coordinates, origin_coords, dest_coords)
            
            # 최적화된 waypoint 순서 추출
            route = directions_result[0]
            waypoint_order = route.get("waypoint_order", list(range(len(waypoints))))
            
            # 최적화된 순서로 인덱스 재구성
            optimized_order = []
            
            # origin 추가 (원본 coordinates에서 origin 인덱스 찾기)
            origin_idx = None
            for idx, coord in enumerate(coordinates):
                if abs(coord[0] - origin_coords[0]) < 0.0001 and abs(coord[1] - origin_coords[1]) < 0.0001:
                    origin_idx = idx
                    break
            if origin_idx is not None:
                optimized_order.append(origin_idx)
            
            # 최적화된 waypoint 순서대로 인덱스 추가
            for wp_order in waypoint_order:
                if wp_order < len(waypoint_indices):
                    optimized_order.append(waypoint_indices[wp_order])
            
            # destination 추가
            dest_idx = None
            for idx, coord in enumerate(coordinates):
                if abs(coord[0] - dest_coords[0]) < 0.0001 and abs(coord[1] - dest_coords[1]) < 0.0001:
                    dest_idx = idx
                    break
            if dest_idx is not None and dest_idx not in optimized_order:
                optimized_order.append(dest_idx)
            
            # 중복 제거 및 순서 유지
            seen = set()
            final_order = []
            for idx in optimized_order:
                if idx not in seen:
                    seen.add(idx)
                    final_order.append(idx)
            
            # 빠진 인덱스가 있으면 추가 (원본 순서 유지)
            missing_indices = [idx for idx in range(len(coordinates)) if idx not in seen]
            final_order.extend(missing_indices)
            
            return final_order
            
        except Exception:
            # API 호출 실패 시 Nearest Neighbor 알고리즘 사용
            origin_coords = None
            dest_coords = None
            if origin and origin.get("coordinates"):
                origin_coords = (origin["coordinates"]["lat"], origin["coordinates"]["lng"])
            if destination and destination.get("coordinates"):
                dest_coords = (destination["coordinates"]["lat"], destination["coordinates"]["lng"])
            return self._nearest_neighbor_optimization(coordinates, origin_coords, dest_coords)
    
    async def _optimize_with_distance_matrix(
        self,
        coordinates: List[Tuple[float, float]],
        origin_coords: Optional[Tuple[float, float]],
        dest_coords: Optional[Tuple[float, float]],
        mode: str
    ) -> Optional[List[int]]:
        """
        Distance Matrix API를 사용하여 실제 이동 수단 기반 거리/시간으로 최적화
        
        Args:
            coordinates: 좌표 리스트
            origin_coords: 출발지 좌표
            dest_coords: 도착지 좌표
            mode: 이동 수단
            
        Returns:
            최적화된 순서의 인덱스 리스트 또는 None
        """
        if not self.client or len(coordinates) == 0:
            return None
        
        try:
            # 모든 좌표를 문자열로 변환
            all_coords = []
            
            # 출발지 추가
            if origin_coords:
                all_coords.append(f"{origin_coords[0]},{origin_coords[1]}")
            
            # 경유지 추가
            for coord in coordinates:
                all_coords.append(f"{coord[0]},{coord[1]}")
            
            # 도착지 추가
            if dest_coords:
                all_coords.append(f"{dest_coords[0]},{dest_coords[1]}")
            
            # Distance Matrix API 호출 (최대 25개 지점 지원)
            if len(all_coords) > 25:
                # 25개 초과 시 첫 25개만 사용
                all_coords = all_coords[:25]
            
            loop = asyncio.get_event_loop()
            distance_matrix = await loop.run_in_executor(
                None,
                lambda: self.client.distance_matrix(
                    origins=all_coords,
                    destinations=all_coords,
                    mode=mode
                )
            )
            
            if not distance_matrix or distance_matrix.get("status") != "OK":
                return None
            
            rows = distance_matrix.get("rows", [])
            if not rows:
                return None
            
            # 거리/시간 행렬 구성
            distance_matrix_data = {}
            duration_matrix_data = {}
            
            origin_offset = 1 if origin_coords else 0
            
            for i, row in enumerate(rows):
                elements = row.get("elements", [])
                for j, element in enumerate(elements):
                    if element.get("status") == "OK":
                        distance = element.get("distance", {}).get("value", float('inf'))
                        duration = element.get("duration", {}).get("value", float('inf'))
                        
                        # 출발지/도착지 인덱스 조정
                        from_idx = i - origin_offset
                        to_idx = j - origin_offset
                        
                        # 경유지 인덱스만 저장 (0 이상이고 coordinates 길이 미만)
                        if from_idx >= 0 and from_idx < len(coordinates) and \
                           to_idx >= 0 and to_idx < len(coordinates):
                            distance_matrix_data[(from_idx, to_idx)] = distance
                            duration_matrix_data[(from_idx, to_idx)] = duration
            
            # 출발지 결정
            start_idx = 0
            if origin_coords:
                # 출발지에서 가장 가까운 경유지 찾기
                min_duration = float('inf')
                origin_row_idx = 0  # 출발지는 첫 번째 행
                if origin_row_idx < len(rows):
                    elements = rows[origin_row_idx].get("elements", [])
                    for j, element in enumerate(elements):
                        if element.get("status") == "OK":
                            to_idx = j - origin_offset
                            if to_idx >= 0 and to_idx < len(coordinates):
                                duration = element.get("duration", {}).get("value", float('inf'))
                                if duration < min_duration:
                                    min_duration = duration
                                    start_idx = to_idx
            
            # Nearest Neighbor 알고리즘 (실제 거리/시간 기반)
            unvisited = set(range(len(coordinates)))
            optimized_order = [start_idx]
            unvisited.remove(start_idx)
            
            current = start_idx
            
            while unvisited:
                nearest_idx = None
                min_cost = float('inf')
                
                for idx in unvisited:
                    # 도착지가 지정되어 있고, 남은 노드가 1개이고 그것이 도착지와 가까운지 확인
                    if dest_coords and len(unvisited) == 1:
                        last_coord = coordinates[idx]
                        if abs(last_coord[0] - dest_coords[0]) < 0.0001 and \
                           abs(last_coord[1] - dest_coords[1]) < 0.0001:
                            nearest_idx = idx
                            break
                    
                    # 실제 이동 시간을 우선적으로 사용, 없으면 거리 사용
                    key = (current, idx)
                    if key in duration_matrix_data:
                        cost = duration_matrix_data[key]
                    elif key in distance_matrix_data:
                        cost = distance_matrix_data[key]
                    else:
                        # 데이터가 없으면 Haversine 거리 사용
                        import math
                        coord1 = coordinates[current]
                        coord2 = coordinates[idx]
                        R = 6371000
                        phi1 = math.radians(coord1[0])
                        phi2 = math.radians(coord2[0])
                        delta_phi = math.radians(coord2[0] - coord1[0])
                        delta_lambda = math.radians(coord2[1] - coord1[1])
                        a = math.sin(delta_phi / 2) ** 2 + \
                            math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
                        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
                        cost = R * c
                    
                    if cost < min_cost:
                        min_cost = cost
                        nearest_idx = idx
                
                if nearest_idx is not None:
                    optimized_order.append(nearest_idx)
                    unvisited.remove(nearest_idx)
                    current = nearest_idx
                else:
                    # nearest_idx가 None이면 남은 노드 중 첫 번째 선택
                    remaining = list(unvisited)
                    if remaining:
                        optimized_order.append(remaining[0])
                        unvisited.remove(remaining[0])
                        current = remaining[0]
            
            return optimized_order
            
        except Exception as e:
            print(f"⚠️  Distance Matrix API 최적화 중 오류: {e}")
            return None
    
    def _nearest_neighbor_optimization(
        self,
        coordinates: List[Tuple[float, float]],
        origin_coords: Optional[Tuple[float, float]],
        dest_coords: Optional[Tuple[float, float]]
    ) -> List[int]:
        """
        Nearest Neighbor 알고리즘으로 경유지 순서 최적화 (간단한 TSP 해결)
        
        Args:
            coordinates: 좌표 리스트
            origin_coords: 출발지 좌표
            dest_coords: 도착지 좌표
            
        Returns:
            최적화된 순서의 인덱스 리스트
        """
        def haversine_distance(coord1: Tuple[float, float], coord2: Tuple[float, float]) -> float:
            """두 좌표 간의 대략적인 거리 계산 (Haversine 공식)"""
            import math
            lat1, lon1 = coord1
            lat2, lon2 = coord2
            R = 6371000  # 지구 반지름 (미터)
            
            phi1 = math.radians(lat1)
            phi2 = math.radians(lat2)
            delta_phi = math.radians(lat2 - lat1)
            delta_lambda = math.radians(lon2 - lon1)
            
            a = math.sin(delta_phi / 2) ** 2 + \
                math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
            c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
            
            return R * c
        
        if len(coordinates) <= 1:
            return list(range(len(coordinates)))
        
        # 출발지 결정
        start_idx = 0
        if origin_coords:
            # origin과 가장 가까운 좌표 찾기
            distances = [haversine_distance(origin_coords, coord) for coord in coordinates]
            start_idx = distances.index(min(distances))
        
        # 방문하지 않은 인덱스 리스트
        unvisited = set(range(len(coordinates)))
        optimized_order = [start_idx]
        unvisited.remove(start_idx)
        
        current = coordinates[start_idx]
        
        # Nearest Neighbor 알고리즘
        while unvisited:
            nearest_idx = None
            nearest_dist = float('inf')
            
            for idx in unvisited:
                # 도착지가 지정되어 있고, 남은 노드가 1개이고 그것이 도착지와 같으면 제외
                if dest_coords and len(unvisited) == 1:
                    dest_idx = None
                    for i, coord in enumerate(coordinates):
                        if abs(coord[0] - dest_coords[0]) < 0.0001 and abs(coord[1] - dest_coords[1]) < 0.0001:
                            dest_idx = i
                            break
                    if dest_idx == idx and idx not in optimized_order:
                        nearest_idx = idx
                        break
                
                dist = haversine_distance(current, coordinates[idx])
                if dist < nearest_dist:
                    nearest_dist = dist
                    nearest_idx = idx
            
            if nearest_idx is not None:
                optimized_order.append(nearest_idx)
                unvisited.remove(nearest_idx)
                current = coordinates[nearest_idx]
        
        return optimized_order
    
    async def _get_optimized_route_directions(
        self,
        places: List[Dict[str, Any]],
        origin: Optional[Dict[str, Any]],
        destination: Optional[Dict[str, Any]],
        mode: str
    ) -> Tuple[List[Dict[str, Any]], int, int]:
        """
        최적화된 경로의 전체 Directions 정보를 한 번의 API 호출로 획득
        
        Args:
            places: 최적화된 순서의 장소 리스트
            origin: 출발지
            destination: 도착지
            mode: 이동 수단
            
        Returns:
            (directions 리스트, 총 소요 시간, 총 거리)
        """
        if len(places) < 2:
            return [], 0, 0
        
        # 좌표 추출
        coordinates_with_places = []
        for place in places:
            coords = place.get("coordinates")
            if coords and coords.get("lat") and coords.get("lng"):
                coordinates_with_places.append({
                    "coord": (float(coords.get("lat")), float(coords.get("lng"))),
                    "place": place
                })
            else:
                # 주소를 좌표로 변환
                address = place.get("address") or place.get("name")
                if address:
                    coord = await self._geocode_address(address)
                    if coord:
                        place["coordinates"] = {"lat": coord[0], "lng": coord[1]}
                        coordinates_with_places.append({
                            "coord": coord,
                            "place": place
                        })
        
        if len(coordinates_with_places) < 2:
            return [], 0, 0
        
        # 출발지와 도착지 결정
        origin_coord = None
        dest_coord = None
        
        if origin:
            if origin.get("coordinates"):
                origin_coord = (origin["coordinates"]["lat"], origin["coordinates"]["lng"])
            elif origin.get("address"):
                origin_coord = await self._geocode_address(origin["address"])
        
        if destination:
            if destination.get("coordinates"):
                dest_coord = (destination["coordinates"]["lat"], destination["coordinates"]["lng"])
            elif destination.get("address"):
                dest_coord = await self._geocode_address(destination["address"])
        
        # 출발지/도착지가 없으면 첫 번째/마지막 좌표 사용
        if not origin_coord:
            origin_coord = coordinates_with_places[0]["coord"]
        if not dest_coord:
            dest_coord = coordinates_with_places[-1]["coord"]
        
        # Waypoints 추출 (출발지/도착지 제외)
        waypoints = []
        waypoint_places = []
        for item in coordinates_with_places:
            coord = item["coord"]
            # 출발지/도착지와 같은지 확인 (허용 오차 0.0001도, 약 11m)
            is_origin = abs(coord[0] - origin_coord[0]) < 0.0001 and abs(coord[1] - origin_coord[1]) < 0.0001
            is_dest = abs(coord[0] - dest_coord[0]) < 0.0001 and abs(coord[1] - dest_coord[1]) < 0.0001
            
            if not is_origin and not is_dest:
                waypoints.append(f"{coord[0]},{coord[1]}")
                waypoint_places.append(item)
        
        # Directions API 호출 (최적화된 waypoints 포함)
        loop = asyncio.get_event_loop()
        origin_str = f"{origin_coord[0]},{origin_coord[1]}"
        dest_str = f"{dest_coord[0]},{dest_coord[1]}"
        
        for attempt in range(self._max_retries):
            try:
                def call_directions():
                    if waypoints:
                        return self.client.directions(
                            origin=origin_str,
                            destination=dest_str,
                            waypoints=waypoints,
                            optimize_waypoints=False,  # 이미 최적화되어 있으므로 False
                            mode=mode
                        )
                    else:
                        return self.client.directions(
                            origin=origin_str,
                            destination=dest_str,
                            mode=mode
                        )
                
                directions_result = await loop.run_in_executor(None, call_directions)
                
                if directions_result and len(directions_result) > 0:
                    route = directions_result[0]
                    legs = route.get("legs", [])
                    
                    if legs:
                        directions = []
                        total_duration = 0
                        total_distance = 0
                        
                        # 각 leg를 directions 형식으로 변환
                        for i, leg in enumerate(legs):
                            duration = leg.get("duration", {}).get("value", 0)
                            distance = leg.get("distance", {}).get("value", 0)
                            total_duration += duration
                            total_distance += distance
                            
                            # 장소 정보 매칭
                            from_place = places[i] if i < len(places) else {"name": "Unknown"}
                            to_place = places[i + 1] if i + 1 < len(places) else {"name": "Unknown"}
                            
                            # 단계별 경로 정보 추출
                            steps = []
                            for step in leg.get("steps", []):
                                steps.append({
                                    "instruction": step.get("html_instructions", ""),
                                    "distance": step.get("distance", {}).get("value", 0),
                                    "duration": step.get("duration", {}).get("value", 0),
                                    "travel_mode": step.get("travel_mode", mode)
                                })
                            
                            directions.append({
                                "from": from_place.get("name", "Unknown"),
                                "to": to_place.get("name", "Unknown"),
                                "from_address": from_place.get("address", ""),
                                "to_address": to_place.get("address", ""),
                                "duration": duration,
                                "distance": distance,
                                "duration_text": leg.get("duration", {}).get("text", ""),
                                "distance_text": leg.get("distance", {}).get("text", ""),
                                "steps": steps,
                                "mode": mode,
                                "start_location": {
                                    "lat": leg.get("start_location", {}).get("lat", 0),
                                    "lng": leg.get("start_location", {}).get("lng", 0)
                                },
                                "end_location": {
                                    "lat": leg.get("end_location", {}).get("lat", 0),
                                    "lng": leg.get("end_location", {}).get("lng", 0)
                                }
                            })
                        
                        return directions, total_duration, total_distance
                
                # API 응답이 비어있는 경우 폴백으로 개별 구간 계산
                break
                
            except Exception as e:
                if attempt < self._max_retries - 1:
                    await asyncio.sleep(self._retry_delay * (attempt + 1))  # 지수 백오프
                    continue
                else:
                    print(f"⚠️  Directions API 호출 실패 (재시도 {self._max_retries}회): {e}")
                    # 폴백: 개별 구간별 계산
                    break
        
        # 폴백: 개별 구간별로 Directions API 호출
        return await self._calculate_directions(places, origin, destination, mode)
    
    async def _calculate_directions(
        self,
        places: List[Dict[str, Any]],
        origin: Optional[Dict[str, Any]],
        destination: Optional[Dict[str, Any]],
        mode: str
    ) -> Tuple[List[Dict[str, Any]], int, int]:
        """
        각 구간별 경로 정보 계산 (폴백 메서드, 병렬 처리)
        
        Args:
            places: 장소 리스트
            origin: 출발지
            destination: 도착지
            mode: 이동 수단
            
        Returns:
            (directions 리스트, 총 소요 시간, 총 거리)
        """
        directions = []
        
        if len(places) < 2:
            return directions, 0, 0
        
        loop = asyncio.get_event_loop()
        
        # 좌표 추출 (병렬 처리)
        coordinates_with_places = []
        geocode_tasks = []
        
        for idx, place in enumerate(places):
            coords = place.get("coordinates")
            if coords and coords.get("lat") and coords.get("lng"):
                coordinates_with_places.append({
                    "coord": (float(coords.get("lat")), float(coords.get("lng"))),
                    "place": place,
                    "place_idx": idx
                })
                geocode_tasks.append(None)
            else:
                address = place.get("address") or place.get("name")
                if address:
                    geocode_tasks.append((idx, self._geocode_address(address)))
                else:
                    geocode_tasks.append(None)
        
        # 병렬로 Geocoding 실행
        geocode_results = {}
        tasks_to_run = [(idx, task) for idx, task in enumerate(geocode_tasks) if task is not None]
        if tasks_to_run:
            results = await asyncio.gather(
                *[task for _, task in tasks_to_run],
                return_exceptions=True
            )
            for (idx, _), result in zip(tasks_to_run, results):
                if not isinstance(result, Exception) and result:
                    place = places[idx]
                    place["coordinates"] = {"lat": result[0], "lng": result[1]}
                    coordinates_with_places.append({
                        "coord": result,
                        "place": place,
                        "place_idx": idx
                    })
        
        # 좌표 순서대로 정렬
        coordinates_with_places.sort(key=lambda x: x["place_idx"])
        
        if len(coordinates_with_places) < 2:
            return directions, 0, 0
        
        # 각 구간별로 Directions API 호출 (병렬 처리)
        async def get_segment_direction(from_item, to_item):
            """단일 구간의 Directions 정보 가져오기"""
            from_coord = from_item["coord"]
            to_coord = to_item["coord"]
            from_place = from_item["place"]
            to_place = to_item["place"]
            
            origin_str = f"{from_coord[0]},{from_coord[1]}"
            dest_str = f"{to_coord[0]},{to_coord[1]}"
            
            for attempt in range(self._max_retries):
                try:
                    def call_directions():
                        return self.client.directions(
                            origin=origin_str,
                            destination=dest_str,
                            mode=mode
                        )
                    
                    directions_result = await loop.run_in_executor(None, call_directions)
                    
                    if directions_result and len(directions_result) > 0:
                        route = directions_result[0]
                        if route.get("legs") and len(route["legs"]) > 0:
                            leg = route["legs"][0]
                            
                            duration = leg.get("duration", {}).get("value", 0)
                            distance = leg.get("distance", {}).get("value", 0)
                            
                            steps = []
                            for step in leg.get("steps", []):
                                steps.append({
                                    "instruction": step.get("html_instructions", ""),
                                    "distance": step.get("distance", {}).get("value", 0),
                                    "duration": step.get("duration", {}).get("value", 0),
                                    "travel_mode": step.get("travel_mode", mode)
                                })
                            
                            return {
                                "from": from_place.get("name", "Unknown"),
                                "to": to_place.get("name", "Unknown"),
                                "from_address": from_place.get("address", ""),
                                "to_address": to_place.get("address", ""),
                                "duration": duration,
                                "distance": distance,
                                "duration_text": leg.get("duration", {}).get("text", ""),
                                "distance_text": leg.get("distance", {}).get("text", ""),
                                "steps": steps,
                                "mode": mode,
                                "start_location": {
                                    "lat": leg.get("start_location", {}).get("lat", 0),
                                    "lng": leg.get("start_location", {}).get("lng", 0)
                                },
                                "end_location": {
                                    "lat": leg.get("end_location", {}).get("lat", 0),
                                    "lng": leg.get("end_location", {}).get("lng", 0)
                                }
                            }
                    
                    # 폴백: walking -> transit
                    if mode == "walking" and attempt == 0:
                        try:
                            def call_directions_transit():
                                return self.client.directions(
                                    origin=origin_str,
                                    destination=dest_str,
                                    mode="transit"
                                )
                            directions_result = await loop.run_in_executor(None, call_directions_transit)
                            if directions_result and len(directions_result) > 0:
                                route = directions_result[0]
                                if route.get("legs") and len(route["legs"]) > 0:
                                    leg = route["legs"][0]
                                    duration = leg.get("duration", {}).get("value", 0)
                                    distance = leg.get("distance", {}).get("value", 0)
                                    return {
                                        "from": from_place.get("name", "Unknown"),
                                        "to": to_place.get("name", "Unknown"),
                                        "from_address": from_place.get("address", ""),
                                        "to_address": to_place.get("address", ""),
                                        "duration": duration,
                                        "distance": distance,
                                        "duration_text": leg.get("duration", {}).get("text", ""),
                                        "distance_text": leg.get("distance", {}).get("text", ""),
                                        "steps": [],
                                        "mode": "transit",
                                        "start_location": {"lat": from_coord[0], "lng": from_coord[1]},
                                        "end_location": {"lat": to_coord[0], "lng": to_coord[1]},
                                        "error": "walking 모드에서 경로를 찾지 못해 transit 모드로 변경"
                                    }
                        except:
                            pass
                    
                except Exception as e:
                    if attempt < self._max_retries - 1:
                        await asyncio.sleep(self._retry_delay * (attempt + 1))
                        continue
                    else:
                        return {
                            "from": from_place.get("name", "Unknown"),
                            "to": to_place.get("name", "Unknown"),
                            "from_address": from_place.get("address", ""),
                            "to_address": to_place.get("address", ""),
                            "duration": 0,
                            "distance": 0,
                            "duration_text": "",
                            "distance_text": "",
                            "steps": [],
                            "mode": mode,
                            "start_location": {"lat": from_coord[0], "lng": from_coord[1]},
                            "end_location": {"lat": to_coord[0], "lng": to_coord[1]},
                            "error": f"API 호출 실패: {str(e)}"
                        }
            
            # 모든 재시도 실패
            return {
                "from": from_place.get("name", "Unknown"),
                "to": to_place.get("name", "Unknown"),
                "from_address": from_place.get("address", ""),
                "to_address": to_place.get("address", ""),
                "duration": 0,
                "distance": 0,
                "duration_text": "",
                "distance_text": "",
                "steps": [],
                "mode": mode,
                "start_location": {"lat": from_coord[0], "lng": from_coord[1]},
                "end_location": {"lat": to_coord[0], "lng": to_coord[1]},
                "error": "경로를 찾을 수 없습니다"
            }
        
        # 모든 구간을 병렬로 처리
        tasks = [
            get_segment_direction(
                coordinates_with_places[i],
                coordinates_with_places[i + 1]
            )
            for i in range(len(coordinates_with_places) - 1)
        ]
        
        directions = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 예외 처리
        valid_directions = []
        for d in directions:
            if isinstance(d, Exception):
                valid_directions.append({
                    "from": "Unknown",
                    "to": "Unknown",
                    "duration": 0,
                    "distance": 0,
                    "error": str(d)
                })
            else:
                valid_directions.append(d)
        
        # 총 소요 시간 및 거리 계산
        total_duration = sum(d.get("duration", 0) for d in valid_directions)
        total_distance = sum(d.get("distance", 0) for d in valid_directions)
        
        return valid_directions, total_duration, total_distance

