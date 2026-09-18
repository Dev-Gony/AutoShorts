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

### 오늘 결정한 사항
- 기능 개발 브랜치: `feat/mvp-foundation`
- 대본/TTS/전사 모델은 환경변수로 교체 가능
- 자막은 TTS 오디오를 재전사한 타임스탬프를 우선 사용
- 렌더러는 MoviePy 2.x로 MVP 구현 후 3분 KPI 미달 시 FFmpeg 직접 호출 검토
- 블로그 이미지 URL도 추출해 후속 버전에서 영상 소재로 재사용 가능하게 유지
- 저장소 자체 검증을 위해 GitHub Actions CI 추가

### 구현 완료
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
- [x] Scraper 단위 테스트
- [x] GitHub Actions CI

### 현재 검증 단계
코드 구조상 URL 하나를 받아 최종 MP4까지 이어지는 E2E 흐름을 구현했다.
실제 외부 블로그 URL + OpenAI API + 배경 MP4를 사용한 실데이터 실행 검증은 다음 단계다.

### 다음 작업
1. CI 통과 여부 확인 및 실패 수정
2. 실제 네이버/티스토리 샘플 URL 테스트
3. 59초 초과 시 대본 자동 축약/재생성 루프
4. 자막 가독성 개선 및 한국어 폰트 전략
5. 렌더링 시간 측정
6. 3분 KPI 미달 시 FFmpeg 직접 렌더러 전환
7. Streamlit UI

### 리스크
- 네이버 SmartEditor 버전별 DOM 차이
- 이미지 위주 블로그 글
- 외부 요청 차단/레이트리밋
- MoviePy 렌더링 속도
- 한국어 자막 폰트 의존성
- 실제 OpenAI 계정에서 사용 가능한 모델명/권한 차이 가능성

### 검증 메모
ChatGPT 작업 환경의 일반 네트워크에서 github.com DNS 접근이 차단되어 로컬 clone 기반 테스트는 수행하지 못했다.
대신 GitHub Actions에서 compileall + pytest를 수행하도록 CI를 추가했다.
