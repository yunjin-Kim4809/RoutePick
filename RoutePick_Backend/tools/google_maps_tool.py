"""
Google Maps 경로 최적화 Tool
선택된 장소들의 동선을 최적화하고 경로를 계산합니다.
"""

from typing import Any, Dict, List, Optional, Tuple
import os
import asyncio
import re
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
        
        # API 키 정리 (앞뒤 공백 제거)
        if self.api_key:
            self.api_key = str(self.api_key).strip()
            if not self.api_key:
                self.api_key = None
        
        # API 키 디버깅 정보 출력
        if self.api_key:
            api_key_preview = f"{self.api_key[:10]}...{self.api_key[-5:]}" if len(self.api_key) > 15 else "***"
            print(f"🔑 Google Maps API 키 로드됨: {api_key_preview} (길이: {len(self.api_key)})")
        else:
            print("⚠️ Google Maps API 키를 찾을 수 없습니다.")
            print(f"   - config['api_key']: {self.config.get('api_key')}")
            print(f"   - config['google_maps_api_key']: {self.config.get('google_maps_api_key')}")
            print(f"   - 환경변수 GOOGLE_MAPS_API_KEY: {os.getenv('GOOGLE_MAPS_API_KEY')}")
        
        # API 키가 없어도 클라이언트는 None으로 유지 (나중에 설정 가능)
        self.client = None
        if self.api_key:
            try:
                # googlemaps.Client는 초기화 시점에 API 키를 검증하지 않음
                # 실제 API 호출 시점에 검증됨
                self.client = googlemaps.Client(key=self.api_key)
                print(f"✅ Google Maps Client 초기화 성공")
            except Exception as e:
                print(f"❌ Google Maps Client 초기화 실패: {e}")
                print(f"   API 키 형식 확인 필요 (길이: {len(self.api_key) if self.api_key else 0})")
                self.client = None
        
        # Geocoding 캐시 (주소 -> 좌표 매핑)
        self._geocoding_cache: Dict[str, Tuple[float, float]] = {}
        # Directions API 재시도 설정
        self._max_retries = 3
        self._retry_delay = 1.0  # 초
    
    def _clean_html_tags(self, text: str) -> str:
        """HTML 태그 제거"""
        if not text:
            return ""
        return re.sub(r'<[^>]+>', '', text)
    
    def _decode_polyline(self, encoded: str) -> List[Dict[str, float]]:
        """
        Google Maps polyline 인코딩 문자열을 좌표 리스트로 디코딩
        
        Args:
            encoded: 인코딩된 polyline 문자열
            
        Returns:
            [{"lat": float, "lng": float}, ...] 형식의 좌표 리스트
        """
        if not encoded:
            return []
        
        coordinates = []
        index = 0
        lat = 0
        lng = 0
        
        while index < len(encoded):
            # 위도 디코딩
            shift = 0
            result = 0
            while True:
                b = ord(encoded[index]) - 63
                index += 1
                result |= (b & 0x1f) << shift
                shift += 5
                if b < 0x20:
                    break
            dlat = ~(result >> 1) if (result & 1) else (result >> 1)
            lat += dlat
            
            # 경도 디코딩
            shift = 0
            result = 0
            while True:
                b = ord(encoded[index]) - 63
                index += 1
                result |= (b & 0x1f) << shift
                shift += 5
                if b < 0x20:
                    break
            dlng = ~(result >> 1) if (result & 1) else (result >> 1)
            lng += dlng
            
            coordinates.append({"lat": lat / 1e5, "lng": lng / 1e5})
        
        return coordinates
    
    def _format_transit_instruction(self, step: Dict[str, Any]) -> Dict[str, Any]:
        """
        단일 step 데이터를 사람이 읽기 좋은 안내 문구로 변환
        
        Args:
            step: Google Directions API의 step 객체
            
        Returns:
            포맷팅된 step 정보 딕셔너리
        """
        travel_mode = step.get("travel_mode", "").upper()
        html_instruction = step.get("html_instructions", "")
        instruction = self._clean_html_tags(html_instruction)
        
        step_data = {
            "instruction": instruction,
            "html_instruction": html_instruction,
            "distance": step.get("distance", {}).get("value", 0),
            "distance_text": step.get("distance", {}).get("text", ""),
            "duration": step.get("duration", {}).get("value", 0),
            "duration_text": step.get("duration", {}).get("text", ""),
            "travel_mode": travel_mode,
            "formatted_instruction": instruction  # 기본값
        }
        
        # 대중교통 상세 정보가 있는 경우
        transit_details = step.get("transit_details")
        if transit_details:
            line = transit_details.get("line", {}) or {}
            vehicle = line.get("vehicle", {}) or {}
            vehicle_type = vehicle.get("type", "").lower() if vehicle.get("type") else ""
            
            # 버스/지하철 번호 추출
            bus_number = line.get("short_name") or line.get("name") or ""
            line_name = line.get("name") or ""
            
            # 정류장 정보
            departure_stop = transit_details.get("departure_stop", {}) or {}
            arrival_stop = transit_details.get("arrival_stop", {}) or {}
            departure_stop_name = departure_stop.get("name", "") if isinstance(departure_stop, dict) else ""
            arrival_stop_name = arrival_stop.get("name", "") if isinstance(arrival_stop, dict) else ""
            
            # 정류장 ID (있는 경우)
            departure_stop_id = departure_stop.get("location", {}).get("lat", "") if isinstance(departure_stop, dict) else ""
            arrival_stop_id = arrival_stop.get("location", {}).get("lat", "") if isinstance(arrival_stop, dict) else ""
            
            num_stops = transit_details.get("num_stops", 0)
            
            # 출발/도착 시간
            departure_time_obj = transit_details.get("departure_time", {}) or {}
            arrival_time_obj = transit_details.get("arrival_time", {}) or {}
            departure_time = departure_time_obj.get("text", "") if isinstance(departure_time_obj, dict) else ""
            arrival_time = arrival_time_obj.get("text", "") if isinstance(arrival_time_obj, dict) else ""
            
            # 버스 번호 정리
            if bus_number:
                # 숫자만 추출
                bus_num_match = re.search(r'(\d+)', bus_number)
                if bus_num_match:
                    bus_number = bus_num_match.group(1)
            
            # 지하철인 경우
            is_subway = (
                vehicle_type == "subway" or 
                "subway" in vehicle_type or 
                "지하철" in line_name or 
                "호선" in line_name or
                "호선" in bus_number or
                "line" in line_name.lower() or
                "line" in bus_number.lower()
            )
            
            # 버스인 경우
            is_bus = (
                vehicle_type == "bus" or 
                "bus" in vehicle_type or 
                "버스" in line_name or
                (not is_subway and bus_number and re.search(r'\d+', bus_number))
            )
            
            formatted_parts = []
            
            if is_subway:
                # 노선명 정리
                subway_line = bus_number or line_name
                if "line" in subway_line.lower():
                    line_num_match = re.search(r'(\d+)', subway_line)
                    if line_num_match:
                        subway_line = f"{line_num_match.group(1)}호선"
                
                formatted_parts.append(f"🚇 지하철 {subway_line} 이용")
                if departure_stop_name:
                    formatted_parts.append(f"  • 승차역: {departure_stop_name}")
                if arrival_stop_name:
                    formatted_parts.append(f"  • 하차역: {arrival_stop_name}")
                if num_stops > 0:
                    formatted_parts.append(f"  • {num_stops}개 역 이동")
                if departure_time:
                    formatted_parts.append(f"  • 출발 시간: {departure_time}")
                if arrival_time:
                    formatted_parts.append(f"  • 도착 시간: {arrival_time}")
            
            elif is_bus:
                formatted_parts.append(f"🚌 {bus_number}번 버스 이용")
                if departure_stop_name:
                    formatted_parts.append(f"  • 승차 정류장: {departure_stop_name}")
                if arrival_stop_name:
                    formatted_parts.append(f"  • 하차 정류장: {arrival_stop_name}")
                if num_stops > 0:
                    formatted_parts.append(f"  • {num_stops}개 정류장 이동")
                if departure_time:
                    formatted_parts.append(f"  • 출발 시간: {departure_time}")
                if arrival_time:
                    formatted_parts.append(f"  • 도착 시간: {arrival_time}")
            
            else:
                # 기타 대중교통
                transit_name = bus_number or line_name or "대중교통"
                formatted_parts.append(f"🚃 {transit_name} 이용")
                if departure_stop_name:
                    formatted_parts.append(f"  • 출발: {departure_stop_name}")
                if arrival_stop_name:
                    formatted_parts.append(f"  • 도착: {arrival_stop_name}")
                if num_stops > 0:
                    formatted_parts.append(f"  • {num_stops}개 정거장 이동")
            
            step_data["formatted_instruction"] = "\n".join(formatted_parts)
            step_data["transit_details"] = transit_details
            step_data["transit_summary"] = {
                "type": "subway" if is_subway else ("bus" if is_bus else "other"),
                "line_number": bus_number,
                "line_name": line_name,
                "departure_stop": departure_stop_name,
                "arrival_stop": arrival_stop_name,
                "num_stops": num_stops,
                "departure_time": departure_time,
                "arrival_time": arrival_time
            }
        
        # 도보 이동인 경우
        elif travel_mode == "WALKING":
            dist_text = step.get("distance", {}).get("text", "")
            dur_text = step.get("duration", {}).get("text", "")
            if dist_text and dur_text:
                step_data["formatted_instruction"] = f"🚶 도보 이동: {dur_text} ({dist_text})"
            elif dur_text:
                step_data["formatted_instruction"] = f"🚶 도보 이동: {dur_text}"
            else:
                step_data["formatted_instruction"] = f"🚶 도보 이동"
            if instruction:
                step_data["formatted_instruction"] += f"\n  • {instruction}"
        
        return step_data
    
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
            
            # preferred_modes와 user_transportation 추출
            preferred_modes = kwargs.get("preferred_modes")
            user_transportation = kwargs.get("user_transportation")
            
            # 최적화된 경로로 Directions API 호출
            # preferred_modes가 있으면 각 구간별로 우선순위에 따라 시도
            directions, total_duration, total_distance = await self._get_optimized_route_directions(
                optimized_places, origin, destination, mode, preferred_modes, user_transportation
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
            error_msg = str(e)
            # API 키 관련 에러인지 확인
            if "API key" in error_msg or "INVALID_REQUEST" in error_msg or "REQUEST_DENIED" in error_msg:
                print(f"❌ Geocoding API 키 오류: {address}")
                print(f"   에러 상세: {error_msg}")
                print(f"   API 키 확인 필요: {self.api_key[:10] if self.api_key and len(self.api_key) > 10 else 'N/A'}...")
            else:
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
        
        # 대중교통 모드는 특별 처리: Distance Matrix API + 로컬 TSP 알고리즘
        if mode == 'transit':
            try:
                # 1. Distance Matrix API로 모든 쌍의 대중교통 소요 시간 획득
                duration_matrix = await self._get_transit_duration_matrix(
                    coordinates, origin, destination
                )
                
                if duration_matrix:
                    # 2. 로컬 TSP 알고리즘으로 최적 순서 계산
                    optimized_indices = self._solve_tsp_locally(
                        duration_matrix, coordinates, origin, destination
                    )
                    if optimized_indices:
                        return optimized_indices
                
                # 폴백: Nearest Neighbor 알고리즘
                print("⚠️  Transit 모드 최적화 실패, Nearest Neighbor로 폴백")
                origin_coords = None
                dest_coords = None
                if origin and origin.get("coordinates"):
                    origin_coords = (origin["coordinates"]["lat"], origin["coordinates"]["lng"])
                if destination and destination.get("coordinates"):
                    dest_coords = (destination["coordinates"]["lat"], destination["coordinates"]["lng"])
                if not origin_coords:
                    origin_coords = coordinates[0] if coordinates else None
                if not dest_coords and coordinates:
                    dest_coords = coordinates[-1]
                return self._nearest_neighbor_optimization(coordinates, origin_coords, dest_coords)
            except Exception as e:
                print(f"⚠️  Transit 모드 최적화 중 오류: {e}")
                # 폴백: Nearest Neighbor
                origin_coords = None
                dest_coords = None
                if origin and origin.get("coordinates"):
                    origin_coords = (origin["coordinates"]["lat"], origin["coordinates"]["lng"])
                if destination and destination.get("coordinates"):
                    dest_coords = (destination["coordinates"]["lat"], destination["coordinates"]["lng"])
                if not origin_coords:
                    origin_coords = coordinates[0] if coordinates else None
                if not dest_coords and coordinates:
                    dest_coords = coordinates[-1]
                return self._nearest_neighbor_optimization(coordinates, origin_coords, dest_coords)
        
        # driving, walking, bicycling 모드는 Master List 방식 사용
        try:
            # ============================================================
            # Step 1: Master List 구성 (origin + coordinates + destination)
            # ============================================================
            full_locations = []  # 통합 리스트: [origin, ...coordinates..., destination]
            location_roles = []  # 각 위치의 역할: 'origin', 'waypoint', 'destination'
            
            # 출발지 좌표 결정 및 추가
            origin_coords = None
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
            
            # 출발지가 없으면 coordinates의 첫 번째를 사용
            if not origin_coords:
                if coordinates:
                    origin_coords = coordinates[0]
                    # origin이 coordinates[0]이면 중복 추가하지 않음
                else:
                    return list(range(len(coordinates)))
            
            # 도착지 좌표 결정
            dest_coords = None
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
            
            # 도착지가 없으면 coordinates의 마지막을 사용
            if not dest_coords:
                if coordinates:
                    dest_coords = coordinates[-1]
                else:
                    dest_coords = origin_coords  # 도착지도 없으면 origin과 동일
            
            # Master List 구성
            start_idx = None
            end_idx = None
            waypoint_indices = []  # waypoint의 full_locations 내 인덱스
            
            # 출발지 추가 (coordinates[0]과 다를 때만 별도 추가)
            origin_is_separate = False
            if coordinates and abs(origin_coords[0] - coordinates[0][0]) < 0.0001 and abs(origin_coords[1] - coordinates[0][1]) < 0.0001:
                # origin이 coordinates[0]과 같으면 별도 추가하지 않음
                origin_is_separate = False
            else:
                # origin이 별도로 추가됨
                full_locations.append(origin_coords)
                location_roles.append('origin')
                start_idx = 0
                origin_is_separate = True
            
            # coordinates 추가
            coord_offset = len(full_locations)  # coordinates가 시작되는 인덱스
            for idx, coord in enumerate(coordinates):
                full_locations.append(coord)
                current_idx = len(full_locations) - 1
                
                # origin과 같은 좌표인지 확인 (허용 오차 0.0001도)
                is_origin = abs(coord[0] - origin_coords[0]) < 0.0001 and abs(coord[1] - origin_coords[1]) < 0.0001
                # destination과 같은 좌표인지 확인
                is_dest = abs(coord[0] - dest_coords[0]) < 0.0001 and abs(coord[1] - dest_coords[1]) < 0.0001
                
                if is_origin:
                    location_roles.append('origin')
                    # start_idx가 아직 설정되지 않았거나, 더 앞선 인덱스면 업데이트
                    if start_idx is None or current_idx < start_idx:
                        start_idx = current_idx
                elif is_dest:
                    location_roles.append('destination')
                    end_idx = current_idx
                else:
                    location_roles.append('waypoint')
                    waypoint_indices.append(current_idx)
            
            # destination 추가 (coordinates에 없거나 마지막과 다를 때만 별도 추가)
            dest_is_separate = False
            if coordinates and abs(dest_coords[0] - coordinates[-1][0]) < 0.0001 and abs(dest_coords[1] - coordinates[-1][1]) < 0.0001:
                # destination이 coordinates[-1]과 같으면 별도 추가하지 않음
                dest_is_separate = False
            else:
                # destination이 별도로 추가됨
                full_locations.append(dest_coords)
                location_roles.append('destination')
                end_idx = len(full_locations) - 1
                dest_is_separate = True
            
            # start_idx가 아직 설정되지 않았으면 첫 번째 인덱스 사용
            if start_idx is None:
                start_idx = 0 if full_locations else None
            
            # end_idx가 아직 설정되지 않았으면 마지막 인덱스 사용
            if end_idx is None:
                end_idx = len(full_locations) - 1 if full_locations else None
            
            # 안전성 체크
            if start_idx is None or end_idx is None or not full_locations:
                return list(range(len(coordinates)))
            
            # ============================================================
            # Step 2: 역할 인덱스 정의
            # ============================================================
            # start_idx: 출발지의 full_locations 내 인덱스
            # end_idx: 도착지의 full_locations 내 인덱스
            # waypoint_indices: 최적화 대상인 중간 장소들의 full_locations 내 인덱스 리스트
            
            # waypoint가 없거나 1개 이하면 최적화 불필요
            if len(waypoint_indices) <= 1:
                # start -> waypoints -> end 순서로 구성
                optimized_full_indices = [start_idx]
                optimized_full_indices.extend(waypoint_indices)
                if end_idx not in optimized_full_indices:
                    optimized_full_indices.append(end_idx)
                
                # 원본 coordinates 인덱스로 변환하여 반환
                return self._convert_to_coordinates_indices(
                    optimized_full_indices, full_locations, location_roles, coord_offset, coordinates
                )
            
            # ============================================================
            # Step 3: API 호출 (좌표값만 전달)
            # ============================================================
            # waypoints는 full_locations에서 waypoint_indices에 해당하는 좌표들
            waypoints_coords = [full_locations[idx] for idx in waypoint_indices]
            waypoints = [f"{lat},{lng}" for lat, lng in waypoints_coords]
            
            # Distance Matrix API를 사용한 최적화 시도 (실제 이동 수단 기반)
            # 주의: transit 모드는 이미 위에서 처리되었으므로 여기서는 driving, walking, bicycling만 처리
            if self.client and len(full_locations) <= 25 and mode != 'transit' and len(waypoint_indices) > 1:
                try:
                    # full_locations를 coordinates로 변환하여 _optimize_with_distance_matrix 호출
                    # 하지만 이 함수도 Master List 방식으로 수정이 필요할 수 있음
                    # 일단 기존 방식으로 시도
                    optimized_order = await self._optimize_with_distance_matrix(
                        coordinates, origin_coords, dest_coords, mode
                    )
                    if optimized_order:
                        return optimized_order
                except Exception as e:
                    print(f"⚠️  Distance Matrix API 최적화 실패: {e}")
                    # 폴백: Directions API의 optimize_waypoints 사용
            
            # Directions API 호출 (optimize_waypoints=True)
            # 주의: transit 모드는 optimize_waypoints를 지원하지 않으므로 사용하지 않음
            if mode == 'transit':
                # transit 모드는 이미 위에서 처리되었으므로 여기 도달하면 안 됨
                # 하지만 안전을 위해 폴백 처리
                return self._nearest_neighbor_optimization(coordinates, origin_coords, dest_coords)
            
            if len(waypoints) == 0:
                # waypoint가 없으면 start -> end 순서
                return self._convert_to_coordinates_indices(
                    [start_idx, end_idx], full_locations, location_roles, coord_offset, coordinates
                )
            
            loop = asyncio.get_event_loop()
            
            # lambda 대신 함수 정의로 변경 (클로저 문제 방지)
            origin_str = f"{full_locations[start_idx][0]},{full_locations[start_idx][1]}"
            dest_str = f"{full_locations[end_idx][0]},{full_locations[end_idx][1]}"
            
            def call_directions():
                return self.client.directions(
                    origin=origin_str,
                    destination=dest_str,
                    waypoints=waypoints,
                    optimize_waypoints=True,
                    mode=mode,
                    language='ko'  # 한국어 설정
                )
            
            directions_result = await loop.run_in_executor(None, call_directions)
            
            if not directions_result or len(directions_result) == 0:
                # API 호출 실패 시 Nearest Neighbor 알고리즘 사용
                return self._nearest_neighbor_optimization(coordinates, origin_coords, dest_coords)
            
            # ============================================================
            # Step 4: 최적화된 순서 재구성
            # ============================================================
            # 최적화된 waypoint 순서 추출
            route = directions_result[0]
            waypoint_order = route.get("waypoint_order", list(range(len(waypoint_indices))))
            
            # 최적화된 full_locations 인덱스 순서 구성
            optimized_full_indices = [start_idx]  # 출발지부터 시작
            
            # 최적화된 waypoint 순서대로 추가
            for wp_order in waypoint_order:
                if wp_order < len(waypoint_indices):
                    optimized_full_indices.append(waypoint_indices[wp_order])
            
            # 도착지 추가 (아직 포함되지 않았을 때만)
            if end_idx not in optimized_full_indices:
                optimized_full_indices.append(end_idx)
            
            # full_locations 인덱스를 원본 coordinates 인덱스로 변환
            return self._convert_to_coordinates_indices(
                optimized_full_indices, full_locations, location_roles, coord_offset, coordinates
            )
            
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
    
    def _convert_to_coordinates_indices(
        self,
        full_indices: List[int],
        full_locations: List[Tuple[float, float]],
        location_roles: List[str],
        coord_offset: int,
        coordinates: List[Tuple[float, float]]
    ) -> List[int]:
        """
        full_locations 인덱스를 원본 coordinates 인덱스로 변환
        
        Args:
            full_indices: full_locations 내 인덱스 리스트
            full_locations: 통합 위치 리스트
            location_roles: 각 위치의 역할 리스트
            coord_offset: coordinates가 시작되는 full_locations 내 인덱스
            coordinates: 원본 좌표 리스트
            
        Returns:
            원본 coordinates 인덱스 리스트
        """
        result = []
        seen = set()
        
        for full_idx in full_indices:
            if full_idx < 0 or full_idx >= len(full_locations):
                continue
            
            role = location_roles[full_idx] if full_idx < len(location_roles) else 'waypoint'
            
            # coordinates 내 인덱스로 변환
            if full_idx >= coord_offset:
                coord_idx = full_idx - coord_offset
                if 0 <= coord_idx < len(coordinates):
                    if coord_idx not in seen:
                        result.append(coord_idx)
                        seen.add(coord_idx)
            else:
                # origin이 별도로 추가된 경우, coordinates[0]을 사용
                if role == 'origin' and len(coordinates) > 0:
                    if 0 not in seen:
                        result.append(0)
                        seen.add(0)
        
        # 빠진 인덱스 추가 (원본 순서 유지)
        missing_indices = [i for i in range(len(coordinates)) if i not in seen]
        result.extend(missing_indices)
        
        return result if result else list(range(len(coordinates)))
    
    async def _get_transit_duration_matrix(
        self,
        coordinates: List[Tuple[float, float]],
        origin: Optional[Dict[str, Any]],
        destination: Optional[Dict[str, Any]]
    ) -> Optional[Dict[Tuple[int, int], int]]:
        """
        대중교통 모드를 위한 소요 시간 행렬 구축 (Distance Matrix API 사용)
        
        Args:
            coordinates: 좌표 리스트
            origin: 출발지
            destination: 도착지
            
        Returns:
            {(from_idx, to_idx): duration_seconds} 딕셔너리 또는 None
        """
        if not self.client or len(coordinates) == 0:
            return None
        
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
                origin_coords = coordinates[0] if coordinates else None
            
            if not dest_coords and len(coordinates) > 0:
                dest_coords = coordinates[-1]
            
            # 모든 좌표를 문자열로 변환 (origin + waypoints + destination)
            all_coords = []
            coord_indices = []  # 각 좌표가 원본 coordinates의 어떤 인덱스인지 추적
            
            # 출발지 추가
            if origin_coords:
                all_coords.append(f"{origin_coords[0]},{origin_coords[1]}")
                coord_indices.append(-1)  # -1은 origin을 의미
            
            # 경유지 추가
            for idx, coord in enumerate(coordinates):
                # origin/destination과 같은 좌표인지 확인
                is_origin = origin_coords and abs(coord[0] - origin_coords[0]) < 0.0001 and abs(coord[1] - origin_coords[1]) < 0.0001
                is_dest = dest_coords and abs(coord[0] - dest_coords[0]) < 0.0001 and abs(coord[1] - dest_coords[1]) < 0.0001
                
                if not is_origin and not is_dest:
                    all_coords.append(f"{coord[0]},{coord[1]}")
                    coord_indices.append(idx)
            
            # 도착지 추가
            if dest_coords:
                all_coords.append(f"{dest_coords[0]},{dest_coords[1]}")
                coord_indices.append(-2)  # -2는 destination을 의미
            
            # Distance Matrix API 호출 (최대 25개 지점 지원)
            if len(all_coords) > 25:
                print(f"⚠️  좌표가 25개를 초과하여 첫 25개만 사용합니다. (총 {len(all_coords)}개)")
                all_coords = all_coords[:25]
                coord_indices = coord_indices[:25]
            
            if len(all_coords) < 2:
                return None
            
            # 현재 시간 또는 여행 시작 시간을 departure_time으로 설정
            # 대중교통은 시간에 따라 소요 시간이 달라지므로 현재 시간 기준으로 계산
            import datetime
            departure_time = datetime.datetime.now()
            
            loop = asyncio.get_event_loop()
            distance_matrix = await loop.run_in_executor(
                None,
                lambda: self.client.distance_matrix(
                    origins=all_coords,
                    destinations=all_coords,
                    mode='transit',
                    departure_time=departure_time
                )
            )
            
            if not distance_matrix or distance_matrix.get("status") != "OK":
                print(f"⚠️  Distance Matrix API 호출 실패: {distance_matrix.get('status', 'UNKNOWN')}")
                return None
            
            rows = distance_matrix.get("rows", [])
            if not rows:
                return None
            
            # 소요 시간 행렬 구성 (경유지 간만 저장)
            duration_matrix = {}
            
            for i, row in enumerate(rows):
                elements = row.get("elements", [])
                from_idx = coord_indices[i] if i < len(coord_indices) else None
                
                # origin이나 destination은 제외 (경유지 간만 저장)
                if from_idx is None or from_idx < 0:
                    continue
                
                for j, element in enumerate(elements):
                    if element.get("status") == "OK":
                        to_idx = coord_indices[j] if j < len(coord_indices) else None
                        
                        # 경유지 간만 저장 (origin/destination 제외)
                        if to_idx is not None and to_idx >= 0:
                            duration = element.get("duration", {}).get("value", float('inf'))
                            if duration != float('inf'):
                                duration_matrix[(from_idx, to_idx)] = int(duration)
            
            return duration_matrix if duration_matrix else None
            
        except Exception as e:
            print(f"⚠️  Transit duration matrix 구축 중 오류: {e}")
            return None
    
    def _solve_tsp_locally(
        self,
        duration_matrix: Dict[Tuple[int, int], int],
        coordinates: List[Tuple[float, float]],
        origin: Optional[Dict[str, Any]],
        destination: Optional[Dict[str, Any]]
    ) -> Optional[List[int]]:
        """
        로컬 TSP 알고리즘으로 최적 순서 계산 (비대칭 비용 지원)
        
        Args:
            duration_matrix: {(from_idx, to_idx): duration_seconds} 딕셔너리
            coordinates: 좌표 리스트
            origin: 출발지
            destination: 도착지
            
        Returns:
            최적화된 순서의 인덱스 리스트 또는 None
        """
        if not duration_matrix or len(coordinates) == 0:
            return None
        
        # 출발지와 도착지 인덱스 찾기
        origin_idx = None
        dest_idx = None
        
        if origin and origin.get("coordinates"):
            origin_coords = (origin["coordinates"]["lat"], origin["coordinates"]["lng"])
            for idx, coord in enumerate(coordinates):
                if abs(coord[0] - origin_coords[0]) < 0.0001 and abs(coord[1] - origin_coords[1]) < 0.0001:
                    origin_idx = idx
                    break
        
        if destination and destination.get("coordinates"):
            dest_coords = (destination["coordinates"]["lat"], destination["coordinates"]["lng"])
            for idx, coord in enumerate(coordinates):
                if abs(coord[0] - dest_coords[0]) < 0.0001 and abs(coord[1] - dest_coords[1]) < 0.0001:
                    dest_idx = idx
                    break
        
        # 출발지가 없으면 첫 번째 좌표 사용
        if origin_idx is None:
            origin_idx = 0
        
        # 도착지가 없으면 마지막 좌표 사용
        if dest_idx is None:
            dest_idx = len(coordinates) - 1
        
        # 경유지 리스트 (origin과 destination 제외)
        waypoint_indices = [i for i in range(len(coordinates)) if i != origin_idx and i != dest_idx]
        
        if len(waypoint_indices) == 0:
            # 경유지가 없으면 origin -> destination 순서
            if origin_idx != dest_idx:
                return [origin_idx, dest_idx]
            else:
                return [origin_idx]
        
        # 개선된 Nearest Neighbor 알고리즘 사용 (비대칭 비용 고려)
        # 실제 대중교통 소요 시간을 기반으로 최적 순서 계산
        optimized_waypoints = self._nearest_neighbor_with_matrix(
            waypoint_indices, duration_matrix, origin_idx, dest_idx
        )
        
        # 최종 순서: origin -> optimized_waypoints -> destination
        result = [origin_idx]
        result.extend(optimized_waypoints)
        if dest_idx != origin_idx and dest_idx not in optimized_waypoints:
            result.append(dest_idx)
        
        return result
    
    def _nearest_neighbor_with_matrix(
        self,
        waypoint_indices: List[int],
        duration_matrix: Dict[Tuple[int, int], int],
        origin_idx: int,
        dest_idx: int
    ) -> List[int]:
        """
        비용 행렬을 사용한 개선된 Nearest Neighbor 알고리즘 (비대칭 비용 지원)
        
        Args:
            waypoint_indices: 경유지 인덱스 리스트
            duration_matrix: 소요 시간 행렬
            origin_idx: 출발지 인덱스
            dest_idx: 도착지 인덱스
            
        Returns:
            최적화된 경유지 순서 리스트
        """
        if len(waypoint_indices) == 0:
            return []
        
        if len(waypoint_indices) == 1:
            return waypoint_indices
        
        # 비용 함수
        def get_cost(from_idx: int, to_idx: int) -> float:
            if from_idx == to_idx:
                return 0.0
            key = (from_idx, to_idx)
            if key in duration_matrix:
                return float(duration_matrix[key])
            # 데이터가 없으면 큰 값 반환
            return float('inf')
        
        # 출발지에서 가장 가까운 경유지 찾기
        unvisited = set(waypoint_indices)
        optimized_order = []
        
        # 출발지에서 가장 가까운 첫 경유지 선택
        current = origin_idx
        nearest_first = None
        min_cost = float('inf')
        
        for wp in unvisited:
            cost = get_cost(current, wp)
            if cost < min_cost:
                min_cost = cost
                nearest_first = wp
        
        if nearest_first is None:
            # 비용 정보가 없으면 첫 번째 경유지 선택
            nearest_first = waypoint_indices[0]
        
        optimized_order.append(nearest_first)
        unvisited.remove(nearest_first)
        current = nearest_first
        
        # 나머지 경유지들을 Nearest Neighbor로 선택
        while unvisited:
            nearest = None
            min_cost = float('inf')
            
            for wp in unvisited:
                cost = get_cost(current, wp)
                if cost < min_cost:
                    min_cost = cost
                    nearest = wp
            
            if nearest is None:
                # 비용 정보가 없으면 남은 노드 중 첫 번째 선택
                nearest = list(unvisited)[0]
            
            optimized_order.append(nearest)
            unvisited.remove(nearest)
            current = nearest
        
        return optimized_order
    
    async def _get_optimized_route_directions(
        self,
        places: List[Dict[str, Any]],
        origin: Optional[Dict[str, Any]],
        destination: Optional[Dict[str, Any]],
        mode: str,
        preferred_modes: Optional[List[str]] = None,
        user_transportation: Optional[str] = None
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
        # 사용자가 입력한 교통수단 우선순위 적용 및 자전거 제외
        modes_to_try = preferred_modes if preferred_modes else [mode]
        # 자전거는 사용자가 명시적으로 선택하지 않은 경우 제외
        if user_transportation:
            # user_transportation에 자전거가 명시적으로 포함되어 있지 않으면 제외
            if '자전거' not in user_transportation and 'bicycling' not in user_transportation.lower():
                modes_to_try = [m for m in modes_to_try if m != 'bicycling']
        else:
            # user_transportation이 없으면 자전거 제외 (기본적으로 자전거는 사용하지 않음)
            modes_to_try = [m for m in modes_to_try if m != 'bicycling']
        
        # 자전거가 없으면 기본값 추가
        if not modes_to_try:
            modes_to_try = ['walking', 'transit', 'driving']
        
        # 첫 번째 우선 교통수단 사용
        primary_mode = modes_to_try[0] if modes_to_try else 'walking'
        
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
                            mode=primary_mode,
                            language='ko'  # 한국어 설정
                        )
                    else:
                        return self.client.directions(
                            origin=origin_str,
                            destination=dest_str,
                            mode=primary_mode,
                            language='ko'  # 한국어 설정
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
                            
                            # 단계별 경로 정보 추출 (대중교통 상세 정보 포함 및 포맷팅)
                            steps = []
                            for step in leg.get("steps", []):
                                # 포맷팅된 step 정보 생성
                                formatted_step = self._format_transit_instruction(step)
                                
                                # 경로 좌표 정보 추가 (polyline 디코딩)
                                polyline_points = []
                                if step.get("polyline"):
                                    polyline_encoded = step["polyline"].get("points", "")
                                    if polyline_encoded:
                                        polyline_points = self._decode_polyline(polyline_encoded)
                                formatted_step["path"] = polyline_points
                                
                                steps.append(formatted_step)
                            
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
        return await self._calculate_directions(places, origin, destination, mode, preferred_modes, user_transportation)
    
    async def _calculate_directions(
        self,
        places: List[Dict[str, Any]],
        origin: Optional[Dict[str, Any]],
        destination: Optional[Dict[str, Any]],
        mode: str,
        preferred_modes: Optional[List[str]] = None,
        user_transportation: Optional[str] = None
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
            """단일 구간의 Directions 정보 가져오기 - 사용자가 입력한 교통수단 우선 사용"""
            from_coord = from_item["coord"]
            to_coord = to_item["coord"]
            from_place = from_item["place"]
            to_place = to_item["place"]
            
            origin_str = f"{from_coord[0]},{from_coord[1]}"
            dest_str = f"{to_coord[0]},{to_coord[1]}"
            
            # 사용자가 입력한 교통수단 우선순위 리스트 (자전거 제외)
            modes_to_try = preferred_modes if preferred_modes else [mode]
            # 자전거는 사용자가 명시적으로 선택하지 않은 경우 제외
            if user_transportation:
                # user_transportation에 자전거가 명시적으로 포함되어 있지 않으면 제외
                if '자전거' not in user_transportation and 'bicycling' not in user_transportation.lower():
                    modes_to_try = [m for m in modes_to_try if m != 'bicycling']
            else:
                # user_transportation이 없으면 자전거 제외 (기본적으로 자전거는 사용하지 않음)
                modes_to_try = [m for m in modes_to_try if m != 'bicycling']
            
            # 자전거가 없으면 기본값 추가
            if not modes_to_try:
                modes_to_try = ['walking', 'transit', 'driving']
            
            # 각 교통수단을 우선순위대로 시도
            for try_mode in modes_to_try:
                for attempt in range(self._max_retries):
                    try:
                        def call_directions():
                            return self.client.directions(
                                origin=origin_str,
                                destination=dest_str,
                                mode=try_mode,
                                language='ko'  # 한국어 설정
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
                                    # 포맷팅된 step 정보 생성
                                    formatted_step = self._format_transit_instruction(step)
                                    
                                    # 경로 좌표 정보 추가 (polyline 디코딩)
                                    polyline_points = []
                                    if step.get("polyline"):
                                        polyline_encoded = step["polyline"].get("points", "")
                                        if polyline_encoded:
                                            polyline_points = self._decode_polyline(polyline_encoded)
                                    formatted_step["path"] = polyline_points
                                    
                                    steps.append(formatted_step)
                                
                                # 성공적으로 경로를 찾았으면 반환
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
                                    "mode": try_mode,  # 실제 사용된 교통수단
                                    "start_location": {
                                        "lat": leg.get("start_location", {}).get("lat", 0),
                                        "lng": leg.get("start_location", {}).get("lng", 0)
                                    },
                                    "end_location": {
                                        "lat": leg.get("end_location", {}).get("lat", 0),
                                        "lng": leg.get("end_location", {}).get("lng", 0)
                                    }
                                }
                        
                        # 이 모드로 경로를 찾지 못했으면 다음 모드 시도
                        break
                    
                    except Exception as e:
                        if attempt < self._max_retries - 1:
                            await asyncio.sleep(self._retry_delay * (attempt + 1))
                            continue
                        # 이 모드로 실패했으면 다음 모드 시도
                        break
                
                # 모든 모드 시도 실패
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