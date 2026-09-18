# AutoShorts

블로그 URL 하나를 입력하면 본문 추출 → 숏폼 대본 생성 → TTS → 자막 → 9:16 영상 렌더링까지 자동으로 수행하는 로컬 기반 숏폼 생성 파이프라인입니다.

## MVP 성공 기준
- 네이버 블로그 / 티스토리 / 일반 블로그 URL 지원
- URL 입력 이후 사용자 개입 0회
- 60초 미만, 1080x1920 MP4 생성
- 전체 처리 시간 3분 이내 목표
- 단계별 검증과 에러 로그 제공

## 실행
1. Python 3.10+ 설치
2. `pip install -r requirements.txt`
3. `.env.example`을 `.env`로 복사하고 API 키 입력
4. `assets/backgrounds/`에 배경 MP4 추가
5. `python app.py`

개발 기록은 `docs/DEVLOG.md`, 제품 요구사항은 `docs/PRD.md`에서 관리합니다.
