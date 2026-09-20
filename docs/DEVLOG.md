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


### Typecast 인기 쇼츠 보이스 탭

일반 추천 보이스가 국어책 낭독처럼 들린다는 실사용 피드백에 따라 AI 추천을 기본 경로에서 내리고, Typecast가 공식 콘텐츠에서 쇼츠/릴스/밈 사용 사례로 소개한 캐릭터를 직접 선택하는 흐름으로 변경.

구현:
- [x] 인기 쇼츠 보이스 탭을 Typecast 기본 선택 화면으로 배치
- [x] 박창수, 발키리, 찬구, 채린이, 호빈이, 미스터 변사, 덕춘 할배 목록
- [x] 최근 사투리 숏폼 비교용 용식, 곽두필 추가
- [x] API에서 캐릭터 이름과 정확히 일치하는 voice_id만 허용
- [x] 유사 이름/다른 캐릭터로 자동 대체하지 않음
- [x] Typecast 기본 preview_url + AutoShorts 동일 문장 미리듣기
- [x] 선택한 인기 캐릭터 voice_id를 전체 영상 생성에 그대로 사용
- [x] 기존 AI 추천 탭은 보조 옵션으로 유지

품질 원칙:
- 공식 콘텐츠에 이름이 등장한다는 사실과 현재 API에서 해당 voice_id가 제공된다는 사실은 분리한다.
- 현재 계정/모델에서 정확한 캐릭터를 찾지 못하면 다른 음성으로 속이지 않고 오류를 표시한다.
- 실제 유튜브 사용 빈도를 독립적으로 측정한 순위라고 표시하지 않는다.


### Typecast 보이스 선택 방식 정정

인기 캐릭터 이름을 Studio 콘텐츠와 API 보이스 라이브러리에서 동일하게 사용할 수 있다고 가정한 구현이 실사용에서 실패함. 사용자의 API 계정에서는 '박창수'의 정확한 voice_id를 찾지 못했다.

정정:
- [x] 하드코딩한 인기 캐릭터 목록 제거
- [x] 공식 Typecast API의 /v2/voices에서 현재 계정에 실제 노출되는 보이스만 조회
- [x] ssfm-v30 지원 여부 필터
- [x] use_cases의 video/review/social/shorts 계열을 우선 정렬
- [x] preview_url이 있으면 즉시 비교
- [x] 사용자가 선택한 실제 voice_id를 전체 영상에 고정
- [x] AI 추천은 보조 탭으로 유지하고 /v2/voices/{voice_id}로 메타데이터 보강

교훈:
- Typecast Studio의 유명 캐릭터 이름과 API Voice Library는 별도 제품 표면으로 취급한다.
- API에 실제 노출된 voice_id만 실행 가능한 보이스로 표시한다.


### 서비스형 UI + 쇼츠 추천 TOP 8

실사용 화면에서 API 보이스 수십 개가 그대로 노출되어 서비스 UI로 보기 어렵다는 피드백 반영.

변경:
- [x] Typecast API가 공개하지 않는 실제 인기/사용량 순위를 '인기순'으로 표시하지 않음
- [x] 현재 계정의 실제 API 보이스를 use_cases/연령/미리듣기 가능 여부로 점수화
- [x] TikTok/Reels/Shorts, YouTube, Review, Social, Video, Ads/Promotion, Conversational 순으로 가중치 부여
- [x] 기본 화면에는 쇼츠 적합도 TOP 8만 카드 형태로 표시
- [x] 전체 보이스 목록과 검색은 '고급' 영역으로 이동
- [x] 좌측 개발자 사이드바 중심 UI 제거
- [x] 1) URL 입력 → 2) 보이스 선택/미리듣기 → 3) 생성 → 결과 화면 순서로 재구성
- [x] Provider/model 같은 기술 정보는 최소화
- [x] 선택한 보이스/소스/목표 길이를 생성 전 요약
- [x] 결과 MP4/대본/재렌더링을 결과 섹션으로 분리

표현 원칙:
- 'TOP 8'은 Typecast 전체 인기 순위가 아니라 AutoShorts의 쇼츠 적합도 순위다.
- 실제 인기 순위/사용량은 Typecast API에서 제공되는 데이터가 있을 때만 표시한다.


### Typecast 다국어 메타데이터 표시 수정
- [x] voice_name이 {"eng": "...", "kor": "..."} 객체로 오는 경우 한국어 이름 우선 표시
- [x] 한국어 이름이 없으면 영어 이름 fallback
- [x] use_cases 다국어 객체도 사람이 읽을 수 있는 문자열로 변환
- [x] 카드의 성별/연령을 한국어 UI 문구로 표시
- [x] HTML 카드 렌더링 시 외부 API 문자열 escape 적용


### 한국어 쇼츠 음성 우선 추천
- [x] Typecast 기본 preview_url 영어 샘플을 기본 카드에서 제거
- [x] 모든 카드 미리듣기를 AutoShorts 한국어 고정 문장 + language=kor 경로로 통일
- [x] 추천 API 질의에 '한국어 원어민처럼 자연스러운 한국인 크리에이터' 조건 명시
- [x] 외국인 억양/국어책 낭독체 제외 조건 추가
- [x] 맛집 리뷰·체험 리뷰·쇼츠/릴스 용도 조건 유지
- [x] 한국어 추천 결과를 실제 API voice_id와 결합해 전체 영상에도 동일 보이스 사용


### 서비스 UI v2 — 음성 엔진 숨기기

사용자 피드백에 따라 Typecast 보이스 탐색 UI를 기본 서비스 화면에서 제거하고, 향후 CLOVA 등 다른 한국어 TTS로 교체해도 화면 구조가 유지되도록 서비스 UX를 단순화.

변경:
- [x] 첫 화면에서 Typecast, 모델명, voice_id, use_case, 보이스 라이브러리 제거
- [x] 사용자 입력을 블로그 URL / 영상 스타일 / 목소리 / 생성 4단계로 단순화
- [x] 영상 스타일: 맛집·체험 리뷰 / 제품 리뷰 / 여행·일상 / 정보형
- [x] 음성은 '자연스러운 한국어 쇼츠 음성' 1개로 고정하는 UX
- [x] 현재 백엔드에서는 기존 한국어 추천 보이스 1개를 내부적으로 선택
- [x] 한국어 미리듣기 버튼 유지
- [x] 말하기 속도만 사용자 설정으로 노출
- [x] 생성 전 목표 길이/해상도/한국어 음성 안내
- [x] 결과 화면을 영상 / 처리시간 / 저장 / 대본 / 재렌더링 중심으로 정리

다음 단계:
- CLOVA Voice 연동 후 서비스 UI는 그대로 유지하고 내부 TTS provider만 교체
- 실제 한국어 쇼츠 음성 후보를 확정한 뒤 기본 보이스 1개로 고정


### 서비스 UI v3 — 정보 밀도와 제품 프리뷰 강화

사용자 피드백: v2는 정돈됐지만 화면이 지나치게 비어 있고 설정 폼처럼 보임.

개선:
- [x] 슈퍼쇼츠의 URL-first 진입은 유지
- [x] 상단을 2열 히어로로 재구성: 메시지/URL 입력 + 9:16 결과물 목업
- [x] 자동 처리 항목을 신뢰 배지로 노출: 60초 미만, 세로형, 대본, 사진 매칭, 한국어 자막
- [x] 영상 스타일을 4개 시각 카드로 표시
- [x] 음성 설정을 한 개 기본 한국어 음성 + 속도 조절로 단순화
- [x] 본문 분석 → 사진 매칭 → 대본/음성 → 자막/렌더링 흐름을 한 줄로 시각화
- [x] 생성 전 결과 스펙을 요약 카드로 표시
- [x] 결과 영역도 영상과 저장/대본/재렌더링 기능을 2열로 구성
- [x] 여백은 줄이되 정보 계층과 카드 단위를 유지

디자인 원칙:
- 경쟁 서비스 화면을 그대로 복제하지 않고 URL-first UX, 결과물 시각화, 카드형 선택 구조만 참고
- 첫 화면에서 사용자가 '무엇을 넣고 무엇을 받는지'를 바로 이해하게 함
- provider/model/API 세부사항은 계속 사용자 화면에서 숨김
