let map;
let geocoder;
let markers = [];  // 마커 추적
let polylines = [];  // 경로 라인 추적

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

                const marker = new AdvancedMarkerElement({
                    map: map,
                    position: coords,
                    title: place.name,
                    content: pin.element,
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

    // 실제 도로 경로 그리기 (Directions Service 사용)
    if (validCoords.length > 1) {
        await drawActualRoute(validCoords, validPlaces, data);
        
        // 화면 자동 맞춤
        const bounds = new google.maps.LatLngBounds();
        validCoords.forEach(c => bounds.extend(c));
        map.fitBounds(bounds);
    }
    
    // 전역 변수 업데이트
    window.markers = markers;
    window.polylines = polylines;
};

// 실제 도로 경로 그리기 함수 (전역으로 노출)
window.drawActualRoute = async function(coords, places, courseData) {
    try {
        // Directions Service 사용 (기존 API 방식)
        const directionsService = new google.maps.DirectionsService();

        // 이동 수단 결정
        const transportation = courseData.transportation || '도보';
        let travelMode = google.maps.TravelMode.WALKING;
        
        if (transportation.includes('버스') || transportation.includes('지하철')) {
            travelMode = google.maps.TravelMode.TRANSIT;
        } else if (transportation.includes('자동차')) {
            travelMode = google.maps.TravelMode.DRIVING;
        } else if (transportation.includes('자전거')) {
            travelMode = google.maps.TravelMode.BICYCLING;
        }

        // 각 구간별로 경로 그리기
        const routePromises = [];
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
                                // 각 구간별로 별도의 Polyline 생성
                                const route = result.routes[0];
                                
                                // 경로 좌표 추출 (overview_path 사용)
                                const path = [];
                                if (route.overview_path) {
                                    route.overview_path.forEach(point => {
                                        path.push({ lat: point.lat(), lng: point.lng() });
                                    });
                                } else if (route.overview_polyline) {
                                    // overview_polyline이 있는 경우 디코딩
                                    const decodedPath = google.maps.geometry.encoding.decodePath(route.overview_polyline.points);
                                    decodedPath.forEach(point => {
                                        path.push({ lat: point.lat(), lng: point.lng() });
                                    });
                                } else {
                                    // legs에서 경로 추출
                                    route.legs.forEach(leg => {
                                        leg.steps.forEach(step => {
                                            step.path.forEach(point => {
                                                path.push({ lat: point.lat(), lng: point.lng() });
                                            });
                                        });
                                    });
                                }
                                
                                // Polyline으로 경로 그리기
                                if (path.length > 0) {
                                    const polyline = new google.maps.Polyline({
                                        path: path,
                                        strokeColor: "#4285F4",
                                        strokeOpacity: 0.8,
                                        strokeWeight: 6,
                                        map: map
                                    });
                                    polylines.push(polyline);
                                }
                                
                                resolve(true);
                            } else {
                                // 실패 시 직선으로 폴백
                                console.warn(`경로 ${i+1} 그리기 실패 (${status}), 직선으로 표시합니다.`);
                                const fallbackPolyline = new google.maps.Polyline({
                                    path: [origin, destination],
                                    strokeColor: "#FF6B6B",
                                    strokeOpacity: 0.5,
                                    strokeWeight: 3,
                                    map: map
                                });
                                polylines.push(fallbackPolyline);
                                resolve(false);
                            }
                        }
                    );
                })
            );
        }
        
        await Promise.all(routePromises);
        
    } catch (error) {
        console.error("실제 경로 그리기 실패, 직선으로 표시합니다:", error);
        // 폴백: 직선 경로
        if (coords.length > 1) {
            const fallbackPolyline = new google.maps.Polyline({
                path: coords,
                strokeColor: "#0000FF",
                strokeOpacity: 0.8,
                strokeWeight: 6,
                map: map
            });
            polylines.push(fallbackPolyline);
        }
    }
};

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