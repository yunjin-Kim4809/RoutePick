let map;
let geocoder;

async function initMap() {
    // google 객체가 로드되었는지 확인 (비동기 대응)
    if (typeof google === 'undefined') {
        console.log("Waiting for Google Maps SDK...");
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
            const coords = await geocodeAddress(place.address);
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
            console.warn(`${place.name} 지오코딩 실패:`, error);
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
                reject(status);
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
    card.innerHTML = `
        <img src="https://via.placeholder.com/100" alt="img">
        <div class="card-info">
            <h4>${place.name} ⭐${place.rating}</h4>
            <p>${place.address}</p>
            <p>${place.description}</p>
        </div>
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