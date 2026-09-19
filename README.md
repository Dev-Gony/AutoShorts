# AutoShorts

블로그 URL 하나를 입력하면  
**본문 추출 → 숏폼 대본 생성 → TTS → 자막 → 9:16 영상 렌더링**까지 이어지는 로컬 숏폼 생성 파이프라인입니다.

반복적인 콘텐츠 변환 작업을 사람의 개입 없이 한 번의 실행으로 연결하는 것을 목표로 만들었습니다.

## Problem

블로그 글을 숏폼 영상으로 다시 만들려면 여러 작업을 순서대로 반복해야 합니다.

- 본문 추출
- 영상용 대본 재작성
- 음성 생성
- 음성과 자막 타이밍 맞추기
- 세로 영상 구성
- 최종 MP4 렌더링

AutoShorts는 이 과정을 하나의 파이프라인으로 묶는 프로젝트입니다.

## Pipeline

```text
Blog URL
   |
   v
URL Validation
   |
   v
Content Extraction
   |
   v
Text Cleanup
   |
   v
Short-form Script
   |
   v
TTS
   |
   v
Timestamp / Subtitle
   |
   v
9:16 Video Rendering
   |
   v
MP4
```

## What Is Implemented

### Content extraction

블로그 URL을 입력받아 본문을 추출하고, 너무 짧거나 유효하지 않은 콘텐츠는 다음 단계로 넘기지 않습니다.

MVP에서 대상으로 하는 형태:

- 네이버 블로그
- 티스토리
- 일반 HTML 블로그

### Script generation

본문을 1분 내외 숏폼에 맞는 대본으로 변환합니다.

현재 AI Provider를 설정으로 분리해 Gemini와 OpenAI를 선택할 수 있도록 구성했습니다.

### TTS and subtitles

생성된 대본을 음성으로 변환하고, 타임스탬프 정보를 이용해 자막 구간을 만듭니다.

### Video rendering

준비된 배경 영상을 이용해 9:16 세로형 MP4를 생성합니다.

MVP 목표:

- 1080 x 1920
- 60초 미만
- URL 입력 이후 추가 사용자 개입 최소화

### CLI and Streamlit UI

CLI:

```bash
python app.py
```

Streamlit:

```bash
streamlit run streamlit_app.py
```

Streamlit 화면에서는 진행 단계를 확인하고 최종 영상을 바로 재생할 수 있습니다.

## Architecture

```text
app.py / streamlit_app.py
          |
          v
       Pipeline
          |
    +-----+-----+-----+-----+
    |           |           |
 Scraper     LLM/TTS     Renderer
    |           |           |
    +-----------+-----------+
                |
                v
             Output
```

UI와 실제 처리 흐름을 분리하고, CLI와 Streamlit이 같은 `Pipeline`을 호출하도록 구성했습니다.

## Tech Stack

- Python
- Gemini API
- OpenAI API
- BeautifulSoup4
- requests
- MoviePy
- Streamlit
- pytest

## Setup

```bash
pip install -r requirements.txt
python scripts/doctor.py
```

Gemini:

```env
AI_PROVIDER=gemini
GEMINI_API_KEY=...
```

OpenAI:

```env
AI_PROVIDER=openai
OPENAI_API_KEY=...
```

## Verification

Scraper smoke test:

```bash
python scripts/smoke_scraper.py "https://blog.naver.com/..."
```

Tests:

```bash
PYTHONPATH=. pytest -q
```

## Current Status

현재 구현된 부분:

- URL 입력
- 본문 추출
- LLM 기반 대본 생성
- Provider 분리
- TTS
- 자막 생성
- 9:16 영상 렌더링
- CLI
- Streamlit UI
- 기본 테스트 및 진단 스크립트

현재 개선 중인 부분:

- Provider별 모델 변경에 대한 안정적인 대응
- 긴 음성이 생성됐을 때 자동 축약
- 실제 블로그 유형별 scraper 안정성
- 렌더링 실패 시 오류 메시지 개선
- 결과 영상 품질 비교와 검증

## Scope

MVP에서는 자동 업로드, 회원가입, 결제, 클라우드 서비스화보다  
**URL 하나가 실제 MP4 하나로 끝까지 변환되는지**를 먼저 검증합니다.

제품 요구사항은 [docs/PRD.md](docs/PRD.md), 개발 기록은 [docs/DEVLOG.md](docs/DEVLOG.md)에서 관리합니다.
