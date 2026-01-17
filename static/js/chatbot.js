document.addEventListener('DOMContentLoaded', () => {
    const chatInput = document.getElementById('chat-input');
    const chatWindow = document.getElementById('chat-window');
    const sendBtn = document.getElementById('send-btn');

    // 초기 코스 정보 로드 및 표시
    async function loadCourseInfo() {
        try {
            const response = await fetch('/api/locations');
            const data = await response.json();
            
            if (data && data.places && data.places.length > 0) {
                // 코스 설명 표시
                if (data.course_description) {
                    appendMessage('bot', `📝 <strong>코스 설명</strong>\n\n${data.course_description}`);
                }
                
                // 방문 순서 표시
                const sequence = data.sequence || [];
                const places = data.places || [];
                const estimated_duration = data.estimated_duration || {};
                
                if (sequence.length > 0 && places.length > 0) {
                    let courseMessage = '📍 <strong>방문 순서</strong>\n\n';
                    
                    sequence.forEach((placeIdx, idx) => {
                        if (placeIdx < places.length) {
                            const place = places[placeIdx];
                            const duration = estimated_duration[placeIdx] || estimated_duration[String(placeIdx)] || '정보 없음';
                            
                            courseMessage += `${idx + 1}. <strong>${place.name || '알 수 없음'}</strong>\n`;
                            courseMessage += `   📌 카테고리: ${place.category || 'N/A'}\n`;
                            courseMessage += `   ⏱ 체류 시간: ${duration}분\n`;
                            courseMessage += `   ⭐ 평점: ${place.rating || 'N/A'}\n`;
                            courseMessage += `   📍 주소: ${place.address || '주소 정보 없음'}\n`;
                            
                            if (place.map_url) {
                                courseMessage += `   🔗 <a href="${place.map_url}" target="_blank">지도 보기</a>\n`;
                            }
                            courseMessage += '\n';
                        }
                    });
                    
                    appendMessage('bot', courseMessage);
                }
                
                // 선정 이유 표시
                if (data.reasoning) {
                    appendMessage('bot', `💡 <strong>선정 이유</strong>\n\n${data.reasoning}`);
                }
            }
        } catch (error) {
            console.error('코스 정보 로드 실패:', error);
        }
    }

    async function sendMessage() {
        const message = chatInput.value.trim();
        if (!message) return;

        // 유저 메시지 화면에 추가
        appendMessage('user', message);
        chatInput.value = '';

        try {
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: message })
            });
            const data = await response.json();
            
            // 봇 메시지 화면에 추가
            appendMessage('bot', data.response);
        } catch (error) {
            appendMessage('bot', '오류가 발생했습니다. 다시 시도해주세요.');
        }
    }

    function appendMessage(sender, text) {
        const msgDiv = document.createElement('div');
        msgDiv.className = `message ${sender}-message`;
        // 줄바꿈을 <br>로 변환하고 HTML 허용
        const formattedText = text.replace(/\n/g, '<br>');
        msgDiv.innerHTML = `<strong>${sender === 'user' ? '나' : 'AI'}:</strong> <span>${formattedText}</span>`;
        chatWindow.appendChild(msgDiv);
        
        // 스크롤 하단 이동
        chatWindow.scrollTop = chatWindow.scrollHeight;
    }

    // 버튼 클릭 및 엔터 키 이벤트
    sendBtn.addEventListener('click', sendMessage);
    chatInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') sendMessage();
    });
    
    // 페이지 로드 시 코스 정보 표시
    loadCourseInfo();
});