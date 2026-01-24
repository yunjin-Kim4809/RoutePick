document.addEventListener('DOMContentLoaded', () => {
    const chatInput = document.getElementById('chat-input');
    const chatWindow = document.getElementById('chat-window');
    const sendBtn = document.getElementById('send-btn');

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
                // 코스 설명 표시
                if (data.course_description) {
                    appendMessage('bot', `<div style="margin-bottom: 12px;"><strong style="font-size: 1.15em; color: #C5A683; display: block; margin-bottom: 8px;">📝 코스 설명</strong></div>${data.course_description}`);
                }
                
                // 방문 순서 표시
                const sequence = data.sequence || [];
                const places = data.places || [];
                const estimated_duration = data.estimated_duration || {};
                
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
                            courseMessage += `<div style="margin-bottom: 6px;">📍 <span style="color: #888; font-weight: 500;">주소:</span> <span style="color: #1a1a1a;">${place.address || '주소 정보 없음'}</span></div>`;
                            if (place.map_url) {
                                courseMessage += `<div><a href="${place.map_url}" target="_blank" style="color: #C5A683; text-decoration: none; font-weight: 600; border-bottom: 1px solid #C5A683; padding-bottom: 1px; transition: color 0.2s;">🔗 지도 보기</a></div>`;
                            }
                            courseMessage += `</div></div>`;
                        }
                    });
                    
                    appendMessage('bot', courseMessage);
                }
                
                // 선정 이유 표시
                if (data.reasoning) {
                    appendMessage('bot', `<div style="margin-bottom: 12px;"><strong style="font-size: 1.15em; color: #C5A683; display: block; margin-bottom: 8px;">💡 선정 이유</strong></div>${data.reasoning}`);
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
            const taskId = window.TASK_ID;
            if (!taskId) {
                appendMessage('bot', '오류: task_id가 없습니다.');
                return;
            }
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: message, taskId: taskId })
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