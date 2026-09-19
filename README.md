# AutoShorts

블로그 URL 하나를 입력하면 본문 추출 → 숏폼 대본 생성 → TTS → 자막 → 9:16 영상 렌더링까지 자동으로 수행하는 로컬 숏폼 생성 파이프라인입니다.

## 기본 Provider

기본값은 **Gemini**입니다.

```env
AI_PROVIDER=gemini
GEMINI_API_KEY=your_key_here
```

OpenAI를 쓰고 싶으면:

```env
AI_PROVIDER=openai
OPENAI_API_KEY=your_key_here
```

## 설치

```bash
pip install -r requirements.txt
python scripts/doctor.py
```

## CLI

```bash
python app.py
```

## Streamlit UI

```bash
streamlit run streamlit_app.py
```

## 실제 URL Scraper 점검

```bash
python scripts/smoke_scraper.py "https://blog.naver.com/..."
```

## 테스트

```bash
PYTHONPATH=. pytest -q
```

개발 기록은 `docs/DEVLOG.md`, 제품 요구사항은 `docs/PRD.md`에서 관리합니다.
