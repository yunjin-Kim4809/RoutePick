document.addEventListener('DOMContentLoaded', () => {
    const chatInput = document.getElementById('chat-input');
    const chatWindow = document.getElementById('chat-window');
    const sendBtn = document.getElementById('send-btn');

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
        msgDiv.innerHTML = `<strong>${sender === 'user' ? '나' : 'AI'}:</strong> <span>${text}</span>`;
        chatWindow.appendChild(msgDiv);
        
        // 스크롤 하단 이동
        chatWindow.scrollTop = chatWindow.scrollHeight;
    }

    // 버튼 클릭 및 엔터 키 이벤트
    sendBtn.addEventListener('click', sendMessage);
    chatInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') sendMessage();
    });
});