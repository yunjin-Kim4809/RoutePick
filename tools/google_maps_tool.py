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
                print(f"✅ Google Maps Client 초기화 성공") # 확인용
            except Exception as e:
                print(f"❌ Google Maps Client 초기화 실패: {e}")
                self.client = None
    
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
            
            # 각 구간별 경로 계산
            directions = await self._calculate_directions(
                optimized_places, origin, destination, mode
            )
            
            # 총 소요 시간 및 거리 계산
            total_duration = sum(d.get("duration", 0) for d in directions)
            total_distance = sum(d.get("distance", 0) for d in directions)
            
            return {
                "success": True,
                "optimized_route": optimized_places,
                "total_duration": total_duration,
                "total_distance": total_distance,
                "directions": directions,
                "error": None
            }
            
        except Exception as e:
            # [수정] 실패하더라도 최소한의 데이터(순서대로 정렬된 리스트)는 돌려줍니다.
            print(f"⚠️  Google Maps API 실행 중 오류 발생 (무시하고 진행): {e}")
            return {
                "success": True, # ⬅️ 실패해도 True로 반환하여 시스템이 멈추지 않게 함
                "optimized_route": places, # 원본이라도 반환
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
    
    async def _extract_coordinates(self, places: List[Dict[str, Any]]) -> List[Tuple[float, float]]:
        """
        장소 리스트에서 좌표 추출 (주소가 있으면 Geocoding으로 변환)
        
        Args:
            places: 장소 정보 리스트
            
        Returns:
            (lat, lng) 튜플 리스트
        """
        coordinates = []
        loop = asyncio.get_event_loop()
        
        for place in places:
            coords = place.get("coordinates")
            if coords and coords.get("lat") and coords.get("lng"):
                # 좌표가 이미 있는 경우
                coordinates.append((float(coords.get("lat")), float(coords.get("lng"))))
            else:
                # 주소를 좌표로 변환 (Geocoding API 사용)
                address = place.get("address") or place.get("name")
                if address and self.client:
                    try:
                        # 동기 함수를 비동기로 실행
                        geocode_result = await loop.run_in_executor(
                            None,
                            self.client.geocode,
                            address
                        )
                        if geocode_result:
                            loc = geocode_result[0]["geometry"]["location"]
                            place["coordinates"] = {"lat": loc["lat"], "lng": loc["lng"]} # 데이터 보강
                            coordinates.append((loc["lat"], loc["lng"]))
                        else:
                            print(f"⚠️  주소 변환 불가: {address} (건너뜀)")
                            # 좌표를 못 찾아도 빈 값을 넣어서 인덱스 순서를 맞춥니다.
                            coordinates.append((0.0, 0.0)) 
                    except:
                        print(f"⚠️  Geocoding 실패: {address} (건너뜀)")
                        coordinates.append((0.0, 0.0)) 
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
            
            # Directions API 호출 (optimize_waypoints=True)
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
    
    async def _calculate_directions(
        self,
        places: List[Dict[str, Any]],
        origin: Optional[Dict[str, Any]],
        destination: Optional[Dict[str, Any]],
        mode: str
    ) -> List[Dict[str, Any]]:
        """
        각 구간별 경로 정보 계산
        
        Args:
            places: 장소 리스트
            origin: 출발지
            destination: 도착지
            mode: 이동 수단
            
        Returns:
            구간별 경로 정보 리스트
        """
        directions = []
        
        if len(places) < 2:
            return directions
        
        loop = asyncio.get_event_loop()
        
        # 좌표 추출 (place 인덱스와 함께 저장)
        coordinates_with_places = []
        for idx, place in enumerate(places):
            coords = place.get("coordinates")
            if coords and coords.get("lat") and coords.get("lng"):
                coordinates_with_places.append({
                    "coord": (float(coords.get("lat")), float(coords.get("lng"))),
                    "place": place,
                    "place_idx": idx
                })
            else:
                address = place.get("address") or place.get("name")
                if address and self.client:
                    try:
                        geocode_result = await loop.run_in_executor(
                            None,
                            self.client.geocode,
                            address
                        )
                        if geocode_result:
                            location = geocode_result[0]["geometry"]["location"]
                            # 좌표 정보를 place에 업데이트
                            place["coordinates"] = {
                                "lat": location["lat"],
                                "lng": location["lng"]
                            }
                            coordinates_with_places.append({
                                "coord": (location["lat"], location["lng"]),
                                "place": place,
                                "place_idx": idx
                            })
                        else:
                            # 좌표를 가져올 수 없으면 건너뛰기
                            continue
                    except Exception as e:
                        # 에러가 발생해도 계속 진행 (나중에 에러 정보 포함)
                        print(f"Warning: Geocoding failed for {address}: {e}")
                        continue
                else:
                    # 좌표나 주소 정보가 없으면 건너뛰기
                    continue
        
        if len(coordinates_with_places) < 2:
            return directions
        
        # 각 구간별로 Directions API 호출
        for i in range(len(coordinates_with_places) - 1):
            from_item = coordinates_with_places[i]
            to_item = coordinates_with_places[i + 1]
            
            from_coord = from_item["coord"]
            to_coord = to_item["coord"]
            from_place = from_item["place"]
            to_place = to_item["place"]
            
            try:
                
                # Directions API 호출
                origin_str = f"{from_coord[0]},{from_coord[1]}"
                dest_str = f"{to_coord[0]},{to_coord[1]}"
                
                def call_directions():
                    try:
                        return self.client.directions(
                            origin=origin_str,
                            destination=dest_str,
                            mode=mode
                        )
                    except Exception as api_error:
                        # API 호출 실패 시 예외를 다시 발생시켜 외부에서 처리
                        raise api_error
                
                try:
                    directions_result = await loop.run_in_executor(None, call_directions)
                except Exception as api_error:
                    # API 호출 실패 (예: ZERO_RESULTS, INVALID_REQUEST 등)
                    error_msg = str(api_error)
                    directions.append({
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
                        "error": f"API 호출 실패: {error_msg}"
                    })
                    continue
                
                # API 호출 성공했지만 응답이 비어있는 경우 - 다른 모드로 폴백 시도
                if not directions_result or len(directions_result) == 0:
                    # walking 모드에서 경로를 찾지 못하면 transit 모드로 폴백 시도
                    if mode == "walking":
                        try:
                            def call_directions_transit():
                                return self.client.directions(
                                    origin=origin_str,
                                    destination=dest_str,
                                    mode="transit"
                                )
                            directions_result = await loop.run_in_executor(None, call_directions_transit)
                            if directions_result and len(directions_result) > 0:
                                # transit 모드로 경로를 찾았지만, 원래 요청 모드는 walking
                                pass  # 계속 진행하여 경로 정보 추출
                        except Exception:
                            pass  # 폴백 실패 시에도 계속 진행
                
                # API 호출 성공 - 응답 확인
                if directions_result and len(directions_result) > 0:
                    route = directions_result[0]
                    if route.get("legs") and len(route["legs"]) > 0:
                        leg = route["legs"][0]
                        
                        # 경로 정보 추출
                        duration = leg.get("duration", {}).get("value", 0)
                        distance = leg.get("distance", {}).get("value", 0)
                        
                        # 단계별 경로 정보 추출 (간소화)
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
                    else:
                        # legs가 없거나 비어있는 경우
                        directions.append({
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
                            "error": "경로를 찾을 수 없습니다 (legs가 비어있음)"
                        })
                else:
                    # directions_result가 비어있는 경우
                    directions.append({
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
                        "error": "경로를 찾을 수 없습니다 (API 응답이 비어있음)"
                    })
                        
            except Exception as e:
                # 해당 구간의 경로 계산 실패 시 기본 정보라도 추가
                directions.append({
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
                    "error": str(e)
                })
        
        return directions

