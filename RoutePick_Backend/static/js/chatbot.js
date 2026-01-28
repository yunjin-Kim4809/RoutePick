document.addEventListener('DOMContentLoaded', () => {
    const chatInput = document.getElementById('chat-input');
    const chatWindow = document.getElementById('chat-window');
    const sendBtn = document.getElementById('send-btn');

    // 빠른 질문 버튼들
    const quickQuestions = [
        "이 코스는 몇 시간 정도 걸리나요?",
        "가장 추천하는 장소는 어디인가요?",
        "교통편은 어떻게 이용하나요?",
        "각 장소에서 얼마나 머물면 되나요?",
        "코스를 수정할 수 있나요?"
    ];

    // 초기 코스 정보 로드 및 표시
    async function loadCourseInfo() {
        try {
            const taskId = window.TASK_ID;
            if (!taskId) {
                console.error('task_id가 없습니다.');
                return;
            }
            const response = await fetch(`/api/locations/${taskId}`);
            const data = await response.json();
            
            if (data && data.places && data.places.length > 0) {
                // 환영 메시지
                appendMessage('bot', '안녕하세요! 😊 RoutePick AI 가이드입니다. 코스에 대해 궁금한 점이 있으시면 언제든지 물어보세요!', true);
                
                // 코스 설명 표시
                // if (data.course_description) {
                //     appendMessage('bot', `<div style="margin-bottom: 12px;"><strong style="font-size: 1.15em; color: #C5A683; display: block; margin-bottom: 8px;">📝 코스 설명</strong></div>${data.course_description}`, true);
                // }
                
                // 방문 순서 표시
                const sequence = data.sequence || [];
                const places = data.places || [];
                const estimated_duration = data.estimated_duration || {};
                const weather_info = data.weather_info || {};  // weather_info 변수 추가
                
                if (sequence.length > 0 && places.length > 0) {
                    let courseMessage = '<div style="margin-bottom: 12px;"><strong style="font-size: 1.15em; color: #C5A683; display: block; margin-bottom: 12px;">📍 방문 순서</strong></div>';
                    
                    sequence.forEach((placeIdx, idx) => {
                        if (placeIdx < places.length) {
                            const place = places[placeIdx];
                            const duration = estimated_duration[placeIdx] || estimated_duration[String(placeIdx)] || '정보 없음';
                            
                            courseMessage += `<div style="margin-bottom: 16px; padding: 16px; background: linear-gradient(135deg, rgba(197, 166, 131, 0.08) 0%, rgba(197, 166, 131, 0.03) 100%); border-radius: 16px; border-left: 4px solid #C5A683; transition: all 0.3s ease;">`;
                            courseMessage += `<div style="font-weight: 700; font-size: 1.1em; margin-bottom: 10px; color: #1a1a1a; letter-spacing: -0.01em;">${idx + 1}. ${place.name || '알 수 없음'}</div>`;
                            courseMessage += `<div style="font-size: 0.9em; color: #555; line-height: 1.8;">`;
                            courseMessage += `<div style="margin-bottom: 4px;">📌 <span style="color: #888; font-weight: 500;">카테고리:</span> <span style="color: #1a1a1a;">${place.category || 'N/A'}</span></div>`;
                            courseMessage += `<div style="margin-bottom: 4px;">⏱ <span style="color: #888; font-weight: 500;">체류 시간:</span> <span style="color: #1a1a1a; font-weight: 600;">${duration}분</span></div>`;
                            courseMessage += `<div style="margin-bottom: 4px;">⭐ <span style="color: #888; font-weight: 500;">평점:</span> <span style="color: #f39c12; font-weight: 600;">${place.rating || 'N/A'}</span></div>`;
                            
                            // 날씨 정보 표시 (data.weather_info 사용)
                            if (weather_info && weather_info[placeIdx]) {
                                const weather = weather_info[placeIdx];
                                if (weather.temperature !== null && weather.temperature !== undefined) {
                                    // 아이콘 URL 처리 (Google Weather API는 전체 URL, OpenWeatherMap은 코드만)
                                    let weatherIcon = '';
                                    if (weather.icon) {
                                        // icon_type이 없거나 google이거나 http로 시작하면 전체 URL로 간주
                                        if (!weather.icon_type || weather.icon_type === 'google' || weather.icon.startsWith('http')) {
                                            // Google Weather API: 전체 URL 사용
                                            weatherIcon = weather.icon;
                                        } else {
                                            // OpenWeatherMap: 코드를 URL로 변환
                                            weatherIcon = `https://openweathermap.org/img/wn/${weather.icon}@2x.png`;
                                        }
                                    }
                                    courseMessage += `<div style="margin-bottom: 4px; display: flex; align-items: center; gap: 6px;">`;
                                    courseMessage += `<span style="color: #888; font-weight: 500;">🌤 날씨:</span>`;
                                    if (weatherIcon) {
                                        courseMessage += `<img src="${weatherIcon}" alt="${weather.condition}" style="width: 24px; height: 24px; vertical-align: middle;" />`;
                                    }
                                    courseMessage += `<span style="color: #1a1a1a; font-weight: 600;">${weather.temperature}°C</span>`;
                                    courseMessage += `<span style="color: #666; margin-left: 4px;">${weather.condition || weather.description || ''}</span>`;
                                    if (weather.humidity !== null && weather.humidity !== undefined) {
                                        courseMessage += `<span style="color: #888; margin-left: 8px; font-size: 0.85em;">습도 ${weather.humidity}%</span>`;
                                    }
                                    courseMessage += `</div>`;
                                }
                            }
                            
                            courseMessage += `<div style="margin-bottom: 6px;">📍 <span style="color: #888; font-weight: 500;">주소:</span> <span style="color: #1a1a1a;">${place.address || '주소 정보 없음'}</span></div>`;
                            if (place.map_url) {
                                courseMessage += `<div><a href="${place.map_url}" target="_blank" style="color: #C5A683; text-decoration: none; font-weight: 600; border-bottom: 1px solid #C5A683; padding-bottom: 1px; transition: color 0.2s;">🔗 지도 보기</a></div>`;
                            }
                            courseMessage += `</div></div>`;
                        }
                    });
                    
                    appendMessage('bot', courseMessage, true);
                }
                
                // 선정 이유 표시
                if (data.reasoning) {
                    appendMessage('bot', `<div style="margin-bottom: 12px;"><strong style="font-size: 1.15em; color: #C5A683; display: block; margin-bottom: 8px;">💡 코스 설명</strong></div>${data.course_description}`, true);
                }
                
                // 초기 빠른 질문 버튼 표시
                setTimeout(() => {
                    showQuickQuestions();
                }, 500);
            }
        } catch (error) {
            console.error('코스 정보 로드 실패:', error);
        }
    }

    async function sendMessage(messageText = null) {
        const message = messageText || chatInput.value.trim();
        if (!message) return;

        // 유저 메시지 화면에 추가
        appendMessage('user', message);
        chatInput.value = '';
        
        // 빠른 질문 버튼 숨기기
        hideQuickQuestions();

        // 로딩 메시지 표시
        const loadingId = showLoadingMessage();

        try {
            const taskId = window.TASK_ID;
            if (!taskId) {
                removeLoadingMessage(loadingId);
                appendMessage('bot', '오류: task_id가 없습니다.');
                return;
            }
            
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: message, taskId: taskId })
            });
            const data = await response.json();
            
            // 로딩 메시지 제거
            removeLoadingMessage(loadingId);
            
            // 봇 메시지를 타이핑 애니메이션으로 표시
            appendMessageWithTyping('bot', data.response, () => {
                // 코스가 업데이트되었으면 지도와 카드 업데이트
                if (data.course_updated && data.course) {
                    updateCourseDisplay(data.course);
                }
            });
        } catch (error) {
            removeLoadingMessage(loadingId);
            appendMessage('bot', '오류가 발생했습니다. 다시 시도해주세요. 😔');
        }
    }
    
    function showLoadingMessage() {
        const loadingId = 'loading-' + Date.now();
        const msgDiv = document.createElement('div');
        msgDiv.id = loadingId;
        msgDiv.className = 'message bot-message';
        msgDiv.innerHTML = `
            <div style="display: flex; align-items: flex-start; gap: 8px;">
                <div style="width: 24px; height: 24px; border-radius: 50%; background: linear-gradient(135deg, #C5A683, #a0855f); display: flex; align-items: center; justify-content: center; flex-shrink: 0; margin-top: 2px;">
                    <span style="color: white; font-size: 10px; font-weight: bold;">AI</span>
                </div>
                <div style="flex: 1;">
                    <div class="typing-indicator">
                        <span></span>
                        <span></span>
                        <span></span>
                    </div>
                </div>
            </div>
        `;
        chatWindow.appendChild(msgDiv);
        chatWindow.scrollTo({
            top: chatWindow.scrollHeight,
            behavior: 'smooth'
        });
        return loadingId;
    }
    
    function removeLoadingMessage(loadingId) {
        const loadingMsg = document.getElementById(loadingId);
        if (loadingMsg) {
            loadingMsg.remove();
        }
    }
    
    function appendMessageWithTyping(sender, text, speed = 30, onComplete = null) {
        const msgDiv = document.createElement('div');
        msgDiv.className = `message ${sender}-message`;
        
        if (sender === 'bot') {
            msgDiv.innerHTML = `
                <div style="display: flex; align-items: flex-start; gap: 8px;">
                    <div style="width: 24px; height: 24px; border-radius: 50%; background: linear-gradient(135deg, #C5A683, #a0855f); display: flex; align-items: center; justify-content: center; flex-shrink: 0; margin-top: 2px;">
                        <span style="color: white; font-size: 10px; font-weight: bold;">AI</span>
                    </div>
                    <div style="flex: 1;">
                        <span class="typing-text"></span>
                    </div>
                </div>
            `;
        } else {
            msgDiv.innerHTML = `<span class="typing-text"></span>`;
        }
        
        chatWindow.appendChild(msgDiv);
        chatWindow.scrollTo({
            top: chatWindow.scrollHeight,
            behavior: 'smooth'
        });
        
        const typingElement = msgDiv.querySelector('.typing-text');
        let index = 0;
        const formattedText = text.replace(/\n/g, '<br>');
        
        function typeChar() {
            if (index < formattedText.length) {
                // HTML 태그는 한 번에 추가
                if (formattedText[index] === '<') {
                    const tagEnd = formattedText.indexOf('>', index);
                    if (tagEnd !== -1) {
                        typingElement.innerHTML += formattedText.substring(index, tagEnd + 1);
                        index = tagEnd + 1;
                    } else {
                        typingElement.innerHTML += formattedText[index];
                        index++;
                    }
                } else {
                    typingElement.innerHTML += formattedText[index];
                    index++;
                }
                setTimeout(typeChar, speed);
            } else {
                // 타이핑 완료 후 빠른 질문 버튼 표시
                showQuickQuestions();
                // 완료 콜백 실행
                if (onComplete) {
                    onComplete();
                }
            }
        }
        
        typeChar();
    }
    
    // 코스 업데이트 함수 (전역으로 노출)
    window.updateCourseDisplay = async function(updatedCourse) {
        if (!updatedCourse || !window.map) {
            console.log('지도가 아직 초기화되지 않았거나 코스 데이터가 없습니다.');
            return;
        }
        
        try {
            console.log('코스 업데이트 시작:', updatedCourse);
            
            // 기존 마커와 카드 제거
            clearMapAndCards();
            
            // Google Maps 라이브러리 로드
            const { AdvancedMarkerElement, PinElement } = await google.maps.importLibrary("marker");
            
            // 업데이트된 코스 데이터로 직접 처리
            const places = updatedCourse.places || [];
            const sequence = updatedCourse.sequence || [];
            const location = updatedCourse.location || "";
            const weather_info = updatedCourse.weather_info || {};
            
            // sequence 순서대로 places 재배열
            const orderedPlaces = [];
            if (sequence.length > 0) {
                for (const idx of sequence) {
                    if (idx < places.length) {
                        const place = { ...places[idx] };
                        // 날씨 정보 추가
                        if (weather_info[idx] !== undefined) {
                            place.weather_info = weather_info[idx];
                        }
                        orderedPlaces.push(place);
                    }
                }
            } else {
                places.forEach((place, idx) => {
                    const placeWithWeather = { ...place };
                    if (weather_info[idx] !== undefined) {
                        placeWithWeather.weather_info = weather_info[idx];
                    }
                    orderedPlaces.push(placeWithWeather);
                });
            }
            
            console.log('정렬된 장소:', orderedPlaces);
            
            // 장소 순회 및 지오코딩
            const geocodePromises = orderedPlaces.map(async (place) => {
                try {
                    let addressToUse = place.address;
                    if (!addressToUse || addressToUse === "주소 정보 확인 필요" || addressToUse.trim() === "") {
                        const isValidLocation = location && location !== "location" && location.trim() !== "";
                        addressToUse = isValidLocation ? `${location} ${place.name}` : place.name;
                    }
                    
                    // 좌표가 이미 있으면 사용, 없으면 지오코딩
                    let coords = null;
                    if (place.coordinates && place.coordinates.lat && place.coordinates.lng) {
                        coords = new google.maps.LatLng(place.coordinates.lat, place.coordinates.lng);
                    } else if (typeof window.geocodeAddress === 'function') {
                        coords = await window.geocodeAddress(addressToUse);
                    } else if (window.geocoder) {
                        // geocodeAddress가 없으면 직접 geocoder 사용
                        coords = await new Promise((resolve, reject) => {
                            window.geocoder.geocode({ address: addressToUse }, (results, status) => {
                                if (status === "OK") {
                                    resolve(results[0].geometry.location);
                                } else {
                                    reject(new Error(`Geocoding 실패: ${status}`));
                                }
                            });
                        });
                    } else {
                        console.error('geocodeAddress 함수와 geocoder를 찾을 수 없습니다.');
                        return null;
                    }
                    
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
                            map: window.map,
                            position: coords,
                            title: place.name,
                            content: markerContainer,
                        });
                        
                        // 마커 추적 배열에 추가
                        if (!window.markers) window.markers = [];
                        window.markers.push(marker);

                        // 카드 생성
                        if (typeof window.createEnhancedCard === 'function') {
                            window.createEnhancedCard(place, "card-matrix");
                            window.createEnhancedCard(place, "side-menu", "menu-item");
                        } else {
                            console.error('createEnhancedCard 함수를 찾을 수 없습니다.');
                        }

                        return coords;
                    }
                } catch (error) {
                    console.warn(`${place.name} 처리 실패:`, error);
                }
                return null;
            });
            
            // 모든 마커 생성 완료 대기
            const results = await Promise.all(geocodePromises);
            const validCoords = results.filter(c => c !== null);
            const validPlaces = orderedPlaces.filter((place, idx) => results[idx] !== null);
            
            // 경로 그리기
            if (validCoords.length > 1 && typeof window.drawActualRoute === 'function') {
                const routePaths = await window.fetchRouteGuidePaths(window.TASK_ID);
                const travelMode = window.getTravelModeFromTransportation
                    ? window.getTravelModeFromTransportation(updatedCourse.transportation)
                    : google.maps.TravelMode.WALKING;
                const hasTransit = routePaths
                    ? routePaths.some(segment =>
                        (segment || []).some(step => (step.travel_mode || '').toUpperCase() === 'TRANSIT')
                    )
                    : false;
                
                if (travelMode === google.maps.TravelMode.TRANSIT || hasTransit) {
                    if (routePaths && routePaths.length > 0 && typeof window.drawRouteFromServerData === 'function') {
                        window.drawRouteFromServerData(routePaths);
                    }
                } else {
                    const drew = await window.drawActualRoute(validCoords, validPlaces, updatedCourse, {
                        travelMode,
                        allowStraightFallback: false
                    });
                    if (!drew && routePaths && routePaths.length > 0 && typeof window.drawRouteFromServerData === 'function') {
                        window.drawRouteFromServerData(routePaths);
                    }
                }
                
                // 화면 자동 맞춤
                const bounds = new google.maps.LatLngBounds();
                validCoords.forEach(c => bounds.extend(c));
                window.map.fitBounds(bounds);
            }
            
            console.log('코스 업데이트 완료');
            
            // 날씨 정보가 있으면 표시
            if (weather_info && Object.keys(weather_info).length > 0) {
                const firstWeatherKey = Object.keys(weather_info)[0];
                const weather = weather_info[firstWeatherKey];
                if (weather && weather.temperature !== null && weather.temperature !== undefined) {
                    // displayWeatherOnMap 함수가 script.js에 정의되어 있으므로 호출
                    if (typeof displayWeatherOnMap === 'function') {
                        displayWeatherOnMap(weather, updatedCourse.visit_date);
                    }
                }
            }
            
            // 챗봇에 업데이트 알림 메시지 추가
            appendMessage('bot', '✅ 코스가 업데이트되었습니다! 지도와 장소 목록을 확인해보세요. 🗺️', true);
        } catch (error) {
            console.error('코스 업데이트 중 오류:', error);
            appendMessage('bot', `⚠️ 코스 업데이트 중 오류가 발생했습니다: ${error.message}`, true);
        }
    };
    
    function clearMapAndCards() {
        // 모든 마커 제거
        if (window.markers && window.markers.length > 0) {
            window.markers.forEach(marker => {
                if (marker && marker.map) {
                    marker.map = null;
                }
            });
            window.markers = [];
        }
        
        // 카드 매트릭스와 사이드 메뉴 비우기
        const cardMatrix = document.getElementById('card-matrix');
        const sideMenu = document.getElementById('side-menu');
        if (cardMatrix) cardMatrix.innerHTML = '';
        if (sideMenu) sideMenu.innerHTML = '';
        
        // 경로 라인 제거
        if (window.polylines && window.polylines.length > 0) {
            window.polylines.forEach(polyline => {
                if (polyline && polyline.setMap) {
                    polyline.setMap(null);
                }
            });
            window.polylines = [];
        }
    }
    
    function showQuickQuestions() {
        // 기존 빠른 질문 버튼 제거
        const existing = document.getElementById('quick-questions');
        if (existing) existing.remove();
        
        // 빠른 질문 버튼 컨테이너 생성
        const quickDiv = document.createElement('div');
        quickDiv.id = 'quick-questions';
        quickDiv.style.cssText = 'margin-top: 12px; display: flex; flex-wrap: wrap; gap: 8px;';
        
        quickQuestions.forEach(question => {
            const btn = document.createElement('button');
            btn.textContent = question;
            btn.className = 'quick-question-btn';
            btn.style.cssText = `
                padding: 8px 12px;
                background: linear-gradient(135deg, rgba(197, 166, 131, 0.1), rgba(197, 166, 131, 0.05));
                border: 1px solid rgba(197, 166, 131, 0.3);
                border-radius: 20px;
                color: #C5A683;
                font-size: 0.85em;
                cursor: pointer;
                transition: all 0.2s ease;
                white-space: nowrap;
            `;
            btn.addEventListener('mouseenter', () => {
                btn.style.background = 'linear-gradient(135deg, rgba(197, 166, 131, 0.2), rgba(197, 166, 131, 0.1))';
                btn.style.transform = 'translateY(-2px)';
            });
            btn.addEventListener('mouseleave', () => {
                btn.style.background = 'linear-gradient(135deg, rgba(197, 166, 131, 0.1), rgba(197, 166, 131, 0.05))';
                btn.style.transform = 'translateY(0)';
            });
            btn.addEventListener('click', () => {
                sendMessage(question);
            });
            quickDiv.appendChild(btn);
        });
        
        chatWindow.appendChild(quickDiv);
        chatWindow.scrollTo({
            top: chatWindow.scrollHeight,
            behavior: 'smooth'
        });
    }
    
    function hideQuickQuestions() {
        const quickDiv = document.getElementById('quick-questions');
        if (quickDiv) quickDiv.remove();
    }

    function appendMessage(sender, text, skipTyping = false) {
        if (!skipTyping && sender === 'bot') {
            appendMessageWithTyping(sender, text);
            return;
        }
        
        const msgDiv = document.createElement('div');
        msgDiv.className = `message ${sender}-message`;
        msgDiv.style.cssText = 'opacity: 0; transform: translateY(10px); transition: all 0.3s ease;';
        
        // 줄바꿈을 <br>로 변환하고 HTML 허용
        const formattedText = text.replace(/\n/g, '<br>');
        
        // AI 메시지는 아이콘 추가
        if (sender === 'bot') {
            msgDiv.innerHTML = `
                <div style="display: flex; align-items: flex-start; gap: 8px;">
                    <div style="width: 24px; height: 24px; border-radius: 50%; background: linear-gradient(135deg, #C5A683, #a0855f); display: flex; align-items: center; justify-content: center; flex-shrink: 0; margin-top: 2px;">
                        <span style="color: white; font-size: 10px; font-weight: bold;">AI</span>
                    </div>
                    <div style="flex: 1;">
                        <span>${formattedText}</span>
                    </div>
                </div>
            `;
        } else {
            msgDiv.innerHTML = `<span>${formattedText}</span>`;
        }
        
        chatWindow.appendChild(msgDiv);
        
        // 애니메이션 적용
        setTimeout(() => {
            msgDiv.style.opacity = '1';
            msgDiv.style.transform = 'translateY(0)';
        }, 10);
        
        // 부드러운 스크롤
        chatWindow.scrollTo({
            top: chatWindow.scrollHeight,
            behavior: 'smooth'
        });
    }
    
    // 전역으로 appendMessage 함수 노출 (script.js에서 사용)
    window.appendMessage = appendMessage;

    // 버튼 클릭 및 엔터 키 이벤트
    sendBtn.addEventListener('click', sendMessage);
    chatInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') sendMessage();
    });
    
    // 페이지 로드 시 코스 정보 표시
    loadCourseInfo();
});