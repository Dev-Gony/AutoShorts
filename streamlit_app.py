from __future__ import annotations

from pathlib import Path

import streamlit as st

from config import settings
from src.pipeline import Pipeline, rerender
from src.preview import preview_voice, safe_error
from src.typecast_voices import recommend_typecast_voices
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

    selected_voice_id = settings.typecast_voice_id or None

    if settings.tts_provider == "typecast":
        st.caption(f"음성: Typecast · {settings.typecast_model}")
        st.caption("추천 후보를 비교한 뒤 전체 영상에 사용할 보이스를 고정합니다.")

        if st.button("쇼츠용 보이스 추천받기", disabled=not tts_ready):
            try:
                with st.spinner("Typecast 추천 보이스 찾는 중"):
                    candidates = recommend_typecast_voices(preset, limit=5)
                st.session_state["typecast_candidates"] = candidates
                st.session_state.pop("voice_preview", None)
                st.session_state.pop("selected_voice_id", None)
            except Exception as exc:
                st.error(safe_error(exc))

        candidates = st.session_state.get("typecast_candidates", [])
        if candidates:
            labels = {item.voice_id: item.label for item in candidates}
            selected_voice_id = st.radio(
                "추천 보이스",
                [item.voice_id for item in candidates],
                format_func=lambda vid: labels[vid],
                key="selected_voice_id",
            )
            selected = next(
                item for item in candidates if item.voice_id == selected_voice_id
            )
            st.caption(f"선택됨: {selected.label}")

            if selected.preview_url:
                st.audio(selected.preview_url)
                st.caption("Typecast 제공 기본 샘플")
            if st.button("선택 보이스로 같은 문장 들어보기"):
                try:
                    with st.spinner("선택 보이스 샘플 생성 중"):
                        path = preview_voice(
                            preset,
                            speed,
                            voice_id=selected_voice_id,
                        )
                    st.session_state["voice_preview"] = str(path)
                except Exception as exc:
                    st.error(safe_error(exc))
        else:
            st.caption("먼저 추천 보이스 5개를 받아 비교해보세요.")

        if st.session_state.get("voice_preview"):
            st.audio(st.session_state["voice_preview"])
            st.caption("실제 AutoShorts 문장으로 생성한 샘플")

    else:
        st.caption(f"음성: {settings.tts_provider}")
        if st.button("짧은 음성 먼저 듣기", disabled=not tts_ready):
            try:
                with st.spinner("음성 샘플 생성 중"):
                    path = preview_voice(preset, speed)
                st.session_state["voice_preview"] = str(path)
            except Exception as exc:
                st.error(safe_error(exc))
        if st.session_state.get("voice_preview"):
            st.audio(st.session_state["voice_preview"])

    if not tts_ready:
        st.error(f"{settings.tts_provider.upper()} TTS API 키가 필요합니다.")
    if not script_ready:
        st.error(f"{settings.ai_provider.upper()} 대본 생성 API 키가 필요합니다.")

    st.caption("먼저 음색을 고르고, 그 다음 전체 영상을 생성하세요.")

url = st.text_input("블로그 URL", placeholder="https://blog.naver.com/...")
st.caption("사진과 본문은 사용 권한이 있는 게시물을 입력하세요. 사진 매칭을 위해 축소 이미지도 선택한 AI로 전송합니다.")

if st.button("숏폼 생성", type="primary", disabled=not can_generate):
    if not url.strip():
        st.warning("블로그 URL을 입력해주세요.")
    elif settings.tts_provider == "typecast" and not selected_voice_id:
        st.warning("먼저 Typecast 추천 보이스를 선택해주세요.")
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
                voice_id=selected_voice_id,
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
