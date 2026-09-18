# AutoShorts

블로그 URL 하나를 입력하면 본문 추출 → 숏폼 대본 생성 → TTS → 자막 → 9:16 영상 렌더링까지 자동으로 수행하는 로컬 기반 숏폼 생성 파이프라인입니다.

## MVP 성공 기준
- 네이버 블로그 / 티스토리 / 일반 블로그 URL 지원
- URL 입력 이후 사용자 개입 0회
- 60초 미만, 1080x1920 MP4 생성
- 전체 처리 시간 3분 이내 목표
- 단계별 검증과 에러 로그 제공

## CLI 실행
1. Python 3.10+ 설치
2. `pip install -r requirements.txt`
3. `.env.example`을 `.env`로 복사하고 API 키 입력
4. `python app.py`

## Streamlit UI
```bash
streamlit run streamlit_app.py
```

URL을 입력하고 **숏폼 생성** 버튼을 누르면 진행 상태, 대본, 최종 영상과 다운로드 버튼을 확인할 수 있습니다.

## 실제 URL Scraper 점검
OpenAI API 없이 블로그 본문 추출만 확인할 수 있습니다.

```bash
python scripts/smoke_scraper.py "https://blog.naver.com/..."
```

출력:
- 플랫폼
- 제목
- 본문 글자 수
- 이미지 수
- 본문 앞부분 미리보기

## 테스트
```bash
PYTHONPATH=. pytest -q
```

Mock E2E 테스트는 외부 API 호출 없이 다음 연결을 검증합니다.

```text
Scraper → Script → TTS → Subtitle → Renderer → MP4
```

개발 기록은 `docs/DEVLOG.md`, 제품 요구사항은 `docs/PRD.md`에서 관리합니다.
