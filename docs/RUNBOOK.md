# AutoShorts Local E2E Runbook

실제 URL과 OpenAI API를 사용해 첫 MP4를 만드는 절차입니다.

## 1. 설치

```bash
python -m venv .venv
```

Windows:

```bash
.venv\Scripts\activate
pip install -r requirements.txt
```

macOS/Linux:

```bash
source .venv/bin/activate
pip install -r requirements.txt
```

## 2. 환경변수

`.env.example`을 복사해 `.env`를 만들고 API Key를 입력합니다.

```env
OPENAI_API_KEY=...
```

중요: `.env`는 Git에 커밋하지 않습니다.

## 3. 환경 점검

```bash
python scripts/doctor.py
```

Python, API Key, FFmpeg, 작업 디렉터리를 점검합니다.

## 4. 블로그 파싱만 먼저 검증

```bash
python scripts/smoke_scraper.py "BLOG_URL"
```

정상 기준:
- OK 출력
- text_chars >= 100
- 제목이 본문 글의 제목과 유사
- 본문 preview에 메뉴/광고 위주가 아닌 실제 글 내용 포함

## 5. CLI E2E

```bash
python app.py
```

URL을 넣으면 다음 순서로 진행됩니다.

1. 본문 추출
2. 대본 생성
3. TTS
4. 타임스탬프 자막
5. 배경 선택
6. 1080x1920 렌더링

완료 파일은 `output/`에 저장됩니다.

## 6. Streamlit

```bash
streamlit run streamlit_app.py
```

브라우저에서 URL 입력 → 숏폼 생성 → 영상 재생/다운로드까지 확인합니다.

## 7. 합격 기준

첫 실제 MVP 합격은 아래를 모두 만족해야 합니다.

- URL 입력 이후 추가 사용자 입력 없음
- 원문 핵심과 대본 내용이 일치
- 60초 미만
- 자막과 음성의 체감 싱크가 정상
- 1080x1920 MP4 정상 재생
- 전체 처리 시간 180초 미만

## 8. 실패 시 보관할 정보

오류가 발생하면 다음 정보를 개발일지에 기록합니다.

- URL 플랫폼
- 어느 단계에서 실패했는지
- 에러 메시지
- 원문 글자 수
- 생성 대본 글자 수
- TTS 길이
- 총 처리 시간
- 사용 OS / Python 버전
