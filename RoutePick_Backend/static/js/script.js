let map;
let geocoder;
let markers = [];  // 마커 추적
let polylines = [];  // 경로 라인 추적

function getHaversineDistanceMeters(a, b) {
    if (!a || !b) return 0;
    const toRad = (v) => (v * Math.PI) / 180;
    const lat1 = typeof a.lat === 'function' ? a.lat() : a.lat;
    const lng1 = typeof a.lng === 'function' ? a.lng() : a.lng;
    const lat2 = typeof b.lat === 'function' ? b.lat() : b.lat;
    const lng2 = typeof b.lng === 'function' ? b.lng() : b.lng;
    const R = 6371000;
    const dLat = toRad(lat2 - lat1);
    const dLng = toRad(lng2 - lng1);
    const sLat1 = toRad(lat1);
    const sLat2 = toRad(lat2);
    const aVal = Math.sin(dLat / 2) ** 2 + Math.cos(sLat1) * Math.cos(sLat2) * Math.sin(dLng / 2) ** 2;
    const c = 2 * Math.atan2(Math.sqrt(aVal), Math.sqrt(1 - aVal));
    return Math.round(R * c);
}

function getTravelModeFromTransportation(transportation) {
    const transportText = transportation || '도보';
    if (transportText.includes('버스') || transportText.includes('지하철') || transportText.includes('대중교통')) {
        return google.maps.TravelMode.TRANSIT;
    }
    if (transportText.includes('자동차')) {
        return google.maps.TravelMode.DRIVING;
    }
    return google.maps.TravelMode.WALKING;
}

async function initMap() {
    // google 객체가 로드되었는지 확인 (비동기 대응)
    if (typeof google === 'undefined') {
        console.log("Waiting for Google Maps SDK...");
        setTimeout(initMap, 100); // 0.1초 후 재시도
        return;
    }

    // importLibrary 함수가 사용 가능한지 확인
    if (typeof google.maps === 'undefined' || typeof google.maps.importLibrary !== 'function') {
        console.log("Waiting for Google Maps importLibrary...");
        setTimeout(initMap, 100); // 0.1초 후 재시도
        return;
    }

    try {
        const { Map } = await google.maps.importLibrary("maps");
        const { AdvancedMarkerElement, PinElement } = await google.maps.importLibrary("marker");
        const { Geocoder } = await google.maps.importLibrary("geocoding");

        geocoder = new Geocoder();
        
        // 전역 변수에 저장 (chatbot.js에서 사용)
        window.geocoder = geocoder;

        map = new Map(document.getElementById("map-container"), {
            zoom: 12,
            center: { lat: 37.5665, lng: 126.9780 },
            mapId: "DEMO_MAP_ID",
            disableDefaultUI: true
        });

        // 지도가 유휴 상태(완전히 그려짐)가 되면 데이터 처리 시작
        google.maps.event.addListenerOnce(map, "idle", () => {
            processLocations(AdvancedMarkerElement, PinElement);
        });
        
        // 전역 변수에 저장 (chatbot.js에서 사용)
        window.map = map;
        window.markers = markers;
        window.polylines = polylines;

    } catch (error) {
        console.error("Error loading Google Maps libraries:", error);
    }
}

// 페이지가 완전히 로드된 후 실행되도록 설정
window.addEventListener('load', () => {
    initMap();
});

// 전역으로 노출 (chatbot.js에서 사용)
window.processLocations = async function(AdvancedMarkerElement, PinElement) {
    // 백엔드 데이터 가져오기
    const taskId = window.TASK_ID;
    if (!taskId) {
        console.error('task_id가 없습니다.');
        return;
    }
    const response = await fetch(`/api/locations/${taskId}`);
    const data = await response.json();
    const places = data.places;
    const sequence = data.sequence || [];
    
    // 날씨 정보 표시 (지도 왼쪽 위)
    if (data.weather_info && Object.keys(data.weather_info).length > 0) {
        // 첫 번째 날씨 정보 사용 (모든 장소가 같은 지역이므로 동일한 날씨)
        const firstWeatherKey = Object.keys(data.weather_info)[0];
        const weather = data.weather_info[firstWeatherKey];
        if (weather && weather.temperature !== null && weather.temperature !== undefined) {
            displayWeatherOnMap(weather, data.visit_date);
        }
    }
    
    // sequence 순서대로 places 재배열
    const orderedPlaces = [];
    if (sequence.length > 0) {
        for (const idx of sequence) {
            if (idx < places.length) {
                orderedPlaces.push(places[idx]);
            }
        }
    } else {
        // sequence가 없으면 원래 순서 사용
        orderedPlaces.push(...places);
    }

    // 장소 순회 및 지오코딩
    const geocodePromises = orderedPlaces.map(async (place) => {
        try {
            // 주소가 유효하지 않으면 장소 이름으로 지오코딩 시도
            let addressToUse = place.address;
            if (!addressToUse || addressToUse === "주소 정보 확인 필요" || addressToUse.trim() === "") {
                // 장소 이름과 위치(있는 경우)를 조합해서 검색
                // location이 유효한 지역명인지 확인 (문자열 "location"이 아닌지 체크)
                const location = data.location || "";
                const isValidLocation = location && location !== "location" && location.trim() !== "";
                addressToUse = isValidLocation ? `${location} ${place.name}` : place.name;
            }
            
            const coords = await geocodeAddress(addressToUse);
            if (coords) {
                // 마커 생성
                const pin = new PinElement({
                    background: "red",
                    glyphColor: "white",
                });

                // 마커 라벨 컨테이너 생성
                const markerContainer = document.createElement("div");
                markerContainer.style.position = "relative";
                markerContainer.style.display = "flex";
                markerContainer.style.flexDirection = "column";
                markerContainer.style.alignItems = "center";
                
                // 마커 라벨 생성
                const label = document.createElement("div");
                label.textContent = place.name;
                label.style.cssText = `
                    background: rgba(255, 255, 255, 0.95);
                    color: #1a1a1a;
                    padding: 4px 8px;
                    border-radius: 4px;
                    font-size: 12px;
                    font-weight: 600;
                    white-space: nowrap;
                    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
                    margin-bottom: 4px;
                    max-width: 150px;
                    overflow: hidden;
                    text-overflow: ellipsis;
                    pointer-events: none;
                    z-index: 1000;
                `;
                
                // Pin과 라벨을 컨테이너에 추가
                markerContainer.appendChild(label);
                markerContainer.appendChild(pin.element);

                const marker = new AdvancedMarkerElement({
                    map: map,
                    position: coords,
                    title: place.name,
                    content: markerContainer,
                });
                
                // 마커 추적 배열에 추가
                markers.push(marker);

                // 카드 생성
                createEnhancedCard(place, "card-matrix");
                createEnhancedCard(place, "side-menu", "menu-item");

                return coords;
            }
        } catch (error) {
            // REQUEST_DENIED나 OVER_QUERY_LIMIT는 상세 로그를 이미 출력했으므로 간단히 표시
            const errorMsg = error.message || error;
            if (errorMsg.includes("REQUEST_DENIED") || errorMsg.includes("OVER_QUERY_LIMIT")) {
                console.error(`${place.name} 지오코딩 실패:`, errorMsg.split('\n')[0]);
            } else {
                console.warn(`${place.name} 지오코딩 실패:`, errorMsg);
            }
        }
        return null;
    });

    // 모든 마커 생성 완료 대기
    const results = await Promise.all(geocodePromises);
    const validCoords = results.filter(c => c !== null);
    const validPlaces = orderedPlaces.filter((place, idx) => results[idx] !== null);
    
    // 전역으로 보관 (경로 안내 버튼/재그리기에서 사용)
    window.routeCoords = validCoords;
    window.routePlaces = validPlaces;
    window.courseData = data;

    // 경로 안내 버튼과 동일한 경로로 초기 표시
    if (validCoords.length > 1) {
        const routePaths = await fetchRouteGuidePaths(taskId);
        const travelMode = getTravelModeFromTransportation(data.transportation);
        if (travelMode === google.maps.TravelMode.TRANSIT) {
            if (routePaths && routePaths.length > 0) {
                drawRouteFromServerData(routePaths);
            } else {
                // 폴백: 서버 경로가 없으면 기존 방식 사용
                await drawActualRoute(validCoords, validPlaces, data, { travelMode });
            }
        } else {
            // 도보/자동차는 DirectionsService 경로 우선 사용
            const drew = await drawActualRoute(validCoords, validPlaces, data, { travelMode, allowStraightFallback: false });
            if (!drew && routePaths && routePaths.length > 0) {
                drawRouteFromServerData(routePaths);
            }
        }
        const bounds = new google.maps.LatLngBounds();
        validCoords.forEach(c => bounds.extend(c));
        map.fitBounds(bounds);
    }
    
    // 전역 변수 업데이트
    window.markers = markers;
    window.polylines = polylines;
    
    // 날씨 정보가 있으면 표시 (데이터에서 다시 확인)
    if (data.weather_info && Object.keys(data.weather_info).length > 0) {
        const firstWeatherKey = Object.keys(data.weather_info)[0];
        const weather = data.weather_info[firstWeatherKey];
        if (weather && weather.temperature !== null && weather.temperature !== undefined) {
            displayWeatherOnMap(weather, data.visit_date);
        }
    }
};

// 이동 수단별 색상 정의
const TRANSPORT_COLORS = {
    'WALKING': '#4285F4',      // 파란색 - 도보
    'DRIVING': '#9C27B0',      // 보라색 - 자동차
    // 자전거는 완전히 제외됨
    'TRANSIT_BUS': '#4CAF50',  // 초록색 - 버스
    'TRANSIT_SUBWAY': '#F44336', // 빨간색 - 지하철
    'TRANSIT': '#FF9800',      // 주황색 - 기타 대중교통
    'FALLBACK': '#757575'      // 회색 - 폴백
};

// 이동 수단별 스타일 가져오기
function getTransportStyle(travelMode, transitDetails) {
    let color = TRANSPORT_COLORS.FALLBACK;
    let strokeWeight = 5;
    let strokeOpacity = 0.8;
    let zIndex = 1;
    
    if (travelMode === 'WALKING') {
        color = TRANSPORT_COLORS.WALKING;
        strokeWeight = 4;
        strokeOpacity = 0.7;
        zIndex = 1;
    } else if (travelMode === 'DRIVING') {
        color = TRANSPORT_COLORS.DRIVING;
        strokeWeight = 6;
        strokeOpacity = 0.8;
        zIndex = 2;
    } else if (travelMode === 'TRANSIT') {
        // 대중교통인 경우 세부 정보 확인
        if (transitDetails) {
            // 서버에서 받은 transitDetails는 딕셔너리 형태일 수 있음
            const line = transitDetails.line || {};
            const vehicle = line.vehicle || {};
            const vehicleType = (vehicle.type || '').toLowerCase();
            const lineName = line.name || '';
            const lineShortName = line.short_name || '';
            
            // 지하철 판단 (더 관대한 조건)
            const isSubway = (
                vehicleType === 'subway' || 
                vehicleType.includes('subway') || 
                lineName.includes('지하철') || 
                lineName.includes('호선') || 
                lineShortName.includes('호선') ||
                lineName.toLowerCase().includes('line') ||
                lineShortName.toLowerCase().includes('line')
            );
            
            // 버스 판단
            const isBus = (
                vehicleType === 'bus' || 
                vehicleType.includes('bus') || 
                lineName.includes('버스') ||
                lineShortName.includes('버스') ||
                (!isSubway && lineShortName && /\d+/.test(lineShortName))
            );
            
            if (isSubway) {
                color = TRANSPORT_COLORS.TRANSIT_SUBWAY;
                strokeWeight = 7;
                strokeOpacity = 0.9;
                zIndex = 3;
            } else if (isBus) {
                color = TRANSPORT_COLORS.TRANSIT_BUS;
                strokeWeight = 6;
                strokeOpacity = 0.8;
                zIndex = 2;
            } else {
                color = TRANSPORT_COLORS.TRANSIT;
                strokeWeight = 5;
                strokeOpacity = 0.8;
                zIndex = 2;
            }
        } else {
            color = TRANSPORT_COLORS.TRANSIT;
            strokeWeight = 5;
            strokeOpacity = 0.8;
            zIndex = 2;
        }
    }
    
    return { color, strokeWeight, strokeOpacity, zIndex };
}

// 실제 도로 경로 그리기 함수 (이동 수단별 색상 구분)
window.drawActualRoute = async function(coords, places, courseData, options = {}) {
    try {
        // Directions Service 사용
        const directionsService = new google.maps.DirectionsService();

        // 이동 수단 결정 (사용자가 입력한 교통수단 우선)
        const transportation = courseData.transportation || '도보';
        let travelMode = options.travelMode || getTravelModeFromTransportation(transportation);
        const allowStraightFallback = options.allowStraightFallback !== false;
        const useOverviewPath = travelMode === google.maps.TravelMode.WALKING || travelMode === google.maps.TravelMode.DRIVING;

        // 각 구간별로 경로 그리기
        const routePromises = [];
        let anyRouteDrawn = false;
        for (let i = 0; i < coords.length - 1; i++) {
            const origin = coords[i];
            const destination = coords[i + 1];
            
            routePromises.push(
                new Promise((resolve) => {
                    directionsService.route(
                        {
                            origin: origin,
                            destination: destination,
                            travelMode: travelMode,
                            optimizeWaypoints: false
                        },
                        (result, status) => {
                            if (status === google.maps.DirectionsStatus.OK && result.routes && result.routes.length > 0) {
                                const route = result.routes[0];
                                if (useOverviewPath && route.overview_path && route.overview_path.length > 0) {
                                    const overviewPath = route.overview_path.map(point => ({
                                        lat: point.lat(),
                                        lng: point.lng()
                                    }));
                                    const style = getTransportStyle(travelMode, null);
                                    const polyline = new google.maps.Polyline({
                                        path: overviewPath,
                                        strokeColor: style.color,
                                        strokeOpacity: style.strokeOpacity,
                                        strokeWeight: style.strokeWeight,
                                        zIndex: style.zIndex,
                                        map: map
                                    });
                                    polylines.push(polyline);
                                    anyRouteDrawn = true;
                                } else {
                                    // 각 leg의 step별로 경로 그리기 (이동 수단별 색상 구분)
                                    route.legs.forEach(leg => {
                                        leg.steps.forEach(step => {
                                            const stepPath = [];
                                            
                                            // step의 경로 좌표 추출
                                            if (step.path) {
                                                step.path.forEach(point => {
                                                    stepPath.push({ lat: point.lat(), lng: point.lng() });
                                                });
                                            }
                                            
                                            if (stepPath.length > 0) {
                                                // step의 travel_mode와 transit_details 확인
                                                const stepTravelMode = step.travel_mode || travelMode;
                                                const stepTransitDetails = step.transit_details;
                                                
                                                // 이동 수단별 스타일 가져오기
                                                const style = getTransportStyle(stepTravelMode, stepTransitDetails);
                                                
                                                // 각 step별로 polyline 생성
                                                const polyline = new google.maps.Polyline({
                                                    path: stepPath,
                                                    strokeColor: style.color,
                                                    strokeOpacity: style.strokeOpacity,
                                                    strokeWeight: style.strokeWeight,
                                                    zIndex: style.zIndex,
                                                    map: map
                                                });
                                                
                                                polylines.push(polyline);
                                                anyRouteDrawn = true;
                                            }
                                        });
                                    });
                                }
                                
                                resolve(true);
                            } else {
                                // 실패 시 직선으로 폴백
                                if (allowStraightFallback) {
                                    console.warn(`경로 ${i+1} 그리기 실패 (${status}), 직선으로 표시합니다.`);
                                    const style = getTransportStyle(travelMode, null);
                                    const fallbackPolyline = new google.maps.Polyline({
                                        path: [origin, destination],
                                        strokeColor: TRANSPORT_COLORS.FALLBACK,
                                        strokeOpacity: 0.5,
                                        strokeWeight: 3,
                                        map: map,
                                        zIndex: 0
                                    });
                                    polylines.push(fallbackPolyline);
                                } else {
                                    console.warn(`경로 ${i+1} 그리기 실패 (${status}), 직선 폴백 생략`);
                                }
                                
                                const directDistance = getHaversineDistanceMeters(origin, destination);
                                console.warn('DirectionsService 실패 상세', {
                                    segmentIndex: i + 1,
                                    status,
                                    travelMode: travelMode,
                                    origin: {
                                        lat: typeof origin.lat === 'function' ? origin.lat() : origin.lat,
                                        lng: typeof origin.lng === 'function' ? origin.lng() : origin.lng
                                    },
                                    destination: {
                                        lat: typeof destination.lat === 'function' ? destination.lat() : destination.lat,
                                        lng: typeof destination.lng === 'function' ? destination.lng() : destination.lng
                                    },
                                    directDistanceMeters: directDistance
                                });
                                resolve(false);
                            }
                        }
                    );
                })
            );
        }
        
        const results = await Promise.all(routePromises);
        const hasSuccess = results.some(Boolean) || anyRouteDrawn;
        
        // 범례 추가
        addRouteLegend();
        return hasSuccess;
        
    } catch (error) {
        console.error("실제 경로 그리기 실패, 직선으로 표시합니다:", error);
        // 폴백: 직선 경로
        if (coords.length > 1 && (options.allowStraightFallback !== false)) {
            const fallbackPolyline = new google.maps.Polyline({
                path: coords,
                strokeColor: TRANSPORT_COLORS.FALLBACK,
                strokeOpacity: 0.8,
                strokeWeight: 6,
                map: map,
                zIndex: 0
            });
            polylines.push(fallbackPolyline);
        }
        return false;
    }
};

// 서버에서 받은 경로 좌표 정보로 지도에 경로 그리기
function drawRouteFromServerData(routePaths) {
    // 경로 정보 출력 (요약 + 전체 데이터)
    const totalSegments = routePaths ? routePaths.length : 0;
    const totalSteps = routePaths ? routePaths.reduce((sum, seg) => sum + (seg ? seg.length : 0), 0) : 0;
    const totalCoords = routePaths ? routePaths.reduce((sum, seg) => {
        return sum + (seg ? seg.reduce((s, step) => s + (step.path ? step.path.length : 0), 0) : 0);
    }, 0) : 0;
    console.log(`drawRouteFromServerData 호출: 지도=${!!window.map}, ${totalSegments}개 구간, ${totalSteps}개 step, 총 ${totalCoords}개 좌표`);
    console.log('routePaths:', routePaths);
    
    if (!window.map) {
        console.error('지도가 초기화되지 않았습니다.');
        return;
    }
    
    if (!routePaths || routePaths.length === 0) {
        console.warn('경로 정보가 없습니다.');
        return;
    }
    
    // 기존 경로 제거
    if (window.polylines && window.polylines.length > 0) {
        window.polylines.forEach(polyline => {
            if (polyline.setMap) {
                polyline.setMap(null);
            }
        });
        window.polylines = [];
    }
    
    // 각 구간별로 경로 그리기
    routePaths.forEach((segmentPaths, segmentIndex) => {
        if (!segmentPaths || segmentPaths.length === 0) {
            return;
        }
        
        // 각 step별로 경로 그리기
        segmentPaths.forEach((stepData, stepIndex) => {
            const path = stepData.path || [];
            const travelMode = stepData.travel_mode || 'WALKING';
            const transitDetails = stepData.transit_details;
            
            if (path.length === 0) {
                console.warn(`구간 ${segmentIndex}, step ${stepIndex}: 경로 좌표가 없습니다.`);
                return;
            }
            
            try {
                // 경로 좌표를 Google Maps LatLng 객체로 변환
                const pathCoordinates = path.map(coord => {
                    if (!coord || typeof coord.lat !== 'number' || typeof coord.lng !== 'number') {
                        console.warn('잘못된 좌표:', coord);
                        return null;
                    }
                    return new google.maps.LatLng(coord.lat, coord.lng);
                }).filter(coord => coord !== null);
                
                if (pathCoordinates.length === 0) {
                    console.warn(`구간 ${segmentIndex}, step ${stepIndex}: 유효한 좌표가 없습니다.`);
                    return;
                }
                
                // 이동 수단별 스타일 가져오기
                const style = getTransportStyle(travelMode, transitDetails);
                
                // Polyline 생성
                const polyline = new google.maps.Polyline({
                    path: pathCoordinates,
                    strokeColor: style.color,
                    strokeOpacity: style.strokeOpacity,
                    strokeWeight: style.strokeWeight,
                    zIndex: style.zIndex,
                    map: window.map
                });
                
                // 전역 polylines 배열에 추가
                if (!window.polylines) {
                    window.polylines = [];
                }
                window.polylines.push(polyline);
                
                console.log(`경로 그리기 성공: 구간 ${segmentIndex}, step ${stepIndex}, 이동수단: ${travelMode}, 좌표 개수: ${pathCoordinates.length}`);
            } catch (error) {
                console.error(`구간 ${segmentIndex}, step ${stepIndex} 경로 그리기 실패:`, error);
            }
        });
    });
    
    // 범례 추가
    addRouteLegend();
    
    // 지도 범위 조정 (모든 경로가 보이도록)
    if (window.polylines.length > 0) {
        const bounds = new google.maps.LatLngBounds();
        window.polylines.forEach(polyline => {
            const path = polyline.getPath();
            if (path) {
                path.forEach(point => {
                    bounds.extend(point);
                });
            }
        });
        window.map.fitBounds(bounds);
    }
}

// 서버 경로 안내 API에서 경로 좌표만 가져오기
async function fetchRouteGuidePaths(taskId) {
    if (!taskId) return null;
    try {
        const response = await fetch(`/api/route-guide/${taskId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        if (!response.ok) {
            console.warn('경로 안내 API 응답 실패:', response.status);
            return null;
        }
        const data = await response.json();
        return data.route_paths || null;
    } catch (error) {
        console.warn('경로 안내 API 호출 실패:', error);
        return null;
    }
}

// 전역으로 노출 (chatbot.js에서 사용)
window.fetchRouteGuidePaths = fetchRouteGuidePaths;
window.drawRouteFromServerData = drawRouteFromServerData;
window.getTravelModeFromTransportation = getTravelModeFromTransportation;

// 지도 왼쪽 위에 날씨 정보 표시 함수
function displayWeatherOnMap(weather, visitDate) {
    // 기존 날씨 정보 제거
    const existingWeather = document.getElementById('weather-widget');
    if (existingWeather) {
        existingWeather.remove();
    }
    
    // 날씨 위젯 생성
    const weatherWidget = document.createElement('div');
    weatherWidget.id = 'weather-widget';
    weatherWidget.style.cssText = `
        position: absolute;
        top: 20px;
        left: 20px;
        background: rgba(255, 255, 255, 0.95);
        backdrop-filter: blur(10px);
        padding: 12px 16px;
        border-radius: 12px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        font-size: 14px;
        z-index: 1000;
        display: flex;
        align-items: center;
        gap: 10px;
        min-width: 180px;
    `;
    
    // 날씨 아이콘 처리
    let iconHtml = '🌤';
    if (weather.icon) {
        const iconType = weather.icon_type;
        const icon = weather.icon;
        // icon_type이 없거나 google이거나 http로 시작하면 전체 URL로 간주
        const iconUrl = (!iconType || iconType === 'google' || icon.startsWith('http')) 
            ? icon  // Google Weather API: 전체 URL 사용
            : `https://openweathermap.org/img/wn/${icon}@2x.png`;  // OpenWeatherMap: 코드를 URL로 변환
        iconHtml = `<img src="${iconUrl}" alt="${weather.condition || ''}" style="width: 32px; height: 32px; object-fit: contain;" />`;
    }
    
    // 온도와 날씨 조건 표시
    const temp = weather.temperature !== null && weather.temperature !== undefined 
        ? `${Math.round(weather.temperature)}°C` 
        : '';
    const condition = weather.condition || weather.description || '';
    const dateLabel = weather.date || visitDate || '';
    
    weatherWidget.innerHTML = `
        <div style="display: flex; align-items: center; gap: 10px; flex: 1;">
            <div style="font-size: 24px; line-height: 1;">
                ${iconHtml}
            </div>
            <div style="display: flex; flex-direction: column; gap: 2px;">
                <div style="font-weight: 700; font-size: 18px; color: #1a1a1a; line-height: 1.2;">
                    ${temp}
                </div>
                <div style="font-size: 12px; color: #666; line-height: 1.2;">
                    ${condition}
                </div>
                ${dateLabel ? `<div style="font-size: 11px; color: #888; line-height: 1.2;">${dateLabel}</div>` : ''}
            </div>
        </div>
    `;
    
    // 지도 컨테이너에 추가
    const mapContainer = document.getElementById('map-container');
    if (mapContainer) {
        mapContainer.appendChild(weatherWidget);
    }
}

// 전역으로 노출 (chatbot.js에서 사용)
window.displayWeatherOnMap = displayWeatherOnMap;

// 경로 범례 추가 함수
function addRouteLegend() {
    // 기존 범례 제거
    const existingLegend = document.getElementById('route-legend');
    if (existingLegend) {
        existingLegend.remove();
    }
    
    // 범례 생성
    const legend = document.createElement('div');
    legend.id = 'route-legend';
    legend.style.cssText = `
        position: absolute;
        bottom: 20px;
        left: 20px;
        background: white;
        padding: 12px 16px;
        border-radius: 8px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.2);
        font-family: sans-serif;
        font-size: 12px;
        z-index: 1000;
        max-width: 200px;
    `;
    
    legend.innerHTML = `
        <div style="font-weight: bold; margin-bottom: 8px; color: #333;">이동 수단</div>
        <div style="display: flex; align-items: center; margin-bottom: 4px;">
            <div style="width: 20px; height: 4px; background: ${TRANSPORT_COLORS.WALKING}; margin-right: 8px; border-radius: 2px;"></div>
            <span>도보</span>
        </div>
        <div style="display: flex; align-items: center; margin-bottom: 4px;">
            <div style="width: 20px; height: 4px; background: ${TRANSPORT_COLORS.TRANSIT_SUBWAY}; margin-right: 8px; border-radius: 2px;"></div>
            <span>지하철</span>
        </div>
        <div style="display: flex; align-items: center; margin-bottom: 4px;">
            <div style="width: 20px; height: 4px; background: ${TRANSPORT_COLORS.TRANSIT_BUS}; margin-right: 8px; border-radius: 2px;"></div>
            <span>버스</span>
        </div>
        <div style="display: flex; align-items: center;">
            <div style="width: 20px; height: 4px; background: ${TRANSPORT_COLORS.DRIVING}; margin-right: 8px; border-radius: 2px;"></div>
            <span>자동차</span>
        </div>
    `;
    
    // 지도 컨테이너에 범례 추가
    const mapContainer = document.getElementById('map-container');
    if (mapContainer) {
        mapContainer.appendChild(legend);
    }
}

// 주소 -> 좌표 변환 함수 (전역으로 노출)
window.geocodeAddress = function(address) {
    return new Promise((resolve, reject) => {
        geocoder.geocode({ address: address }, (results, status) => {
            if (status === "OK") {
                resolve(results[0].geometry.location);
            } else {
                // 상세한 에러 정보 로깅
                let errorMessage = `Geocoding 실패 (${status}): ${address}`;
                
                if (status === "REQUEST_DENIED") {
                    errorMessage += "\n⚠️ 해결 방법:\n";
                    errorMessage += "1. Google Cloud Console > 사용자 인증 정보에서 API 키 선택\n";
                    errorMessage += "2. 'API 제한사항'에서 'Geocoding API'가 허용되었는지 확인\n";
                    errorMessage += "3. '애플리케이션 제한사항'도 확인\n";
                    errorMessage += "4. 결제 계정이 설정되어 있는지 확인";
                    console.error("⚠️ 구글 API 에러:", errorMessage);
                } else if (status === "OVER_QUERY_LIMIT") {
                    errorMessage += "\n⚠️ 할당량 초과: 일일 할당량을 초과했거나 결제 계정이 설정되지 않았을 수 있습니다.";
                    console.error("⚠️ 구글 API 에러:", errorMessage);
                } else if (status === "ZERO_RESULTS") {
                    console.warn(`주소를 찾을 수 없음: ${address}`);
                } else {
                    console.error("⚠️ 구글 API 에러:", errorMessage);
                }
                
                reject(new Error(errorMessage));
            }
        });
    });
};

// 카드 생성 함수 (전역으로 노출)
window.createEnhancedCard = function(place, containerId, className = "card") {
    const container = document.getElementById(containerId);
    if (!container) return;
    
    const card = document.createElement("div");
    card.className = className;
    // 이미지 URL 설정 (있는 경우 사용, 없으면 placeholder)
    const imageUrl = place.photo_url || "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='100' height='100'%3E%3Crect fill='%23ddd' width='100' height='100'/%3E%3Ctext fill='%23999' font-family='sans-serif' font-size='14' dy='10.5' font-weight='bold' x='50%25' y='50%25' text-anchor='middle'%3E이미지%3C/text%3E%3C/svg%3E";
    
    // Google Maps 링크 생성
    let mapLink = "#";
    if (place.map_url) {
        mapLink = place.map_url;
    } else if (place.coordinates && place.coordinates.lat && place.coordinates.lng) {
        // 좌표가 있으면 좌표로 링크 생성
        mapLink = `https://www.google.com/maps?q=${place.coordinates.lat},${place.coordinates.lng}`;
    } else if (place.address) {
        // 주소가 있으면 주소로 링크 생성
        const query = encodeURIComponent(`${place.name} ${place.address}`);
        mapLink = `https://www.google.com/maps/search/?api=1&query=${query}`;
    } else if (place.name) {
        // 이름만 있으면 이름으로 링크 생성
        const query = encodeURIComponent(place.name);
        mapLink = `https://www.google.com/maps/search/?api=1&query=${query}`;
    }
    
    // 카테고리별 아이콘
    const categoryIcons = {
        '관광지': '🏛️',
        '식당': '🍽️',
        '카페': '☕',
        '쇼핑': '🛍️',
        '숙소': '🏨',
        '활동': '🎯'
    };
    const categoryIcon = categoryIcons[place.category] || '📍';
    
    card.innerHTML = `
        <div style="position: relative; overflow: hidden;">
            <img src="${imageUrl}" alt="${place.name}" onerror="this.src='data:image/svg+xml,%3Csvg xmlns=\\'http://www.w3.org/2000/svg\\' width=\\'100\\' height=\\'100\\'%3E%3Crect fill=\\'%23ddd\\' width=\\'100\\' height=\\'100\\'/%3E%3Ctext fill=\\'%23999\\' font-family=\\'sans-serif\\' font-size=\\'14\\' dy=\\'10.5\\' font-weight=\\'bold\\' x=\\'50%25\\' y=\\'50%25\\' text-anchor=\\'middle\\'%3E이미지%3C/text%3E%3C/svg%3E';" style="width: 140px; height: 100%; object-fit: cover; display: block;">
            <div style="position: absolute; top: 8px; left: 8px; background: rgba(255,255,255,0.95); backdrop-filter: blur(8px); padding: 4px 8px; border-radius: 12px; font-size: 11px; font-weight: 600; color: #1a1a1a; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                ${categoryIcon} ${place.category || '장소'}
            </div>
        </div>
        <a href="${mapLink}" target="_blank" rel="noopener noreferrer" class="card-info-link">
            <div class="card-info">
                <div style="display: flex; align-items: baseline; gap: 6px; margin-bottom: 4px;">
                    <h4 class="font-semibold text-route-black">${place.name}</h4>
                    <span class="rating" style="display: inline-flex; align-items: center; gap: 2px;">⭐${place.rating || 'N/A'}</span>
                </div>
                <p class="addr text-gray-600">${place.address || '주소 정보 없음'}</p>
                ${place.description ? `<p class="desc text-gray-500">${place.description}</p>` : ''}
                ${place.weather_info ? `
                    <div style="display: flex; align-items: center; gap: 6px; margin-top: 8px; padding: 6px 8px; background: rgba(59, 130, 246, 0.1); border-radius: 8px;">
                        ${place.weather_info.icon ? (() => {
                            // 아이콘 URL 처리 (Google Weather API는 전체 URL, OpenWeatherMap은 코드만)
                            const icon = place.weather_info.icon;
                            const iconType = place.weather_info.icon_type;
                            // icon_type이 없거나 google이거나 http로 시작하면 전체 URL로 간주
                            const iconUrl = (!iconType || iconType === 'google' || icon.startsWith('http')) 
                                ? icon  // Google Weather API: 전체 URL 사용
                                : `https://openweathermap.org/img/wn/${icon}@2x.png`;  // OpenWeatherMap: 코드를 URL로 변환
                            return `<img src="${iconUrl}" alt="${place.weather_info.condition || ''}" style="width: 24px; height: 24px;" />`;
                        })() : '🌤'}
                        <span style="font-weight: 600; color: #1a1a1a; font-size: 14px;">${place.weather_info.temperature !== null && place.weather_info.temperature !== undefined ? `${place.weather_info.temperature}°C` : ''}</span>
                        <span style="color: #666; font-size: 13px;">${place.weather_info.condition || place.weather_info.description || ''}</span>
                        ${place.weather_info.humidity !== null && place.weather_info.humidity !== undefined ? `<span style="color: #888; font-size: 12px; margin-left: 4px;">습도 ${place.weather_info.humidity}%</span>` : ''}
                    </div>
                ` : ''}
            </div>
        </a>
    `;
    container.appendChild(card);
};

// (a) 챗봇 로직
async function sendMessage() {
    const input = document.getElementById("chat-input");
    const window = document.getElementById("chat-window");
    const text = input.value;
    if (!text) return;

    window.innerHTML += `<div><strong>사용자:</strong> ${text}</div>`;
    input.value = "";

    const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text })
    });
    const data = await response.json();
    window.innerHTML += `<div><strong>Bot:</strong> ${data.response}</div>`;
    window.scrollTop = window.scrollHeight;
}

// (d) 햄버거 토글 로직
document.getElementById("menu-toggle").addEventListener("click", function() {
    this.classList.toggle("active");
    document.getElementById("side-menu").classList.toggle("active");
});

// 경로 안내 버튼 클릭 이벤트
document.addEventListener('DOMContentLoaded', () => {
    const routeGuideBtn = document.getElementById('route-guide-btn');
    if (routeGuideBtn) {
        routeGuideBtn.addEventListener('click', async () => {
            const taskId = window.TASK_ID;
            if (!taskId) {
                alert('오류: task_id가 없습니다.');
                return;
            }
            
            // 버튼 비활성화 및 로딩 표시
            routeGuideBtn.disabled = true;
            routeGuideBtn.textContent = '경로 안내 생성 중...';
            
            try {
                const response = await fetch(`/api/route-guide/${taskId}`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    }
                });
                
                if (!response.ok) {
                    throw new Error('경로 안내 생성에 실패했습니다.');
                }
                
                const data = await response.json();
                
                // 채팅창에 경로 안내 메시지 추가
                if (window.appendMessage) {
                    window.appendMessage('bot', data.guide);
                } else {
                    // chatbot.js의 appendMessage 함수 사용
                    const chatWindow = document.getElementById('chat-window');
                    if (chatWindow) {
                        const msgDiv = document.createElement('div');
                        msgDiv.className = 'message bot-message';
                        const formattedText = data.guide.replace(/\n/g, '<br>');
                        msgDiv.innerHTML = `<strong>AI:</strong> <span>${formattedText}</span>`;
                        chatWindow.appendChild(msgDiv);
                        chatWindow.scrollTop = chatWindow.scrollHeight;
                    }
                }
                
                // 서버에서 받은 경로 좌표 정보로 지도에 경로 그리기
                if (data.route_paths && window.map) {
                    // 경로 좌표 정보 출력 (요약 + 전체 데이터)
                    const totalSegments = data.route_paths ? data.route_paths.length : 0;
                    const totalSteps = data.route_paths ? data.route_paths.reduce((sum, seg) => sum + (seg ? seg.length : 0), 0) : 0;
                    const totalCoords = data.route_paths ? data.route_paths.reduce((sum, seg) => {
                        return sum + (seg ? seg.reduce((s, step) => s + (step.path ? step.path.length : 0), 0) : 0);
                    }, 0) : 0;
                    console.log(`경로 좌표 정보 수신: ${totalSegments}개 구간, ${totalSteps}개 step, 총 ${totalCoords}개 좌표`);
                    console.log('경로 좌표 정보:', data.route_paths);
                    
                    // window.polylines 초기화 (없으면 생성)
                    if (!window.polylines) {
                        window.polylines = [];
                    }
                    
                    // 기존 경로 제거
                    if (window.polylines && window.polylines.length > 0) {
                        window.polylines.forEach(polyline => {
                            if (polyline.setMap) {
                                polyline.setMap(null);
                            }
                        });
                        window.polylines = [];
                    }
                    
                    const routePaths = data.route_paths;
                    const hasTransit = routePaths.some(segment =>
                        (segment || []).some(step => (step.travel_mode || '').toUpperCase() === 'TRANSIT')
                    );
                    
                    if (!hasTransit && window.routeCoords && window.routePlaces && window.courseData) {
                        // 도보/자동차는 DirectionsService 경로 우선 사용
                        (async () => {
                            const drew = await drawActualRoute(window.routeCoords, window.routePlaces, window.courseData, {
                                travelMode: getTravelModeFromTransportation(window.courseData.transportation),
                                allowStraightFallback: false
                            });
                            if (!drew && routePaths && routePaths.length > 0) {
                                drawRouteFromServerData(routePaths);
                            }
                        })();
                    } else {
                        // 서버에서 받은 경로 좌표 정보로 경로 그리기
                        drawRouteFromServerData(routePaths);
                    }
                } else {
                    console.warn('경로 그리기 조건 불만족:', {
                        hasRoutePaths: !!data.route_paths,
                        hasMap: !!window.map,
                        routePathsLength: data.route_paths ? data.route_paths.length : 0
                    });
                }
            } catch (error) {
                console.error('경로 안내 오류:', error);
                alert('경로 안내를 생성하는 중 오류가 발생했습니다.');
            } finally {
                // 버튼 활성화 및 텍스트 복원
                routeGuideBtn.disabled = false;
                routeGuideBtn.textContent = '경로 안내';
            }
        });
    }
});