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
