let map;
let geocoder;

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

    } catch (error) {
        console.error("Error loading Google Maps libraries:", error);
    }
}

// 페이지가 완전히 로드된 후 실행되도록 설정
window.addEventListener('load', () => {
    initMap();
});

async function processLocations(AdvancedMarkerElement, PinElement) {
    // 백엔드 데이터 가져오기
    const response = await fetch('/api/locations');
    const data = await response.json();
    const places = data.places;

    const pathCoords = [];

    // 장소 순회 및 지오코딩
    const geocodePromises = places.map(async (place) => {
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

                new AdvancedMarkerElement({
                    map: map,
                    position: coords,
                    title: place.name,
                    content: pin.element,
                });

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

    // 경로 그리기 (Polyline)
    if (validCoords.length > 1) {
        new google.maps.Polyline({
            path: validCoords,
            strokeColor: "#0000FF",
            strokeOpacity: 0.8,
            strokeWeight: 6,
            map: map
        });

        // 화면 자동 맞춤
        const bounds = new google.maps.LatLngBounds();
        validCoords.forEach(c => bounds.extend(c));
        map.fitBounds(bounds);
    }
}

// 주소 -> 좌표 변환 함수
function geocodeAddress(address) {
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
}

// 카드 생성 함수
function createEnhancedCard(place, containerId, className = "card") {
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
    
    card.innerHTML = `
        <img src="${imageUrl}" alt="${place.name}" onerror="this.src='data:image/svg+xml,%3Csvg xmlns=\\'http://www.w3.org/2000/svg\\' width=\\'100\\' height=\\'100\\'%3E%3Crect fill=\\'%23ddd\\' width=\\'100\\' height=\\'100\\'/%3E%3Ctext fill=\\'%23999\\' font-family=\\'sans-serif\\' font-size=\\'14\\' dy=\\'10.5\\' font-weight=\\'bold\\' x=\\'50%25\\' y=\\'50%25\\' text-anchor=\\'middle\\'%3E이미지%3C/text%3E%3C/svg%3E';">
        <a href="${mapLink}" target="_blank" rel="noopener noreferrer" class="card-info-link">
            <div class="card-info">
                <h4>${place.name} ⭐${place.rating}</h4>
                <p>${place.address}</p>
                <p>${place.description}</p>
            </div>
        </a>
    `;
    container.appendChild(card);
}

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