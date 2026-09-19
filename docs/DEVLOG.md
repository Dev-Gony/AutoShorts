# AutoShorts Development Log

## 2026-09-18

### 프로젝트 시작
블로그 URL 하나로 60초 미만 세로형 숏폼 MP4를 자동 생성하는 로컬 MVP 개발 시작.

### 아키텍처
URL → Scraper → Cleaner → Script Generator → TTS → Transcription → Subtitle → Renderer → MP4

Scraper는 플랫폼별 Adapter 구조:
- NaverScraper
- TistoryScraper
- GenericScraper

### 기반 구현 완료
- [x] 저장소 초기화
- [x] PRD/개발일지
- [x] URL 검증
- [x] Generic Scraper
- [x] Naver Scraper 1차
- [x] Tistory Scraper 1차
- [x] 플랫폼별 Scraper Factory
- [x] LLM 숏폼 대본 생성
- [x] OpenAI TTS
- [x] 오디오 재전사 기반 자막 타임스탬프
- [x] SRT 생성
- [x] MoviePy 9:16 렌더러
- [x] CLI End-to-End 파이프라인
- [x] 59초 초과 시 자동 축약/TTS 재시도
- [x] 배경 영상 미등록 시 기본 배경 fallback
- [x] GitHub Actions CI

### 2차 작업 - 검증/UI
기능 연결을 실제 사용 형태에 가깝게 검증하기 위한 작업 진행.

추가 구현:
- [x] Pipeline dependency injection 구조
- [x] UI용 progress callback
- [x] Streamlit MVP UI
- [x] 실제 URL Scraper smoke command
- [x] 외부 API 없는 Mock E2E 테스트
- [x] 결과 MP4 UI 재생/다운로드

Mock E2E 검증 범위:
Scraper → Script Generator → TTS → timed subtitle → Renderer → output MP4

### 현재 남은 핵심 검증
- [ ] 실제 네이버 공개 글 본문 추출
- [ ] 실제 티스토리 공개 글 본문 추출
- [ ] 실제 OpenAI API 대본 생성
- [ ] 실제 TTS + timestamp transcription
- [ ] 실제 MoviePy 한국어 자막 렌더링
- [ ] 실제 45~58초 영상 처리 시간 측정
- [ ] 3분 KPI 검증

### 다음 작업
1. CI에서 Mock E2E 포함 전체 테스트 통과 확인
2. 실 URL Scraper 검증
3. 실 API E2E 실행을 위한 runbook 확정
4. 한국어 자막 폰트/줄바꿈 개선
5. 렌더링 시간 계측
6. 3분 초과 시 FFmpeg renderer 검토

### 리스크
- 네이버 SmartEditor DOM 버전 차이
- 이미지 위주 블로그 글
- 외부 사이트 요청 차단/레이트리밋
- 한국어 TextClip 폰트 환경 차이
- MoviePy 렌더링 속도
- 실제 OpenAI API 계정의 모델 접근 권한 차이

### 개발 원칙
- API Key는 Git에 저장하지 않는다.
- 실 API가 없어도 Mock 테스트로 파이프라인 연결 상태를 검증한다.
- 외부 URL을 사용하는 검증은 CI 필수 테스트가 아니라 수동 smoke test로 분리한다.


## 2026-09-19

### Gemini Provider 지원

사용자가 Gemini API Key를 보유하고 있어 기본 AI provider를 Gemini로 전환.

추가/변경:
- [x] `AI_PROVIDER=gemini|openai`
- [x] Gemini 대본 생성
- [x] Gemini TTS
- [x] Gemini WAV 출력
- [x] Gemini 경로 자막 타이밍 자동 생성
- [x] OpenAI provider 기존 기능 유지
- [x] CLI / Streamlit / doctor provider-aware 전환
- [x] `google-genai` 의존성 추가

기본 Gemini 모델:
- Script: `gemini-2.5-flash-lite`
- TTS: `gemini-3.1-flash-tts-preview`

실사용 검증 예정:
1. 사용자 Gemini API Key로 doctor 재확인
2. 실제 네이버 블로그 E2E
3. TTS 모델 quota/사용 가능 여부 확인
4. 한국어 자막 렌더링 확인


### Gemini 모델 변경 대응
- [x] 신규 사용자에게 중단된 `gemini-2.5-flash-lite` 제거
- [x] 기본 대본 모델을 `gemini-3.5-flash-lite`로 변경
- [x] 기존 로컬 .env에 2.5 모델명이 남아 있어도 자동으로 3.5로 치환
- [x] 사용하지 않는 Automatic Function Calling 비활성화

### 숏폼 품질 v2 — PR #6

사용자 검증에서 기본 TTS의 낭독체, 자막 하단 잘림, 기본 폰트/단순 슬라이드 구성 문제가 제기됐다. 사진이 표시되고 파일이 생성되는 것을 완성 품질로 취급한 기존 기준을 수정했다.

변경:
- 맛집 리뷰(Puck), 밝은 브이로그(Aoede), 차분한 설명(Sulafat) 음성 연출 프리셋.
- 대화체 장면 대본, 억양/강조/호흡 지시, 피치를 유지하는 재생 속도 조절.
- 짧은 음성 샘플과 캐시. 샘플과 실제 영상은 동일 음성 경로를 사용.
- 글자 수 비율 자막 타이밍 삭제. 생성한 발화별 PCM 프레임 수로 자막 구간 확정.
- 글리프 경계 기반 자막 그리기, 최대 2줄, 굵은 한글 폰트, 키워드 강조와 반투명 카드.
- 사진의 흐림 확장 배경, 약한 줌, 짧은 전환. Gemini가 축소 사진을 보고 장면에 맞는 사진 번호 선택.
- 유효한 사진/영상이 없으면 회색 영상 대신 AI 호출 전에 중단.
- 실행별 manifest와 단계별 소요시간, v2 결과물의 API 호출 없는 화면 재렌더링.
- 한글 폰트 지원/자막 위치/실측 타임라인/캐시/실제 MP4 인코딩 테스트.

확인한 결과:
- 첫 구현 커밋 f941144: 로컬 48개 테스트 통과.
- GitHub Actions run 35435106197: 48개 테스트 통과, 실패/스킵 0개.
- Mock 파일 생성과 별개로 실제 H.264/AAC 인코딩 테스트 포함.
- 1080x1920, 6초 로컬 레이아웃 검증 영상: 렌더링 8.359초. 사용자 화면 캡처의 사진 영역과 테스트 톤 사용. 전체 파이프라인/실제 음성 품질 성능이 아님.
- 첫/마지막 프레임을 실제 인코딩된 MP4에서 추출해 확인.
- Google SDK 설정 계약 테스트 2개를 추가했으며 최종 결과는 PR CI에 기록.

검증 한계:
- 사용자가 제공한 입력은 화면 캡처여서 기존 음성은 직접 듣지 못했다.
- 개발 환경에서 실제 Gemini/OpenAI TTS API를 호출하지 않았으므로 개선 음성의 자연스러움을 검증 완료로 표시하지 않는다.
- 발화별 TTS로 호출 수가 증가한다. 무료 한도 및 180초 목표는 계정/모델/PC 환경에서 별도 검증해야 한다.
- 슈퍼쇼츠의 내부 TTS 공급자는 확인되지 않았으며 같은 엔진/음성을 사용한다고 주장하지 않는다.

사용 방법과 한계: [QUALITY_V2.md](QUALITY_V2.md)


### Typecast TTS 1차 연동

Gemini TTS 미리듣기 검증 후 더 자연스러운 한국어 숏폼 내레이션을 비교하기 위해 Typecast를 1순위 TTS Provider로 분리.

구현:
- [x] 대본 Provider(`AI_PROVIDER`)와 음성 Provider(`TTS_PROVIDER`) 분리
- [x] Typecast 공식 Python SDK 0.4.0 사용
- [x] SSFM 3.0 + Smart Emotion
- [x] `TYPECAST_VOICE_ID` 수동 고정 지원
- [x] voice_id 미지정 시 Voice Recommendations API로 스타일별 후보 자동 선택
- [x] 기존 문장별 실측 타임라인/캐시/영상 렌더링 유지
- [x] Streamlit에서 Typecast 준비 상태와 짧은 음성 미리듣기 제공
- [x] doctor에서 Typecast API 키 점검
- [x] SDK request model, 보이스 추천, Smart Emotion 요청 단위 테스트

실사용 검증 순서:
1. Typecast API 계정/키 발급
2. 짧은 음성 미리듣기
3. 자동 추천 보이스 청취
4. 마음에 드는 voice_id 고정
5. 동일 블로그로 Gemini TTS 대비 결과 비교

주의:
- Typecast 웹 편집기 구독과 API 플랜은 별개.
- 자동 추천 결과는 한국어 지원 여부를 메타데이터만으로 확정할 수 없으므로 반드시 미리듣기로 확인.
- 실제 API 키/크레딧/음질은 사용자 로컬 계정에서 검증 필요.


### Typecast 쇼츠 보이스 선택 UI

Typecast 자동 추천 1개만 사용했을 때 여전히 일반 내레이션 느낌이 남아 있어, 유튜브 쇼츠에 가까운 음색을 사용자가 직접 비교할 수 있도록 변경.

구현:
- [x] Typecast 추천 보이스 최대 5개 표시
- [x] 이름/성별/연령/추천 점수 표시
- [x] Typecast 기본 preview_url이 있으면 즉시 미리듣기
- [x] 선택한 voice_id로 AutoShorts 동일 문장 재생성
- [x] 선택한 voice_id를 전체 영상 Pipeline에 그대로 전달
- [x] 런타임 보이스 선택은 .env를 수정하지 않아도 됨
- [x] 추천 후보 파싱/수동 선택 단위 테스트

사용 흐름:
1. 스타일 선택
2. 쇼츠용 보이스 추천받기
3. 후보 5개 비교
4. 선택 보이스로 같은 문장 들어보기
5. 마음에 들면 블로그 URL로 전체 영상 생성
