# RoutePick 아키텍처 문서

## 목차

1. [시스템 개요](#시스템-개요)
2. [전체 아키텍처](#전체-아키텍처)
3. [주요 컴포넌트](#주요-컴포넌트)
4. [에이전트 시스템](#에이전트-시스템)
5. [도구(Tool) 시스템](#도구tool-시스템)
6. [데이터 흐름](#데이터-흐름)
7. [API 구조](#api-구조)
8. [프론트엔드 구조](#프론트엔드-구조)
9. [기술 스택](#기술-스택)
10. [성능 최적화](#성능-최적화)
11. [확장성 고려사항](#확장성-고려사항)

---

## 시스템 개요

RoutePick은 **멀티 에이전트 아키텍처**를 기반으로 한 여행 코스 설계 시스템입니다. 실시간 웹 검색, LLM 기반 코스 제작, 지도 API를 통한 경로 최적화를 통합하여 사용자 맞춤형 여행 계획을 제공합니다.

### 핵심 가치

- **지능형 검색**: Tavily API를 통한 실시간 웹 검색으로 최신 장소 정보 확보
- **맞춤형 코스**: LLM이 사용자 선호도, 날씨, 예산을 고려하여 최적 코스 생성
- **스마트 라우팅**: T Map API(한국 내)와 Google Maps API를 선택적으로 사용
- **실시간 상호작용**: 대화형 챗봇을 통한 코스 수정 및 질의응답

---

## 전체 아키텍처

### 시스템 레이어 구조

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Presentation Layer                           │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │              React Frontend (TypeScript)                     │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │   │
│  │  │ TripPlanner  │  │  Chatbot UI  │  │   Map View   │      │   │
│  │  │  Component   │  │  Component   │  │  (Google Maps)│      │   │
│  │  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘      │   │
│  └─────────┼──────────────────┼──────────────────┼──────────────┘   │
└────────────┼──────────────────┼──────────────────┼──────────────────┘
             │                  │                  │
             │ HTTP/REST API    │ WebSocket/SSE    │ Google Maps JS API
             │                  │                  │
┌────────────▼──────────────────▼──────────────────▼───────────────────┐
│                        Application Layer                             │
│  ┌──────────────────────────────────────────────────────────────┐    │
│  │                    Flask Backend (Python)                    │    │
│  │  ┌────────────────────────────────────────────────────────┐  │    │
│  │  │              API Routes (app.py)                       │  │    │
│  │  │  /api/create-trip  /api/locations/<id>  /api/chat      │  │    │
│  │  │  /api/route-guide/<id>  /status/<id>                   │  │    │
│  │  └──────────────────────┬─────────────────────────────────┘   │    │
│  │                         │                                         │    │
│  │  ┌──────────────────────▼───────────────────────────────────┐   │    │
│  │  │          Agent Execution Pipeline                         │   │    │
│  │  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │   │    │
│  │  │  │Search Agent  │→ │Planning Agent│→ │Routing Agent │   │   │    │
│  │  │  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘   │   │    │
│  │  └─────────┼──────────────────┼──────────────────┼───────────┘   │    │
│  └────────────┼──────────────────┼──────────────────┼─────────────┘  │
└───────────────┼──────────────────┼──────────────────┼────────────────┘
                │                  │                  │
┌───────────────▼──────────────────▼──────────────────▼────────────────┐
│                        Service Layer                                 │
│  ┌──────────────────────────────────────────────────────────────┐    │
│  │                    Tools Layer                               │    │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │    │
│  │  │TavilySearch  │  │CourseCreation│  │GoogleMaps   │       │    │
│  │  │    Tool      │  │    Tool      │  │   Tool      │       │    │
│  │  └──────────────┘  └──────────────┘  └──────────────┘       │    │
│  │  ┌──────────────┐                                            │    │
│  │  │   TMapTool   │                                            │    │
│  │  └──────────────┘                                            │    │
│  └──────────────┬───────────────────────────────────────────────┘    │
└─────────────────┼────────────────────────────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────────────────────────────┐
│                        External Services                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                  │
│  │ Tavily API   │  │Google Maps   │  │  T Map API   │                  │
│  │              │  │    API       │  │              │                  │
│  └──────────────┘  └──────────────┘  └──────────────┘                  │
│  ┌──────────────┐  ┌──────────────┐                                     │
│  │  OpenAI API  │  │OpenWeather   │                                     │
│  │              │  │    API       │                                     │
│  └──────────────┘  └──────────────┘                                     │
└──────────────────────────────────────────────────────────────────────────┘
```

### 컴포넌트 간 상호작용

```
┌─────────────┐
│   사용자     │
└──────┬──────┘
       │
       │ 1. 여행 계획 입력
       ↓
┌─────────────────────────────────────┐
│      Flask Backend (app.py)         │
│  - POST /api/create-trip            │
│  - task_id 생성 및 비동기 실행        │
└──────────────┬──────────────────────┘
               │
               │ 2. execute_Agents() 호출
               ↓
┌──────────────────────────────────────┐
│      Agent Execution Pipeline         │
│                                       │
│  ┌────────────────────────────────┐  │
│  │ Step 1: SearchAgent            │  │
│  │ - TavilySearchTool 실행        │  │
│  │ - LLM으로 장소 정보 추출       │  │
│  │ - 신뢰도 점수 계산             │  │
│  │ 출력: candidate_pool            │  │
│  └──────────────┬──────────────────┘  │
│                 │                     │
│  ┌──────────────▼───────────────────┐  │
│  │ Step 2: PlanningAgent           │  │
│  │ - CourseCreationTool 실행       │  │
│  │ - LLM이 최적 코스 생성          │  │
│  │ - check_routing으로 경로 검증   │  │
│  │ 출력: course (장소 + 순서)      │  │
│  └──────────────┬───────────────────┘  │
│                 │                     │
│  ┌──────────────▼───────────────────┐  │
│  │ Step 3: RoutingAgent (선택적)   │  │
│  │ - 실제 이동 시간/거리 계산       │  │
│  │ - 경로 최적화                    │  │
│  │ 출력: directions                 │  │
│  └──────────────────────────────────┘  │
└───────────────────────────────────────┘
               │
               │ 3. 결과 저장 (agent_tasks)
               ↓
┌──────────────────────────────────────┐
│      프론트엔드 폴링                  │
│  - GET /api/locations/<task_id>      │
│  - GET /status/<task_id>              │
└──────────────────────────────────────┘
```

---

## 주요 컴포넌트

### 1. 프론트엔드 (RoutePick_Frontend)

#### 기술 스택
- **React 19+** with TypeScript
- **Vite 6+** (빌드 도구)
- **Google Maps JavaScript API** (지도 렌더링)
- **Lucide React** (아이콘)

#### 주요 컴포넌트

##### TripPlanner.tsx
- 여행 계획 입력 폼
- 테마, 지역, 날짜, 시간, 교통수단, 인원, 예산 입력
- PlaceSearchModal 통합
- 코스 생성 요청 및 상태 관리

##### PlaceSearchModal.tsx
- 장소 검색 및 선택 모달
- 저장된 장소 표시

##### 기타 컴포넌트
- **Hero.tsx**: 랜딩 페이지 메인 섹션
- **Navbar.tsx**: 네비게이션 바
- **Features.tsx**: 기능 소개
- **Gallery.tsx**: 갤러리
- **Philosophy.tsx**: 서비스 철학
- **Cta.tsx**: Call-to-Action
- **Footer.tsx**: 푸터

#### 정적 파일 (Backend/static)

##### script.js
- Google Maps 지도 초기화
- 마커 생성 및 표시 (가게 이름 라벨 포함)
- 경로 그리기 (Polyline)
- 지오코딩 (주소 → 좌표 변환)
- 경로 안내 시각화

##### chatbot.js
- 챗봇 UI 렌더링
- 코스 정보 표시
- 사용자 메시지 전송 및 응답 표시
- 코스 업데이트 처리

##### style.css
- 전역 스타일링
- 반응형 디자인

### 2. 백엔드 (RoutePick_Backend)

#### Flask 애플리케이션 (app.py)

##### 핵심 기능
- **비동기 작업 처리**: `execute_Agents()` 함수를 별도 스레드에서 실행
- **작업 상태 관리**: `agent_tasks` 딕셔너리로 task_id별 상태 추적
- **CORS 지원**: Flask-CORS로 프론트엔드와 통신

##### 주요 엔드포인트

```python
POST /api/create-trip          # 여행 코스 생성 요청
GET  /api/locations/<task_id>  # 생성된 코스의 장소 정보 조회
POST /api/route-guide/<task_id> # 상세 경로 안내 조회
POST /api/chat                 # 챗봇 대화 처리
GET  /status/<task_id>         # 작업 상태 조회
GET  /chat-map/<task_id>       # 챗봇 페이지 렌더링
```

##### 실행 플로우

```python
# 1. 사용자 요청 수신
POST /api/create-trip
    ↓
# 2. task_id 생성 및 초기 상태 설정
agent_tasks[task_id] = {...}
    ↓
# 3. 별도 스레드에서 비동기 실행
threading.Thread(target=run_agent_task_with_id, ...)
    ↓
# 4. Agent 파이프라인 실행
execute_Agents(task_id, input_data)
    ↓
# 5. 결과 저장
agent_tasks[task_id]["course"] = course_result
agent_tasks[task_id]["success"] = True
```

#### 챗봇 시스템 (chatbot.py)

##### 기능
- OpenAI API를 사용한 대화형 챗봇
- 코스 정보를 컨텍스트로 포함
- 코스 수정 요청 파싱 및 처리
- task_id별 채팅 히스토리 관리

---

## 에이전트 시스템

### BaseAgent (agents/base_agent.py)

모든 에이전트의 기본 클래스로 공통 인터페이스를 제공합니다.

```python
class BaseAgent(ABC):
    @abstractmethod
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]
    
    @abstractmethod
    def validate_input(self, input_data: Dict[str, Any]) -> bool
```

### 1. SearchAgent (agents/search_agent.py)

#### 역할
테마와 지역을 기반으로 장소 후보군을 검색하고 필터링합니다.

#### 실행 플로우

```
입력: {theme, location}
    ↓
1. 전략 수립 (LLM)
   - 테마 분석
   - 검색 쿼리 생성
    ↓
2. Tavily 멀티 검색
   - 병렬 검색 실행
   - 최대 15개 결과 수집
    ↓
3. LLM 엔티티 추출
   - 장소명 추출
   - 카테고리 분류
    ↓
4. Google Maps 검증
   - 지오코딩
   - 평점/리뷰 확인
    ↓
5. 신뢰도 점수 계산
   - 평점, 리뷰 수, 최신성 고려
    ↓
출력: {candidate_pool: List[Place]}
```

#### 주요 메서드
- `execute()`: 검색 파이프라인 실행
- `_generate_strategy()`: LLM으로 검색 전략 수립
- `_extract_places_from_search()`: 검색 결과에서 장소 추출
- `_verify_with_google_maps()`: Google Maps로 장소 검증
- `select_best_20_candidates()`: 신뢰도 기반 상위 20개 선정

### 2. PlanningAgent (agents/planning_agent.py)

#### 역할
검색된 장소 후보군 중에서 사용자 선호도에 맞는 최적의 코스를 생성합니다.

#### 실행 플로우

```
입력: {places, user_preferences, time_constraints}
    ↓
1. CourseCreationTool 실행
   - LLM AgentExecutor 사용
   - check_routing 도구 활용
    ↓
2. LLM 코스 생성
   - 저장된 장소 우선 포함
   - 테마에 맞는 장소 선정
   - 거리 최소화 순서 배열
   - 경로 검증
    ↓
3. 결과 파싱
   - JSON 형식 검증
   - 인덱스 유효성 확인
    ↓
출력: {course: {places, sequence, estimated_duration}}
```

#### 주요 메서드
- `execute()`: 코스 제작 파이프라인 실행
- `validate_input()`: 입력 데이터 검증

### 3. RoutingAgent (agents/routing_agent.py)

#### 역할
선정된 코스의 실제 이동 시간과 거리를 계산하고 경로를 최적화합니다.

#### API 선택 로직

```python
if mode in ["walking", "driving"] and not has_transit:
    if is_in_korea(places):
        use_tmap = True  # T Map API 사용
    else:
        use_tmap = False  # Google Maps API 사용
else:
    use_tmap = False  # 대중교통은 Google Maps만 지원
```

#### 실행 플로우

```
입력: {places, mode, optimize_waypoints}
    ↓
1. API 선택
   - 한국 내 + 도보/자동차 → T Map API
   - 대중교통 또는 한국 외 → Google Maps API
    ↓
2. 경로 계산
   - 각 구간별 경로 계산
   - 경유지 최적화 (선택적)
    ↓
3. 결과 집계
   - 총 이동 시간
   - 총 거리
   - 상세 경로 정보
    ↓
출력: {directions, total_duration, total_distance}
```

#### 주요 메서드
- `execute()`: 경로 최적화 실행
- `_is_in_korea()`: 한국 영역 내 여부 확인
- `cluster_places()`: DBSCAN 기반 장소 군집화

---

## 도구(Tool) 시스템

### BaseTool (tools/base_tool.py)

모든 도구의 기본 클래스로 공통 인터페이스를 제공합니다.

```python
class BaseTool(ABC):
    @abstractmethod
    async def execute(self, **kwargs) -> Dict[str, Any]
    
    @abstractmethod
    def get_schema(self) -> Dict[str, Any]
```

### 1. TavilySearchTool (tools/tavily_search_tool.py)

#### 역할
Tavily API를 통한 실시간 웹 검색을 수행합니다.

#### 주요 기능
- 검색 쿼리 실행
- 검색 결과 파싱
- 최대 결과 수 제한

### 2. GoogleMapsTool (tools/google_maps_tool.py)

#### 역할
Google Maps API를 사용하여 경로 계산, 지오코딩, 날씨 정보 조회를 수행합니다.

#### 주요 기능

##### 경로 계산
- 도보, 자동차, 대중교통 경로 계산
- 경유지 순서 최적화 (Waypoint Optimization)
- 여러 구간 병렬 처리

##### 지오코딩
- 주소 → 좌표 변환
- 장소명 → 좌표 변환

##### 날씨 정보 조회
- OpenWeather API 통합
- 현재 날씨 및 예보 조회
- 사용자 설정 날짜에 맞는 날씨 정보 제공

#### 최적화 알고리즘

##### Waypoint Optimization
- **대중교통**: Google Maps Directions API의 `optimize:true` 옵션 사용
- **도보/자동차**: Master List 방식으로 경유지 순서 최적화

### 3. TMapTool (tools/tmap_tool.py)

#### 역할
T Map API를 사용하여 한국 내 도보 및 자동차 경로 안내를 제공합니다.

#### 주요 기능

##### 보행자 경로 안내
- 엔드포인트: `POST /tmap/routes/pedestrian`
- GeoJSON 응답 파싱
- 상세 경로 좌표 추출

##### 자동차 경로 안내
- 엔드포인트: `POST /tmap/routes`
- 요금 정보 포함
- 교통 정보 지원

#### 좌표 변환
- T Map API: `[lng, lat]` 형식
- Google Maps: `[lat, lng]` 형식
- 내부적으로 변환 처리

#### 에러 처리
- API 키 문제 감지
- 서비스 제공 지역 확인
- 실패 시 Google Maps로 폴백

### 4. CourseCreationTool (tools/course_creation_tool.py)

#### 역할
LLM을 사용하여 맞춤형 코스를 생성합니다.

#### 주요 기능

##### LLM AgentExecutor
- LangChain 기반 에이전트
- `check_routing` 도구를 내부적으로 사용
- 최대 10회 반복 제한

##### 코스 생성 로직
1. 저장된 장소 우선 포함
2. 테마에 맞는 추가 장소 선정
3. 식당/카페 연속 방문 방지
4. 거리 최소화 순서 배열
5. 경로 검증 (check_routing)

##### 캐싱 메커니즘
- `check_routing` 결과 캐시
- 동일한 장소 조합에 대한 중복 호출 방지
- 최대 100개 캐시 유지 (FIFO)

##### 사전 필터링
- 두 지점이 10m 이내인 경우 API 호출 생략
- 직접 경로 반환

---

## 데이터 흐름

### 1. 코스 생성 전체 플로우

```
┌─────────────────────────────────────────────────────────────┐
│ 사용자 입력                                                  │
│ - theme: "비 오는 날 서울 실내 데이트"                      │
│ - location: "서울"                                          │
│ - visit_date: "2025-02-15"                                  │
│ - transportation: ["도보", "지하철"]                        │
└──────────────────┬──────────────────────────────────────────┘
                   │
                   ↓
┌─────────────────────────────────────────────────────────────┐
│ POST /api/create-trip                                       │
│ - task_id 생성 (UUID)                                       │
│ - agent_tasks[task_id] 초기화                               │
│ - 별도 스레드에서 execute_Agents() 실행                    │
└──────────────────┬──────────────────────────────────────────┘
                   │
                   ↓
┌─────────────────────────────────────────────────────────────┐
│ Step 1: SearchAgent.execute()                              │
│                                                             │
│ 입력: {theme, location}                                    │
│   ↓                                                         │
│ 1. LLM 전략 수립                                            │
│    - 검색 쿼리 생성                                         │
│   ↓                                                         │
│ 2. Tavily 멀티 검색 (병렬)                                  │
│    - 각 쿼리별 최대 15개 결과                               │
│   ↓                                                         │
│ 3. LLM 엔티티 추출                                          │
│    - 장소명, 카테고리 추출                                  │
│   ↓                                                         │
│ 4. Google Maps 검증                                        │
│    - 지오코딩, 평점 확인                                    │
│   ↓                                                         │
│ 5. 신뢰도 점수 계산                                         │
│    - 평점, 리뷰 수, 최신성 고려                            │
│   ↓                                                         │
│ 출력: candidate_pool (최대 20개)                           │
└──────────────────┬──────────────────────────────────────────┘
                   │
                   ↓
┌─────────────────────────────────────────────────────────────┐
│ Step 2: PlanningAgent.execute()                            │
│                                                             │
│ 입력: {places, user_preferences, time_constraints}        │
│   ↓                                                         │
│ 1. 날씨 정보 조회 (선택적)                                  │
│    - visit_date 기반                                        │
│    - OpenWeather API                                        │
│   ↓                                                         │
│ 2. CourseCreationTool.execute()                            │
│    - LLM AgentExecutor 실행                                │
│    - check_routing으로 경로 검증                            │
│   ↓                                                         │
│ 3. 결과 파싱 및 검증                                        │
│    - JSON 형식 검증                                         │
│    - 인덱스 유효성 확인                                     │
│   ↓                                                         │
│ 출력: course {places, sequence, estimated_duration}        │
└──────────────────┬──────────────────────────────────────────┘
                   │
                   ↓
┌─────────────────────────────────────────────────────────────┐
│ Step 3: RoutingAgent.execute() (선택적)                    │
│                                                             │
│ 입력: {places, mode, optimize_waypoints}                  │
│   ↓                                                         │
│ 1. API 선택                                                 │
│    - 한국 내 + 도보/자동차 → T Map API                      │
│    - 대중교통 또는 한국 외 → Google Maps API               │
│   ↓                                                         │
│ 2. 경로 계산                                                │
│    - 각 구간별 경로 계산                                    │
│    - 경유지 최적화 (선택적)                                 │
│   ↓                                                         │
│ 출력: directions (상세 경로 정보)                          │
└──────────────────┬──────────────────────────────────────────┘
                   │
                   ↓
┌─────────────────────────────────────────────────────────────┐
│ 결과 저장                                                    │
│ agent_tasks[task_id] = {                                   │
│   "success": True,                                          │
│   "course": course_result,                                  │
│   "done": True                                              │
│ }                                                           │
└──────────────────┬──────────────────────────────────────────┘
                   │
                   ↓
┌─────────────────────────────────────────────────────────────┐
│ 프론트엔드 폴링                                             │
│ GET /api/locations/<task_id>                               │
│ → 코스 정보 반환                                            │
└─────────────────────────────────────────────────────────────┘
```

### 2. 경로 안내 상세 플로우

```
┌─────────────────────────────────────────────────────────────┐
│ 사용자 "경로 안내" 버튼 클릭                                │
└──────────────────┬──────────────────────────────────────────┘
                   │
                   ↓
┌─────────────────────────────────────────────────────────────┐
│ POST /api/route-guide/<task_id>                            │
│ - transportation: "도보, 지하철"                           │
│ - departureTime: "2025-02-15T14:00:00"                    │
└──────────────────┬──────────────────────────────────────────┘
                   │
                   ↓
┌─────────────────────────────────────────────────────────────┐
│ RoutingAgent.execute()                                      │
│                                                             │
│ 1. transportation 파싱                                      │
│    - preferred_modes = ['transit', 'walking']              │
│    - primary_mode = 'transit' (대중교통 우선)              │
│   ↓                                                         │
│ 2. API 선택 로직                                            │
│    - mode == 'transit' → Google Maps API                   │
│    - mode == 'walking' + 한국 내 → T Map API               │
│    - mode == 'driving' + 한국 내 → T Map API               │
│   ↓                                                         │
│ 3. 경로 계산                                                │
│    - 각 구간별 경로 계산                                    │
│    - preferred_modes 순서대로 시도                         │
│   ↓                                                         │
│ 4. 경로 정보 변환                                           │
│    - route_paths 생성 (각 구간별 좌표)                      │
│    - guide 텍스트 생성                                      │
└──────────────────┬──────────────────────────────────────────┘
                   │
                   ↓
┌─────────────────────────────────────────────────────────────┐
│ 응답 반환                                                   │
│ {                                                           │
│   "guide": ["경로 안내 텍스트 배열"],                       │
│   "route_paths": [                                          │
│     [                                                       │
│       {                                                      │
│         "path": [{"lat": ..., "lng": ...}, ...],           │
│         "travel_mode": "WALKING",                           │
│         "transit_details": null                             │
│       }                                                     │
│     ]                                                       │
│   ]                                                         │
│ }                                                           │
└──────────────────┬──────────────────────────────────────────┘
                   │
                   ↓
┌─────────────────────────────────────────────────────────────┐
│ 프론트엔드 지도 렌더링                                      │
│ - script.js의 drawRouteFromServerData()                    │
│ - Google Maps Polyline으로 경로 그리기                      │
└─────────────────────────────────────────────────────────────┘
```

### 3. 챗봇 대화 플로우

```
┌─────────────────────────────────────────────────────────────┐
│ 사용자 메시지 입력                                          │
│ "첫 번째 장소는 뭐야?"                                     │
└──────────────────┬──────────────────────────────────────────┘
                   │
                   ↓
┌─────────────────────────────────────────────────────────────┐
│ POST /api/chat                                              │
│ {                                                           │
│   "message": "첫 번째 장소는 뭐야?",                        │
│   "task_id": "uuid-string"                                 │
│ }                                                           │
└──────────────────┬──────────────────────────────────────────┘
                   │
                   ↓
┌─────────────────────────────────────────────────────────────┐
│ get_chatbot_response() (chatbot.py)                        │
│                                                             │
│ 1. 코스 정보 로드                                           │
│    - agent_tasks[task_id]["course"]                         │
│   ↓                                                         │
│ 2. 채팅 히스토리 로드                                       │
│    - chat_histories[task_id]                               │
│   ↓                                                         │
│ 3. OpenAI API 호출                                         │
│    - 코스 정보를 컨텍스트로 포함                           │
│    - 사용자 메시지와 히스토리 전달                         │
│   ↓                                                         │
│ 4. 응답 파싱                                                │
│    - 코스 수정 요청 감지                                    │
│    - parse_course_update() 호출 (선택적)                   │
│   ↓                                                         │
│ 5. 히스토리 업데이트                                        │
│    - 사용자 메시지 추가                                     │
│    - 응답 추가                                              │
└──────────────────┬──────────────────────────────────────────┘
                   │
                   ↓
┌─────────────────────────────────────────────────────────────┐
│ 응답 반환                                                   │
│ {                                                           │
│   "response": "첫 번째 장소는..."                           │
│ }                                                           │
└─────────────────────────────────────────────────────────────┘
```

---

## API 구조

### RESTful API 엔드포인트

#### 1. 코스 생성

**엔드포인트**: `POST /api/create-trip`

**요청 본문**:
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

**응답**:
```json
{
  "taskId": "550e8400-e29b-41d4-a716-446655440000",
  "status": "processing"
}
```

**동작**:
1. task_id 생성 (UUID)
2. `agent_tasks[task_id]` 초기화
3. 별도 스레드에서 `execute_Agents()` 실행
4. 즉시 task_id 반환 (비동기 처리)

#### 2. 작업 상태 조회

**엔드포인트**: `GET /status/<task_id>`

**응답**:
```json
{
  "done": false,
  "success": false,
  "error": null,
  "message": "🔍 '서울' 지역의 '비 오는 날 서울 실내 데이트' 테마를 분석 중입니다..."
}
```

**용도**: 프론트엔드에서 작업 진행 상태를 폴링하여 확인

#### 3. 장소 정보 조회

**엔드포인트**: `GET /api/locations/<task_id>`

**응답**:
```json
{
  "places": [
    {
      "name": "장소명",
      "address": "주소",
      "coordinates": {"lat": 37.5665, "lng": 126.9780},
      "category": "관광지",
      "rating": 4.5,
      "photo_url": "https://...",
      "map_url": "https://...",
      "trust_score": 0.95
    },
    ...
  ],
  "sequence": [0, 2, 5, 3, 1],
  "transportation": "도보, 지하철",
  "visit_date": "2025-02-15",
  "weather_info": {
    "0": {
      "temperature": 15.0,
      "condition": "맑음",
      "description": "맑음",
      "humidity": 60,
      "wind_speed": 2.5,
      "icon": "01d",
      "icon_type": "openweather",
      "date": "2025-02-15"
    }
  }
}
```

#### 4. 경로 안내 조회

**엔드포인트**: `POST /api/route-guide/<task_id>`

**요청 본문**:
```json
{
  "transportation": "도보, 지하철",
  "departureTime": "2025-02-15T14:00:00"
}
```

**응답**:
```json
{
  "guide": [
    "🗺️ <strong>상세 경로 안내 (도보, 지하철)</strong>",
    "",
    "🚶 도보 이동: 5분 (300m)",
    "  • 광화문역 5번 출구로 이동",
    "🚇 지하철 이동: 15분",
    "  • 3호선 광화문역 → 안국역",
    "  • 하차 후 2번 출구",
    ...
  ],
  "route_paths": [
    [
      {
        "path": [
          {"lat": 37.5665, "lng": 126.9780},
          {"lat": 37.5670, "lng": 126.9785},
          ...
        ],
        "travel_mode": "WALKING",
        "transit_details": null
      },
      {
        "path": [...],
        "travel_mode": "TRANSIT",
        "transit_details": {
          "line": {"name": "서울 지하철 3호선"},
          "departure_stop": {"name": "광화문역"},
          "arrival_stop": {"name": "안국역"}
        }
      }
    ]
  ]
}
```

#### 5. 챗봇 대화

**엔드포인트**: `POST /api/chat`

**요청 본문**:
```json
{
  "message": "첫 번째 장소는 뭐야?",
  "task_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**응답**:
```json
{
  "response": "첫 번째 장소는 '국립중앙박물관'입니다. 이곳은..."
}
```

---

## 프론트엔드 구조

### 컴포넌트 계층

```
App.tsx
├── Navbar.tsx
├── Hero.tsx
├── Features.tsx
├── TripPlanner.tsx
│   ├── PlaceSearchModal.tsx
│   └── (여행 계획 입력 폼)
├── Gallery.tsx
├── Philosophy.tsx
├── Cta.tsx
└── Footer.tsx
```

### 상태 관리

#### 로컬 상태
- React `useState` 훅 사용
- 컴포넌트별 독립적인 상태 관리

#### 전역 상태
- `window` 객체를 통한 전역 변수
  - `window.map`: Google Maps 인스턴스
  - `window.markers`: 마커 배열
  - `window.polylines`: 경로 라인 배열
  - `window.courseData`: 코스 데이터
  - `window.TASK_ID`: 현재 작업 ID

#### 서버 상태
- REST API 호출로 관리
- 폴링 방식으로 작업 상태 확인

### 지도 렌더링 (script.js)

#### 초기화
```javascript
async function initMap() {
    const { Map } = await google.maps.importLibrary("maps");
    const { AdvancedMarkerElement, PinElement } = await google.maps.importLibrary("marker");
    
    map = new Map(document.getElementById("map-container"), {
        zoom: 12,
        center: { lat: 37.5665, lng: 126.9780 },
        mapId: "DEMO_MAP_ID"
    });
}
```

#### 마커 생성
- `AdvancedMarkerElement` 사용
- 마커 위에 가게 이름 라벨 표시
- PinElement와 라벨을 포함한 컨테이너 생성

#### 경로 그리기
- `Polyline` 사용
- 서버에서 받은 `route_paths` 데이터 기반
- 교통수단별 색상 구분

---

## 기술 스택

### 백엔드

| 카테고리 | 기술 | 버전 | 용도 |
|---------|------|------|------|
| 언어 | Python | 3.8+ | 백엔드 개발 |
| 웹 프레임워크 | Flask | 3.1.2+ | RESTful API 서버 |
| 비동기 처리 | asyncio | 내장 | 비동기 작업 처리 |
| HTTP 클라이언트 | aiohttp | 3.9.0+ | 비동기 HTTP 요청 |
| LLM 프레임워크 | LangChain | 0.3.x | 에이전트 시스템 |
| API 클라이언트 | googlemaps | 4.10.0+ | Google Maps API |
| API 클라이언트 | tavily-python | 0.3.0+ | Tavily 검색 API |
| API 클라이언트 | openai | 1.0.0+ | OpenAI API |
| 데이터 처리 | scikit-learn | 1.0.0+ | DBSCAN 군집화 |
| 이미지 처리 | Pillow | - | 이미지 생성 |

### 프론트엔드

| 카테고리 | 기술 | 버전 | 용도 |
|---------|------|------|------|
| UI 라이브러리 | React | 19.2.3+ | 컴포넌트 기반 UI |
| 언어 | TypeScript | 5.8.2+ | 타입 안정성 |
| 빌드 도구 | Vite | 6.2.0+ | 개발 서버 및 빌드 |
| 아이콘 | Lucide React | 0.562.0+ | 아이콘 컴포넌트 |
| 지도 API | Google Maps JS API | - | 지도 렌더링 |

### 외부 API

| 서비스 | 용도 | 문서 |
|--------|------|------|
| Tavily API | 실시간 웹 검색 | [Tavily Docs](https://docs.tavily.com) |
| Google Maps API | 경로 계산, 지오코딩 | [Google Maps Platform](https://developers.google.com/maps) |
| T Map API | 한국 내 도보/자동차 경로 | [T Map Open API](https://openapi.sk.com) |
| OpenAI API | LLM 기반 코스 제작 | [OpenAI Platform](https://platform.openai.com) |
| OpenWeather API | 날씨 정보 조회 | [OpenWeather](https://openweathermap.org/api) |

---

## 성능 최적화

### 1. 비동기 처리

#### 병렬 API 호출
```python
# 여러 장소의 경로를 병렬로 계산
tasks = [
    get_segment_direction(from_item, to_item)
    for from_item, to_item in zip(waypoints[:-1], waypoints[1:])
]
results = await asyncio.gather(*tasks)
```

#### 비동기 HTTP 요청
- `aiohttp`를 사용한 비동기 HTTP 클라이언트
- 동시에 여러 API 호출 가능

### 2. 캐싱 메커니즘

#### check_routing 결과 캐시
```python
_routing_cache = {}  # 전역 캐시 딕셔너리

# 캐시 키 생성 (장소 이름 + 좌표 + mode)
cache_key = hashlib.md5(cache_key_str.encode()).hexdigest()

# 캐시 확인
if cache_key in _routing_cache:
    return _routing_cache[cache_key]
```

**효과**: 동일한 장소 조합에 대한 중복 API 호출 방지

### 3. 사전 필터링

#### 거리 기반 필터링
```python
# 두 지점이 10m 이내인 경우 API 호출 생략
if distance_m < 10:
    return {
        "success": True,
        "directions": [{"distance": int(distance_m), ...}]
    }
```

**효과**: 불필요한 API 호출 감소

### 4. LLM 호출 최적화

#### 반복 횟수 제한
```python
planner_executer = AgentExecutor(
    max_iterations=10,  # 최대 반복 횟수 제한
    max_execution_time=300  # 최대 실행 시간 5분
)
```

#### 프롬프트 최적화
- 중복 호출 방지 지시 포함
- 명확한 출력 형식 지정

---

## 확장성 고려사항

### 현재 구조의 특징

1. **모듈화된 설계**
   - Agent와 Tool이 독립적으로 동작
   - 새로운 기능 추가가 용이

2. **인터페이스 기반 설계**
   - `BaseAgent`와 `BaseTool`을 통한 일관된 인터페이스
   - 다형성 활용

3. **비동기 처리**
   - 모든 Agent와 Tool이 비동기로 동작
   - 확장 가능한 성능

### 확장 가능한 영역

#### 1. 새로운 에이전트 추가

예시: `RecommendationAgent` 추가

```python
class RecommendationAgent(BaseAgent):
    """추천 에이전트 - 사용자 히스토리 기반 추천"""
    
    async def execute(self, input_data):
        # 추천 로직 구현
        pass
```

#### 2. 새로운 도구 추가

예시: `WeatherTool` 추가

```python
class WeatherTool(BaseTool):
    """날씨 도구 - 다양한 날씨 API 통합"""
    
    async def execute(self, **kwargs):
        # 날씨 조회 로직 구현
        pass
```

#### 3. 데이터베이스 통합

현재는 메모리 기반 상태 관리 (`agent_tasks`). 영구 저장이 필요한 경우:

- **SQLite**: 소규모 프로젝트
- **PostgreSQL**: 대규모 프로젝트
- **Redis**: 캐싱 및 세션 관리

#### 4. 메시지 큐 도입

장기 실행 작업의 경우:

- **Celery + Redis**: 비동기 작업 큐
- **RabbitMQ**: 메시지 브로커

#### 5. 마이크로서비스 아키텍처

현재는 모놀리식 구조. 필요시 분리 가능:

- 검색 서비스
- 코스 제작 서비스
- 경로 계산 서비스
- 챗봇 서비스

---

## 보안 고려사항

### 1. API 키 관리

- `.env` 파일 사용 (`.gitignore`에 포함)
- 환경 변수로 관리
- 절대 코드에 하드코딩하지 않음

### 2. 입력 검증

- 모든 Agent와 Tool에서 `validate_input()` 수행
- 타입 검증 및 범위 검증

### 3. CORS 설정

```python
CORS(app)  # 기본 설정
# 또는 특정 도메인만 허용
CORS(app, origins=["https://yourdomain.com"])
```

### 4. 에러 메시지

- 민감한 정보를 에러 메시지에 포함하지 않음
- 사용자에게는 일반적인 에러 메시지만 표시

---

## 배포 구조

### 개발 환경

```
Backend: Flask 개발 서버 (localhost:5000)
Frontend: Vite 개발 서버 (localhost:5173)
```

### 프로덕션 환경 (권장)

```
┌─────────────────────────────────────────┐
│         Nginx (Reverse Proxy)           │
│  - 정적 파일 서빙 (프론트엔드 빌드)     │
│  - API 요청을 Gunicorn으로 프록시       │
└──────────────┬──────────────────────────┘
               │
    ┌──────────┴──────────┐
    │                     │
┌───▼────┐         ┌──────▼─────┐
│Gunicorn│         │  Static    │
│(Flask) │         │   Files    │
└────────┘         └────────────┘
```

### 배포 스크립트 예시

```bash
# 백엔드 빌드 및 실행
cd RoutePick_Backend
gunicorn -w 4 -b 0.0.0.0:5000 app:app

# 프론트엔드 빌드
cd RoutePick_Frontend
npm run build
# 빌드된 파일을 Nginx로 서빙
```

---

## 데이터 모델

### Place (장소)

```python
{
    "name": str,                    # 장소명
    "address": str,                 # 주소
    "coordinates": {
        "lat": float,               # 위도
        "lng": float                # 경도
    },
    "category": str,                # 카테고리 ("관광지", "식당", "카페" 등)
    "rating": float,                # 평점 (0.0 ~ 5.0)
    "photo_url": str,               # 사진 URL
    "map_url": str,                 # Google Maps 링크
    "place_id": str,                # Google Places ID
    "trust_score": float,           # 신뢰도 점수 (0.0 ~ 1.0)
    "is_saved_place": bool,         # 저장된 장소 여부
    "original_index": int           # 원본 인덱스
}
```

### Course (코스)

```python
{
    "places": List[Place],          # 선택된 장소 리스트
    "sequence": List[int],           # 방문 순서 인덱스
    "estimated_duration": Dict[int, int],  # 장소별 체류 시간(분)
    "course_description": str,      # 코스 설명
    "weather_info": Dict[int, Dict],  # 장소별 날씨 정보
    "visit_date": str,              # 방문 날짜
    "transportation": str            # 교통수단
}
```

### Directions (경로)

```python
{
    "success": bool,
    "total_duration": int,          # 총 소요 시간 (초)
    "total_distance": int,          # 총 거리 (미터)
    "directions": [
        {
            "from": str,            # 출발지명
            "to": str,              # 목적지명
            "duration": int,        # 소요 시간 (초)
            "distance": int,        # 거리 (미터)
            "duration_text": str,   # "5분"
            "distance_text": str,   # "300m"
            "steps": List[Dict],    # 상세 단계별 안내
            "mode": str,            # "walking", "driving", "transit"
            "route_coordinates": List[Dict],  # 경로 좌표
            "transit_details": Dict  # 대중교통 상세 정보 (선택적)
        }
    ],
    "error": Optional[str]
}
```

---

## 에러 처리 전략

### 계층별 에러 처리

#### 1. Tool 레벨
```python
try:
    result = await api_call()
    return {"success": True, "result": result}
except Exception as e:
    return {
        "success": False,
        "error": f"API 호출 실패: {str(e)}"
    }
```

#### 2. Agent 레벨
```python
# Tool 실패 시 폴백 로직
if not tmap_result.get("success"):
    print("⚠️ T Map API 실패, Google Maps API로 폴백합니다.")
    result = await google_maps_tool.execute(...)
```

#### 3. API 레벨
```python
try:
    course_result = await execute_Agents(task_id, input_data)
    agent_tasks[task_id]["success"] = True
except Exception as e:
    agent_tasks[task_id]["error"] = str(e)
    agent_tasks[task_id]["success"] = False
```

### 폴백 메커니즘

1. **T Map API 실패** → Google Maps API 사용
2. **경로 계산 실패** → 기본 경로 정보 반환
3. **LLM 호출 실패** → 기본 코스 구조 반환
4. **날씨 정보 실패** → 날씨 정보 없이 진행

---

## 모니터링 및 로깅

### 로그 레벨

- `🔍`: 검색 단계
- `🧠`: 계획 단계
- `🗺️`: 경로 계산 단계
- `🌤️`: 날씨 정보 조회
- `✅`: 성공 메시지
- `⚠️`: 경고 메시지
- `❌`: 에러 메시지

### 주요 로그 포인트

1. **Agent 실행 시작/종료**
2. **API 호출 및 응답**
3. **에러 발생 시점**
4. **캐시 히트/미스**
5. **성능 메트릭** (선택적)

---

## 테스트 전략

### 단위 테스트

- 각 Tool의 `execute()` 메서드 테스트
- 각 Agent의 `execute()` 메서드 테스트
- 입력 검증 로직 테스트

### 통합 테스트

- Agent 파이프라인 전체 테스트
- API 엔드포인트 테스트
- 프론트엔드-백엔드 통신 테스트

### 테스트 파일

- `test_agent_interactive.py`: 인터랙티브 테스트
- `planner_test.py`: PlanningAgent 테스트
- `debug_routing.py`: RoutingAgent 디버깅
- `debug_tavily.py`: Tavily 검색 디버깅

---

## 결론

RoutePick은 **모듈화된 멀티 에이전트 아키텍처**를 통해 확장 가능하고 유지보수하기 쉬운 구조를 가지고 있습니다. 각 컴포넌트는 명확한 책임을 가지며, 인터페이스를 통해 느슨하게 결합되어 있어 새로운 기능 추가가 용이합니다.

### 핵심 설계 원칙

1. **관심사의 분리**: Agent, Tool, API 레이어 분리
2. **인터페이스 기반 설계**: BaseAgent, BaseTool을 통한 일관성
3. **비동기 처리**: 성능 최적화 및 확장성
4. **에러 복원력**: 폴백 메커니즘으로 안정성 확보
5. **캐싱 및 최적화**: 불필요한 호출 방지

이러한 구조를 통해 RoutePick은 사용자에게 최적화된 여행 코스를 제공하면서도, 새로운 기능 추가와 성능 개선이 지속적으로 가능합니다.
