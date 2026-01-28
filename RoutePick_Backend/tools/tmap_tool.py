"""
T Map API 경로 안내 Tool
대한민국 내에서 도보 경로 안내와 자동차 경로 안내를 제공합니다.
"""

from typing import Any, Dict, List, Optional, Tuple
import os
import asyncio
import aiohttp
import urllib.parse
import json
import math
from .base_tool import BaseTool


class TMapTool(BaseTool):
    """T Map API를 사용한 경로 안내 Tool"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Args:
            config: Tool 설정 (api_key 등)
        """
        super().__init__(
            name="tmap_routing",
            description="대한민국 내에서 도보 및 자동차 경로 안내를 제공합니다.",
            config=config or {}
        )
        
        # API 키 로드
        self.api_key = (
            self.config.get("t_map_api_key") or
            os.getenv("T_MAP_API_KEY") or
            ""
        )
        
        if self.api_key:
            api_key_preview = f"{self.api_key[:6]}...{self.api_key[-4:]}" if len(self.api_key) > 12 else "***"
            print(f"🗺️ T Map API 키 로드됨: {api_key_preview}")
        else:
            print("⚠️ T Map API 키를 찾을 수 없습니다.")
        
        # API 엔드포인트
        self.base_url = "https://apis.openapi.sk.com"
        self.pedestrian_url = f"{self.base_url}/tmap/routes/pedestrian"
        self.car_url = f"{self.base_url}/tmap/routes"
    
    def _url_encode(self, text: str) -> str:
        """UTF-8 기반 URL 인코딩"""
        if not text:
            return ""
        return urllib.parse.quote(text, safe='')
    
    async def _make_request(
        self,
        url: str,
        data: Dict[str, Any],
        version: int = 1
    ) -> Optional[Dict[str, Any]]:
        """T Map API 요청"""
        if not self.api_key:
            print("❌ T Map API 키가 설정되지 않았습니다.")
            return None
        
        headers = {
            "appKey": self.api_key,
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        
        params = {"version": str(version)}
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=data, params=params, timeout=aiohttp.ClientTimeout(total=30)) as response:
                    if response.status == 200:
                        try:
                            result = await response.json()
                            # 응답이 비어있는지 확인
                            if not result or (isinstance(result, dict) and not result.get("features")):
                                response_text = await response.text()
                                print(f"⚠️ T Map API 응답이 비어있습니다. 응답 내용: {response_text[:500]}")
                                return None
                            return result
                        except Exception as e:
                            try:
                                response_text = await response.text()
                                print(f"❌ T Map API JSON 파싱 실패: {e}")
                                print(f"   응답 내용: {response_text[:500]}")
                            except:
                                print(f"❌ T Map API JSON 파싱 실패: {e}")
                            return None
                    else:
                        # 에러 응답 상세 로깅
                        response_text = await response.text()
                        print(f"❌ T Map API 요청 실패 ({response.status})")
                        print(f"   요청 URL: {url}")
                        print(f"   요청 데이터: {data}")
                        print(f"   응답 내용: {response_text[:500]}")
                        
                        # JSON 형식의 에러 응답 파싱 시도
                        error_msg = None
                        try:
                            if response_text:
                                error_json = json.loads(response_text)
                                error_msg = (
                                    error_json.get("errorMessage") or 
                                    error_json.get("message") or 
                                    error_json.get("error") or 
                                    error_json.get("statusMessage") or
                                    str(error_json)
                                )
                                print(f"   에러 메시지: {error_msg}")
                        except:
                            # JSON 파싱 실패 시 원문 출력
                            print(f"   에러 메시지 (원문): {response_text[:500]}")
                            error_msg = response_text[:200] if response_text else "알 수 없는 오류"
                        
                        # 401, 403 에러는 API 키 문제
                        if response.status in [401, 403]:
                            print(f"   → API 키 인증 문제일 수 있습니다. T Map API 키를 확인해주세요.")
                        elif response.status == 400:
                            print(f"   → 잘못된 요청입니다. 요청 파라미터를 확인해주세요.")
                            # 400 에러의 경우 특정 에러 메시지 확인
                            if error_msg and ("too near" in error_msg.lower() or "너무 가깝" in error_msg):
                                print(f"   → 두 지점이 너무 가까워 경로를 계산할 수 없습니다.")
                        elif response.status == 404:
                            print(f"   → API 엔드포인트를 찾을 수 없습니다.")
                        elif response.status == 500:
                            print(f"   → 서버 내부 오류입니다.")
                        
                        return None
        except asyncio.TimeoutError:
            print(f"❌ T Map API 요청 타임아웃 (30초 초과)")
            return None
        except Exception as e:
            print(f"❌ T Map API 요청 중 오류: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _parse_geojson_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """GeoJSON 형식 응답 파싱"""
        if not response or not isinstance(response, dict):
            raise ValueError("응답이 유효하지 않습니다.")
        
        features = response.get("features", [])
        
        if not features or not isinstance(features, list):
            raise ValueError("응답에 features가 없거나 비어있습니다.")
        
        # 총 거리, 총 시간 추출 (출발지 pointType=SP에서)
        total_distance = 0
        total_time = 0
        
        # 경로 좌표 수집
        route_coordinates = []
        route_segments = []
        instructions = []
        
        for feature in features:
            if not isinstance(feature, dict):
                continue
                
            feature_type = feature.get("type")
            geometry = feature.get("geometry", {})
            properties = feature.get("properties", {})
            
            if not isinstance(geometry, dict) or not isinstance(properties, dict):
                continue
            
            geom_type = geometry.get("type")
            coordinates = geometry.get("coordinates", [])
            
            # 출발지에서 총 거리/시간 추출
            point_type = properties.get("pointType", "")
            if point_type == "SP":  # 보행자 출발지
                total_distance = properties.get("totalDistance", 0) or 0
                total_time = properties.get("totalTime", 0) or 0
            elif point_type == "S":  # 자동차 출발지
                total_distance = properties.get("totalDistance", 0) or 0
                total_time = properties.get("totalTime", 0) or 0
            
            # LineString: 경로 구간
            if geom_type == "LineString":
                if coordinates:
                    # 좌표 형식 변환: [lng, lat] -> [lat, lng]
                    path_coords = []
                    for coord in coordinates:
                        if isinstance(coord, list) and len(coord) >= 2:
                            try:
                                lng, lat = float(coord[0]), float(coord[1])
                                path_coords.append({"lat": lat, "lng": lng})
                            except (ValueError, TypeError, IndexError):
                                continue
                    
                    if path_coords:
                        route_segments.append({
                            "path": path_coords,
                            "distance": properties.get("distance", 0) or 0,
                            "time": properties.get("time", 0) or 0,
                            "name": properties.get("name", ""),
                            "description": properties.get("description", ""),
                            "roadType": properties.get("roadType"),
                            "facilityType": properties.get("facilityType")
                        })
                        route_coordinates.extend(path_coords)
            
            # Point: 안내 지점
            elif geom_type == "Point" and coordinates:
                try:
                    if isinstance(coordinates, list) and len(coordinates) >= 2:
                        lng, lat = float(coordinates[0]), float(coordinates[1])
                    else:
                        continue
                except (ValueError, TypeError, IndexError):
                    continue
                    
                point_type = properties.get("pointType", "")
                turn_type = properties.get("turnType", 0)
                name = properties.get("name", "")
                description = properties.get("description", "")
                
                # 안내 지점 정보 수집
                if point_type in ["SP", "EP", "PP", "PP1", "PP2", "PP3", "PP4", "PP5", "GP", "S", "E", "B1", "B2", "B3", "N"]:
                    instructions.append({
                        "type": point_type,
                        "coordinates": {"lat": lat, "lng": lng},
                        "name": name,
                        "description": description,
                        "turnType": turn_type,
                        "direction": properties.get("direction", ""),
                        "intersectionName": properties.get("intersectionName", "")
                    })
        
        return {
            "total_distance": total_distance,
            "total_time": total_time,
            "route_coordinates": route_coordinates,
            "route_segments": route_segments,
            "instructions": instructions
        }
    
    async def get_pedestrian_route(
        self,
        start_x: float,
        start_y: float,
        end_x: float,
        end_y: float,
        start_name: str = "",
        end_name: str = "",
        pass_list: Optional[str] = None,
        search_option: int = 0,
        sort: str = "custom"
    ) -> Dict[str, Any]:
        """
        보행자 경로 안내
        
        Args:
            start_x: 출발지 경도
            start_y: 출발지 위도
            end_x: 목적지 경도
            end_y: 목적지 위도
            start_name: 출발지 명칭 (URL 인코딩 필요)
            end_name: 목적지 명칭 (URL 인코딩 필요)
            pass_list: 경유지 좌표 (형식: "x1,y1_x2,y2_...")
            search_option: 경로 탐색 옵션 (0: 추천, 4: 추천+대로 우선, 10: 최단, 30: 최단거리+계단 제외)
            sort: 정렬 방법 ("index" 또는 "custom")
            
        Returns:
            경로 정보 딕셔너리
        """
        data = {
            "startX": start_x,
            "startY": start_y,
            "endX": end_x,
            "endY": end_y,
            "reqCoordType": "WGS84GEO",
            "resCoordType": "WGS84GEO",
            "searchOption": search_option,
            "sort": sort
        }
        
        if start_name:
            data["startName"] = self._url_encode(start_name)
        if end_name:
            data["endName"] = self._url_encode(end_name)
        if pass_list:
            data["passList"] = pass_list
        
        response = await self._make_request(self.pedestrian_url, data)
        
        if not response:
            return {
                "success": False,
                "error": "T Map 보행자 경로 API 요청 실패. API 키 또는 서비스 구독 상태를 확인해주세요."
            }
        
        # GeoJSON 응답 파싱
        try:
            parsed = self._parse_geojson_response(response)
        except Exception as e:
            print(f"❌ T Map 응답 파싱 실패: {e}")
            return {
                "success": False,
                "error": f"T Map API 응답 파싱 실패: {str(e)}"
            }
        
        # 경로 정보가 없는 경우
        if not parsed.get("route_coordinates") and not parsed.get("route_segments"):
            return {
                "success": False,
                "error": "T Map API에서 경로 정보를 찾을 수 없습니다. 출발지와 목적지가 T Map 서비스 제공 지역인지 확인해주세요."
            }
        
        return {
            "success": True,
            "total_distance": parsed["total_distance"],
            "total_time": parsed["total_time"],
            "route_coordinates": parsed["route_coordinates"],
            "route_segments": parsed["route_segments"],
            "instructions": parsed["instructions"],
            "raw_response": response
        }
    
    async def get_car_route(
        self,
        start_x: float,
        start_y: float,
        end_x: float,
        end_y: float,
        start_name: str = "",
        end_name: str = "",
        pass_list: Optional[str] = None,
        search_option: int = 0,
        tollgate_fare_option: int = 16,
        sort: str = "custom",
        traffic_info: str = "Y",
        main_road_info: str = "Y"
    ) -> Dict[str, Any]:
        """
        자동차 경로 안내
        
        Args:
            start_x: 출발지 경도
            start_y: 출발지 위도
            end_x: 목적지 경도
            end_y: 목적지 위도
            start_name: 출발지 명칭 (URL 인코딩 필요)
            end_name: 목적지 명칭 (URL 인코딩 필요)
            pass_list: 경유지 좌표 (형식: "x1,y1_x2,y2_...")
            search_option: 경로 탐색 옵션 (0: 교통최적+추천, 1: 교통최적+무료우선, 2: 교통최적+최소시간, 등)
            tollgate_fare_option: 요금 가중치 옵션 (1: 유료/무료, 2: 최적 요금, 8: 무료 우선, 16: 로직 판단)
            sort: 정렬 방법 ("index" 또는 "custom")
            traffic_info: 교통 정보 포함 여부 ("Y" 또는 "N")
            main_road_info: 주요 도로 정보 표출 여부 ("Y" 또는 "N")
            
        Returns:
            경로 정보 딕셔너리
        """
        data = {
            "startX": start_x,
            "startY": start_y,
            "endX": end_x,
            "endY": end_y,
            "reqCoordType": "WGS84GEO",
            "resCoordType": "WGS84GEO",
            "searchOption": search_option,
            "tollgateFareOption": tollgate_fare_option,
            "sort": sort,
            "trafficInfo": traffic_info,
            "mainRoadInfo": main_road_info
        }
        
        if start_name:
            data["startName"] = self._url_encode(start_name)
        if end_name:
            data["endName"] = self._url_encode(end_name)
        if pass_list:
            data["passList"] = pass_list
        
        response = await self._make_request(self.car_url, data)
        
        if not response:
            return {
                "success": False,
                "error": "T Map 자동차 경로 API 요청 실패. API 키 또는 서비스 구독 상태를 확인해주세요."
            }
        
        # GeoJSON 응답 파싱
        try:
            parsed = self._parse_geojson_response(response)
        except Exception as e:
            print(f"❌ T Map 응답 파싱 실패: {e}")
            return {
                "success": False,
                "error": f"T Map API 응답 파싱 실패: {str(e)}"
            }
        
        # 경로 정보가 없는 경우
        if not parsed.get("route_coordinates") and not parsed.get("route_segments"):
            return {
                "success": False,
                "error": "T Map API에서 경로 정보를 찾을 수 없습니다. 출발지와 목적지가 T Map 서비스 제공 지역인지 확인해주세요."
            }
        
        # 자동차 경로의 경우 요금 정보도 추출
        total_fare = 0
        taxi_fare = 0
        
        features = response.get("features", [])
        for feature in features:
            properties = feature.get("properties", {})
            point_type = properties.get("pointType", "")
            if point_type == "S":  # 출발지
                total_fare = properties.get("totalFare", 0)
                taxi_fare = properties.get("taxiFare", 0)
                break
        
        return {
            "success": True,
            "total_distance": parsed["total_distance"],
            "total_time": parsed["total_time"],
            "total_fare": total_fare,
            "taxi_fare": taxi_fare,
            "route_coordinates": parsed["route_coordinates"],
            "route_segments": parsed["route_segments"],
            "instructions": parsed["instructions"],
            "raw_response": response
        }
    
    async def execute(
        self,
        places: List[Dict[str, Any]],
        origin: Optional[Dict[str, Any]] = None,
        destination: Optional[Dict[str, Any]] = None,
        mode: str = "walking",  # 'walking' 또는 'driving'
        optimize_waypoints: bool = True,
        **kwargs
    ) -> Dict[str, Any]:
        """
        경로 안내 실행
        
        Args:
            places: 장소 정보 리스트
            origin: 출발지 (선택사항)
            destination: 도착지 (선택사항)
            mode: 이동 수단 ('walking' 또는 'driving')
            optimize_waypoints: 경유지 순서 최적화 여부
            
        Returns:
            {
                "success": bool,
                "optimized_route": List[Dict],
                "total_duration": int,
                "total_distance": int,
                "directions": List[Dict],
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
            
            if not self.api_key:
                return {
                    "success": False,
                    "optimized_route": [],
                    "total_duration": 0,
                    "total_distance": 0,
                    "directions": [],
                    "error": "T Map API 키가 설정되지 않았습니다."
                }
            
            # 좌표 추출
            coordinates = []
            for place in places:
                coords = place.get("coordinates")
                if coords and coords.get("lat") and coords.get("lng"):
                    coordinates.append((coords["lat"], coords["lng"]))
                else:
                    return {
                        "success": False,
                        "optimized_route": [],
                        "total_duration": 0,
                        "total_distance": 0,
                        "directions": [],
                        "error": f"장소 '{place.get('name', 'Unknown')}'의 좌표가 없습니다."
                    }
            
            if len(coordinates) < 2:
                return {
                    "success": False,
                    "optimized_route": [],
                    "total_duration": 0,
                    "total_distance": 0,
                    "directions": [],
                    "error": "경로 안내를 위해 최소 2개의 장소가 필요합니다."
                }
            
            # 각 구간별로 경로 안내 요청
            directions = []
            total_duration = 0
            total_distance = 0
            
            for i in range(len(coordinates) - 1):
                start_lat, start_lng = coordinates[i]
                end_lat, end_lng = coordinates[i + 1]
                
                from_place = places[i]
                to_place = places[i + 1]
                
                # T Map API는 경도, 위도 순서로 받음
                start_x = start_lng  # 경도
                start_y = start_lat  # 위도
                end_x = end_lng
                end_y = end_lat
                
                # 두 지점 간 거리 확인 (너무 가까우면 경로 계산 불필요)
                import math
                def haversine_distance(lat1, lon1, lat2, lon2):
                    """두 지점 간 거리 계산 (미터)"""
                    R = 6371000  # 지구 반지름 (미터)
                    phi1 = math.radians(lat1)
                    phi2 = math.radians(lat2)
                    delta_phi = math.radians(lat2 - lat1)
                    delta_lambda = math.radians(lon2 - lon1)
                    
                    a = math.sin(delta_phi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda/2)**2
                    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
                    
                    return R * c
                
                distance_m = haversine_distance(start_lat, start_lng, end_lat, end_lng)
                
                # 거리가 너무 가까우면 (10미터 이하) 직접 경로로 처리
                if distance_m < 10:
                    print(f"⚠️ 두 지점이 너무 가깝습니다 ({distance_m:.1f}m). 직접 경로로 처리합니다.")
                    directions.append({
                        "from": from_place.get("name", "Unknown"),
                        "to": to_place.get("name", "Unknown"),
                        "from_address": from_place.get("address", ""),
                        "to_address": to_place.get("address", ""),
                        "duration": 0,
                        "distance": int(distance_m),
                        "duration_text": "즉시",
                        "distance_text": f"{int(distance_m)}m",
                        "steps": [{
                            "instruction": f"{from_place.get('name', '출발지')}에서 {to_place.get('name', '목적지')}까지 도보로 이동",
                            "distance": int(distance_m),
                            "distance_text": f"{int(distance_m)}m",
                            "duration": 0,
                            "duration_text": "즉시",
                            "travel_mode": mode.upper(),
                            "path": [
                                {"lat": start_lat, "lng": start_lng},
                                {"lat": end_lat, "lng": end_lng}
                            ]
                        }],
                        "mode": mode,
                        "start_location": {"lat": start_lat, "lng": start_lng},
                        "end_location": {"lat": end_lat, "lng": end_lng},
                        "route_coordinates": [
                            {"lat": start_lat, "lng": start_lng},
                            {"lat": end_lat, "lng": end_lng}
                        ]
                    })
                    total_distance += int(distance_m)
                    continue
                
                start_name = from_place.get("name", "")
                end_name = to_place.get("name", "")
                
                # 이동 수단에 따라 다른 API 호출
                if mode == "walking":
                    print(f"🚶 보행자 경로 요청: {start_name} ({start_lat:.6f}, {start_lng:.6f}) → {end_name} ({end_lat:.6f}, {end_lng:.6f})")
                    route_result = await self.get_pedestrian_route(
                        start_x=start_x,
                        start_y=start_y,
                        end_x=end_x,
                        end_y=end_y,
                        start_name=start_name,
                        end_name=end_name,
                        search_option=10  # 최단거리
                    )
                else:  # driving
                    route_result = await self.get_car_route(
                        start_x=start_x,
                        start_y=start_y,
                        end_x=end_x,
                        end_y=end_y,
                        start_name=start_name,
                        end_name=end_name,
                        search_option=0  # 교통최적+추천
                    )
                
                if not route_result.get("success"):
                    error_msg = route_result.get("error", "알 수 없는 오류")
                    print(f"⚠️ T Map API 경로 계산 실패 ({from_place.get('name', 'Unknown')} → {to_place.get('name', 'Unknown')}): {error_msg}")
                    
                    # API 키 문제인 경우 명확한 에러 반환
                    if "API 키" in error_msg or "키가 설정되지 않았습니다" in error_msg:
                        return {
                            "success": False,
                            "optimized_route": places,
                            "total_duration": 0,
                            "total_distance": 0,
                            "directions": [],
                            "error": f"T Map API 키 문제: {error_msg}. 한국 내 도보/자동차 경로 안내를 사용하려면 유효한 T Map API 키가 필요합니다."
                        }
                    
                    # 서비스 제공 지역이 아닌 경우도 명확히 표시
                    if "서비스 제공 지역" in error_msg or "경로 정보를 찾을 수 없습니다" in error_msg:
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
                            "error": f"T Map 서비스 제공 지역이 아닙니다: {error_msg}"
                        })
                        continue
                    
                    # 기타 오류는 그대로 전달
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
                        "error": error_msg
                    })
                    continue
                
                # 경로 정보 변환
                route_segments = route_result.get("route_segments", [])
                instructions = route_result.get("instructions", [])
                
                # Steps 생성
                steps = []
                for segment in route_segments:
                    step = {
                        "instruction": segment.get("description", ""),
                        "distance": segment.get("distance", 0),
                        "distance_text": f"{segment.get('distance', 0)}m",
                        "duration": segment.get("time", 0),
                        "duration_text": f"{segment.get('time', 0)}초",
                        "travel_mode": mode.upper(),
                        "path": segment.get("path", [])
                    }
                    steps.append(step)
                
                # 안내 지점을 steps에 추가
                for inst in instructions:
                    if inst.get("type") in ["GP", "PP", "PP1", "PP2", "PP3", "PP4", "PP5"]:
                        step = {
                            "instruction": inst.get("description", ""),
                            "distance": 0,
                            "distance_text": "",
                            "duration": 0,
                            "duration_text": "",
                            "travel_mode": mode.upper(),
                            "path": [inst.get("coordinates", {})],
                            "turnType": inst.get("turnType"),
                            "direction": inst.get("direction"),
                            "intersectionName": inst.get("intersectionName")
                        }
                        steps.append(step)
                
                # 거리/시간 변환
                seg_distance = route_result.get("total_distance", 0)
                seg_duration = route_result.get("total_time", 0)
                
                # 거리 텍스트 변환
                if seg_distance < 1000:
                    distance_text = f"{seg_distance}m"
                else:
                    distance_text = f"{seg_distance/1000:.1f}km"
                
                # 시간 텍스트 변환
                if seg_duration < 60:
                    duration_text = f"{seg_duration}초"
                elif seg_duration < 3600:
                    duration_text = f"{seg_duration//60}분"
                else:
                    hours = seg_duration // 3600
                    minutes = (seg_duration % 3600) // 60
                    duration_text = f"{hours}시간 {minutes}분"
                
                total_duration += seg_duration
                total_distance += seg_distance
                
                direction = {
                    "from": from_place.get("name", "Unknown"),
                    "to": to_place.get("name", "Unknown"),
                    "from_address": from_place.get("address", ""),
                    "to_address": to_place.get("address", ""),
                    "duration": seg_duration,
                    "distance": seg_distance,
                    "duration_text": duration_text,
                    "distance_text": distance_text,
                    "steps": steps,
                    "mode": mode,
                    "start_location": {"lat": start_lat, "lng": start_lng},
                    "end_location": {"lat": end_lat, "lng": end_lng},
                    "route_coordinates": route_result.get("route_coordinates", [])
                }
                
                # 자동차 경로인 경우 요금 정보 추가
                if mode == "driving":
                    direction["total_fare"] = route_result.get("total_fare", 0)
                    direction["taxi_fare"] = route_result.get("taxi_fare", 0)
                
                directions.append(direction)
            
            # 모든 구간이 실패했는지 확인
            all_failed = len(directions) > 0 and all(
                d.get("error") or (not d.get("steps") and d.get("duration", 0) == 0)
                for d in directions
            )
            
            if all_failed:
                error_messages = [d.get("error", "알 수 없는 오류") for d in directions if d.get("error")]
                if error_messages:
                    error_summary = "; ".join(error_messages[:3])
                    if len(error_messages) > 3:
                        error_summary += f" 외 {len(error_messages) - 3}개 구간 실패"
                    return {
                        "success": False,
                        "optimized_route": places,
                        "total_duration": 0,
                        "total_distance": 0,
                        "directions": directions,
                        "error": f"모든 구간의 T Map 경로 계산에 실패했습니다. {error_summary}"
                    }
            
            # 일부 구간만 성공한 경우도 success=True로 반환 (에러는 포함)
            has_valid_directions = any(
                d.get("steps") and len(d.get("steps", [])) > 0
                for d in directions
            )
            
            return {
                "success": has_valid_directions,
                "optimized_route": places,
                "total_duration": total_duration,
                "total_distance": total_distance,
                "directions": directions,
                "error": None if has_valid_directions else "일부 구간의 경로를 찾지 못했습니다."
            }
            
        except Exception as e:
            error_msg = str(e)
            print(f"❌ T Map API 실행 중 오류 발생: {error_msg}")
            return {
                "success": False,
                "optimized_route": places if places else [],
                "total_duration": 0,
                "total_distance": 0,
                "directions": [],
                "error": f"경로 계산 중 오류가 발생했습니다: {error_msg}"
            }
    
    def get_schema(self) -> Dict[str, Any]:
        """Tool 입력 스키마 반환"""
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
                    "enum": ["walking", "driving"],
                    "description": "이동 수단",
                    "default": "walking"
                },
                "optimize_waypoints": {
                    "type": "boolean",
                    "description": "경유지 순서 최적화 여부",
                    "default": True
                }
            },
            "required": ["places"]
        }
