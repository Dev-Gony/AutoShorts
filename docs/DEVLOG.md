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

### 진행 상태
- [x] 저장소 초기화
- [x] PRD/개발일지 생성
- [ ] Scraper
- [ ] LLM 대본
- [ ] TTS
- [ ] 자막
- [ ] Renderer
- [ ] E2E

### 리스크
- 네이버 SmartEditor DOM 차이
- 이미지 위주 글
- 외부 요청 차단/레이트리밋
- 렌더링 속도
- 한국어 자막 폰트 의존성
