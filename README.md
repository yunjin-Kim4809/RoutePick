# RoutePick 🗺️

실시간 웹 검색과 지도 API를 결합하여 사용자의 니즈에 최적화된 여행/데이트 코스를 설계하는 멀티 에이전트 시스템입니다.

## 📋 목차

- [주요 기능](#주요-기능)
- [시스템 아키텍처](#시스템-아키텍처)
- [기술 스택](#기술-스택)
- [설치 및 실행](#설치-및-실행)
- [환경 변수 설정](#환경-변수-설정)
- [사용 방법](#사용-방법)
- [프로젝트 구조](#프로젝트-구조)
- [API 문서](#api-문서)
- [개발 가이드](#개발-가이드)
- [문제 해결](#문제-해결)

---

## ✨ 주요 기능

### 1. **스마트 장소 검색**
- Tavily API를 통한 실시간 웹 검색
- LLM 기반 장소 정보 추출 및 검증
- 신뢰도 점수 기반 필터링

### 2. **맞춤형 코스 제작**
- 사용자 선호도 기반 최적 코스 생성
- 날씨 정보를 고려한 실내/야외 장소 선택
- 예산 제약 조건 고려
- 식당/카페 연속 방문 방지

### 3. **지능형 경로 최적화**
- **한국 내**: T Map API 우선 사용 (도보/자동차)
- **대중교통 또는 한국 외**: Google Maps API 사용
- 경유지 순서 자동 최적화
- 실시간 이동 시간 및 거리 계산

### 4. **대화형 챗봇**
- 코스 수정 및 질의응답
- 실시간 코스 업데이트

### 5. **인터랙티브 지도**
- Google Maps 기반 지도 표시
- 마커에 가게 이름 라벨 표시
- 상세 경로 시각화
- 날씨 정보 표시

---

## 🏗️ 시스템 아키텍처

RoutePick은 **멀티 에이전트 아키텍처**를 기반으로 합니다:

```
사용자 입력
    ↓
SearchAgent (장소 검색)
    ↓
PlanningAgent (코스 제작)
    ↓
RoutingAgent (경로 최적화)
    ↓
최종 코스 결과
```

자세한 아키텍처 정보는 [ARCHITECTURE.md](./ARCHITECTURE.md)를 참고하세요.

---

## 🛠️ 기술 스택

### 백엔드
- **Python 3.8+**
- **Flask**: 웹 프레임워크
- **LangChain**: LLM 에이전트 프레임워크
- **OpenAI API**: GPT 모델
- **asyncio**: 비동기 처리
- **aiohttp**: 비동기 HTTP 클라이언트

### 프론트엔드
- **React 18+** with TypeScript
- **Vite**: 빌드 도구
- **Google Maps JavaScript API**: 지도 렌더링

### 외부 API
- **Tavily API**: 실시간 웹 검색
- **Google Maps API**: 경로 계산, 지오코딩
- **T Map API**: 한국 내 도보/자동차 경로 안내
- **OpenAI API**: LLM 기반 코스 제작
- **OpenWeather API**: 날씨 정보 조회

---

## 🚀 설치 및 실행

### 사전 요구사항

- Python 3.8 이상
- Node.js 16 이상
- npm 또는 yarn

### 1. 저장소 클론

```bash
git clone <repository-url>
cd RoutePick
```

### 2. 백엔드 설정

```bash
cd RoutePick_Backend

# 가상 환경 생성 (선택사항)
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt
```

### 3. 프론트엔드 설정

```bash
cd RoutePick_Frontend

# 의존성 설치
npm install
# 또는
yarn install
```

### 4. 환경 변수 설정

프로젝트 루트에 `.env` 파일을 생성하고 필요한 API 키를 설정하세요:

```env
# 필수 API 키
TAVILY_API_KEY=your_tavily_api_key
GOOGLE_MAPS_API_KEY=your_google_maps_api_key
OPENAI_API_KEY=your_openai_api_key
T_MAP_API_KEY=your_tmap_api_key
OPENWEATHER_API_KEY=your_openweather_api_key

# 선택사항
LLM_MODEL=gpt-4o-mini
```

### 5. 실행

#### 백엔드 실행

```bash
cd RoutePick_Backend
python app.py
```

백엔드는 기본적으로 `http://localhost:5000`에서 실행됩니다.

#### 프론트엔드 실행

```bash
cd RoutePick_Frontend
npm run dev
# 또는
yarn dev
```

프론트엔드는 기본적으로 `http://localhost:5173`에서 실행됩니다.

---

## ⚙️ 환경 변수 설정

### 필수 API 키

| 변수명 | 설명 | 발급 위치 |
|--------|------|-----------|
| `TAVILY_API_KEY` | Tavily 검색 API 키 | [Tavily](https://tavily.com) |
| `GOOGLE_MAPS_API_KEY` | Google Maps API 키 | [Google Cloud Console](https://console.cloud.google.com) |
| `OPENAI_API_KEY` | OpenAI API 키 | [OpenAI Platform](https://platform.openai.com) |
| `T_MAP_API_KEY` | T Map API 키 | [T Map Open API](https://openapi.sk.com) |
| `OPENWEATHER_API_KEY` | OpenWeather API 키 | [OpenWeather](https://openweathermap.org) |

---

## 📖 사용 방법

### 1. 웹 인터페이스 사용

1. 브라우저 접속
2. 여행 계획 입력:
   - 테마 (예: "비 오는 날 서울 실내 데이트")
   - 지역 (예: "서울")
   - 방문 날짜
   - 방문 시간
   - 교통수단 (도보, 지하철, 버스, 자동차)
   - 인원 수
   - 예산 (선택사항)
3. "여행 만들기" 버튼 클릭
4. 코스 생성 완료 후 지도에서 확인
5. 챗봇을 통해 코스 수정 가능

### 2. API 사용 예시

#### 코스 생성

```python
import requests

response = requests.post('http://localhost:5000/api/create-trip', json={
    "theme": "비 오는 날 서울 실내 데이트",
    "location": "서울",
    "startDate": "2025-02-15",
    "endDate": "2025-02-15",
    "visitTime": "오후",
    "transportation": ["도보", "지하철"],
    "groupSize": "2명",
    "budget": "50000"
})

task_id = response.json()["taskId"]
```

#### 장소 정보 조회

```python
response = requests.get(f'http://localhost:5000/api/locations/{task_id}')
data = response.json()

places = data["places"]
sequence = data["sequence"]
```

#### 경로 안내 조회

```python
response = requests.post(
    f'http://localhost:5000/api/route-guide/{task_id}',
    json={
        "transportation": "도보, 지하철",
        "departureTime": "2025-02-15T14:00:00"
    }
)

route_data = response.json()
guide = route_data["guide"]
route_paths = route_data["route_paths"]
```

---

## 📁 프로젝트 구조

```
RoutePick/
├── RoutePick_Backend/          # Flask 백엔드
│   ├── agents/                 # 에이전트 클래스
│   │   ├── base_agent.py
│   │   ├── search_agent.py     # 장소 검색 에이전트
│   │   ├── planning_agent.py   # 코스 제작 에이전트
│   │   └── routing_agent.py    # 경로 최적화 에이전트
│   ├── tools/                  # 도구 클래스
│   │   ├── base_tool.py
│   │   ├── tavily_search_tool.py
│   │   ├── google_maps_tool.py
│   │   ├── tmap_tool.py        # T Map API 도구
│   │   └── course_creation_tool.py
│   ├── config/                 # 설정 파일
│   │   └── config.py
│   ├── static/                 # 정적 파일
│   │   ├── js/                 # JavaScript 파일
│   │   ├── css/                # 스타일시트
│   │   └── images/             # 이미지
│   ├── templates/              # HTML 템플릿
│   ├── app.py                  # Flask 애플리케이션
│   ├── chatbot.py              # 챗봇 로직
│   └── requirements.txt        # Python 의존성
│
├── RoutePick_Frontend/         # React 프론트엔드
│   ├── components/             # React 컴포넌트
│   │   ├── TripPlanner.tsx
│   │   ├── PlaceSearchModal.tsx
│   │   └── ...
│   ├── App.tsx
│   ├── index.tsx
│   ├── package.json
│   └── vite.config.ts
│
├── .env                        # 환경 변수 (생성 필요)
├── .md                   # 이 파일
└── ARCHITECTURE.md             # 아키텍처 문서
```

---

## 📡 API 문서

### POST /api/create-trip

여행 코스를 생성합니다.

**Request:**
```json
{
  "theme": "비 오는 날 서울 실내 데이트",
  "location": "서울",
  "startDate": "2025-02-15",
  "endDate": "2025-02-15",
  "visitTime": "오후",
  "transportation": ["도보", "지하철"],
  "groupSize": "2명",
  "budget": "50000"
}
```

**Response:**
```json
{
  "taskId": "uuid-string",
  "status": "processing"
}
```

### GET /api/locations/<task_id>

생성된 코스의 장소 정보를 조회합니다.

**Response:**
```json
{
  "places": [...],
  "sequence": [0, 2, 5, ...],
  "transportation": "도보, 지하철",
  "visit_date": "2025-02-15",
  "weather_info": {...}
}
```

### POST /api/route-guide/<task_id>

상세 경로 안내를 조회합니다.

**Request:**
```json
{
  "transportation": "도보, 지하철",
  "departureTime": "2025-02-15T14:00:00"
}
```

**Response:**
```json
{
  "guide": ["경로 안내 텍스트 배열"],
  "route_paths": [...]
}
```

### POST /api/chat

챗봇과 대화합니다.

**Request:**
```json
{
  "message": "첫 번째 장소는 뭐야?",
  "task_id": "uuid-string"
}
```

**Response:**
```json
{
  "response": "첫 번째 장소는..."
}
```

---

## 📝 라이선스

이 프로젝트는 MIT 라이선스를 따릅니다.

---

## 📚 추가 문서

- [ARCHITECTURE.md](./ARCHITECTURE.md): 상세한 아키텍처 문서

---


이 프로젝트는 다음 오픈소스 및 API를 사용합니다:
- [Tavily](https://tavily.com) - 실시간 웹 검색
- [Google Maps Platform](https://developers.google.com/maps) - 지도 및 경로 서비스
- [T Map Open API](https://openapi.sk.com) - 한국 내 경로 안내
- [OpenAI](https://openai.com) - LLM 서비스
- [OpenWeather](https://openweathermap.org) - 날씨 정보


