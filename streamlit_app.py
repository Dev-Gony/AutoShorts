from __future__ import annotations

from pathlib import Path

import streamlit as st

from config import settings
from src.pipeline import Pipeline


st.set_page_config(
    page_title="AutoShorts MVP",
    page_icon="🎬",
    layout="centered",
)

st.title("🎬 AutoShorts")
st.caption("블로그 URL 하나로 숏폼 영상을 자동 생성합니다.")

with st.sidebar:
    st.subheader("상태")
    if settings.openai_api_key:
        st.success("OpenAI API Key 설정됨")
    else:
        st.error("OPENAI_API_KEY 미설정")
    st.write(f"대본 모델: `{settings.script_model}`")
    st.write(f"TTS 모델: `{settings.tts_model}`")
    st.write(f"최대 영상 길이: {settings.max_video_seconds:.0f}초")

url = st.text_input(
    "블로그 URL",
    placeholder="https://blog.naver.com/...",
)

generate = st.button(
    "숏폼 생성",
    type="primary",
    use_container_width=True,
    disabled=not settings.openai_api_key,
)

if generate:
    if not url.strip():
        st.warning("블로그 URL을 입력해주세요.")
        st.stop()

    progress = st.progress(0)
    status = st.empty()

    def on_progress(step: int, total: int, message: str) -> None:
        progress.progress(min(step / total, 1.0))
        status.info(f"[{step}/{total}] {message}")

    try:
        result = Pipeline(progress_callback=on_progress).run(url.strip())
    except Exception as exc:
        status.error(f"생성 실패: {exc}")
        st.exception(exc)
    else:
        progress.progress(1.0)
        status.success(f"완료 · {result.elapsed_seconds:.1f}초")

        st.subheader("생성 결과")
        st.write(f"**원문 제목:** {result.source.title}")
        st.write(f"**원문 길이:** {len(result.source.text):,}자")
        st.write(f"**대본 길이:** {len(result.short_script.script):,}자")
        st.write(f"**자막 구간:** {len(result.subtitles)}개")

        with st.expander("생성된 대본", expanded=True):
            st.write(result.short_script.script)

        video_path = Path(result.video_path)
        if video_path.exists():
            st.video(str(video_path))
            with video_path.open("rb") as file:
                st.download_button(
                    "MP4 다운로드",
                    data=file.read(),
                    file_name=video_path.name,
                    mime="video/mp4",
                    use_container_width=True,
                )
