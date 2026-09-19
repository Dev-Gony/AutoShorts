from __future__ import annotations

from pathlib import Path

import streamlit as st

from config import settings
from src.pipeline import Pipeline, rerender
from src.preview import preview_voice, safe_error
from src.voices import PROFILES, selected_profile

st.set_page_config(page_title="AutoShorts", page_icon="🎬", layout="centered")
st.title("AutoShorts")
st.caption("블로그 사진과 대화체 음성으로 만드는 세로형 리뷰 영상")

script_ready = bool(settings.active_api_key)
tts_ready = bool(settings.active_tts_api_key)
can_generate = script_ready and tts_ready

with st.sidebar:
    st.subheader("음성 연출")
    default, _ = selected_profile()
    names = list(PROFILES)
    preset = st.selectbox(
        "스타일",
        names,
        index=names.index(default),
        format_func=lambda key: PROFILES[key].label,
    )
    speed = st.slider("말하기 속도", min_value=.9, max_value=1.2, value=1.06, step=.02)

    st.caption(f"대본/사진 분석: {settings.ai_provider}")
    if settings.tts_provider == "typecast":
        voice_label = settings.typecast_voice_id or "자동 추천"
        st.caption(f"음성: Typecast · {settings.typecast_model} · 보이스 {voice_label}")
        st.caption("Smart Emotion을 사용하고, 보이스 ID가 없으면 스타일 설명으로 후보를 자동 추천합니다.")
    else:
        st.caption(f"음성: {settings.tts_provider}")

    if not tts_ready:
        st.error(f"{settings.tts_provider.upper()} TTS API 키가 필요합니다.")
    if not script_ready:
        st.error(f"{settings.ai_provider.upper()} 대본 생성 API 키가 필요합니다.")

    if st.button("짧은 음성 먼저 듣기", disabled=not tts_ready):
        try:
            with st.spinner("음성 샘플 생성 중"):
                path = preview_voice(preset, speed)
            st.session_state["voice_preview"] = str(path)
        except Exception as exc:
            st.error(safe_error(exc))

    if st.session_state.get("voice_preview"):
        st.audio(st.session_state["voice_preview"])

    st.caption("먼저 짧은 샘플로 실제 음색을 확인한 뒤 전체 영상을 생성하세요.")

url = st.text_input("블로그 URL", placeholder="https://blog.naver.com/...")
st.caption("사진과 본문은 사용 권한이 있는 게시물을 입력하세요. 사진 매칭을 위해 축소 이미지도 선택한 AI로 전송합니다.")

if st.button("숏폼 생성", type="primary", disabled=not can_generate):
    if not url.strip():
        st.warning("블로그 URL을 입력해주세요.")
    else:
        progress = st.progress(0.0)
        status = st.empty()

        def on_progress(step, total, message):
            progress.progress(min((step - 1) / total, .99))
            status.info(message)

        try:
            result = Pipeline(
                progress_callback=on_progress,
                preset=preset,
                speed=speed,
            ).run(url.strip())
            st.session_state["result"] = {
                "video": str(result.video_path),
                "run": str(result.work_dir),
                "script": result.short_script.script,
                "elapsed": result.elapsed_seconds,
            }
            progress.progress(1.0)
            status.success("영상 생성 및 파일 검증 완료")
        except Exception as exc:
            status.error(safe_error(exc))

result = st.session_state.get("result")
if result:
    st.subheader("생성 결과")
    st.video(result["video"])
    st.write(f"처리 시간: {result['elapsed']:.1f}초")
    with st.expander("대본"):
        st.write(result["script"])
    video = Path(result["video"])
    st.download_button(
        "MP4 저장",
        video.read_bytes(),
        file_name=video.name,
        mime="video/mp4",
    )
    if st.button("같은 음성·사진으로 화면만 다시 렌더링"):
        try:
            with st.spinner("외부 API 호출 없이 화면 다시 만드는 중"):
                result["video"] = str(rerender(result["run"]))
            st.rerun()
        except Exception as exc:
            st.error(safe_error(exc))
