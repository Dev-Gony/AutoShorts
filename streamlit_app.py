from __future__ import annotations

from pathlib import Path

import streamlit as st

from config import settings
from src.pipeline import Pipeline, rerender
from src.preview import preview_voice, safe_error
from src.typecast_voices import (
    POPULAR_SHORTS_VOICES,
    recommend_typecast_voices,
    resolve_popular_typecast_voice,
)
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
    speed = st.slider("말하기 속도", min_value=.9, max_value=1.2, value=1.10, step=.02)

    st.caption(f"대본/사진 분석: {settings.ai_provider}")
    selected_voice_id = settings.typecast_voice_id or st.session_state.get("chosen_voice_id")

    if settings.tts_provider == "typecast":
        st.caption(f"음성: Typecast · {settings.typecast_model}")
        popular_tab, recommend_tab = st.tabs(["인기 쇼츠 보이스", "AI 추천"])

        with popular_tab:
            popular_names = list(POPULAR_SHORTS_VOICES)
            popular_name = st.radio(
                "Typecast 인기 캐릭터",
                popular_names,
                key="popular_voice_name",
            )
            popular = POPULAR_SHORTS_VOICES[popular_name]
            st.caption(popular.note)
            st.caption(popular.source_note)
            st.caption(f"권장 시작 속도: {popular.recommended_speed:.2f}")

            if st.button(
                "이 인기 보이스 불러오기",
                disabled=not tts_ready,
                key="load_popular_voice",
            ):
                try:
                    with st.spinner(f"{popular_name} voice_id 확인 중"):
                        candidate = resolve_popular_typecast_voice(popular_name)
                    st.session_state["popular_candidate"] = candidate
                    st.session_state["chosen_voice_id"] = candidate.voice_id
                    st.session_state["chosen_voice_label"] = candidate.name
                    st.session_state.pop("voice_preview", None)
                except Exception as exc:
                    st.error(safe_error(exc))

            candidate = st.session_state.get("popular_candidate")
            if candidate and candidate.name == popular_name:
                selected_voice_id = candidate.voice_id
                st.success(f"선택됨: {candidate.label}")
                if candidate.preview_url:
                    st.audio(candidate.preview_url)
                    st.caption("Typecast 제공 기본 샘플")

                if st.button(
                    "이 보이스로 AutoShorts 문장 듣기",
                    key="preview_popular_voice",
                ):
                    try:
                        with st.spinner("실제 AutoShorts 문장 생성 중"):
                            path = preview_voice(
                                preset,
                                speed,
                                voice_id=candidate.voice_id,
                            )
                        st.session_state["voice_preview"] = str(path)
                    except Exception as exc:
                        st.error(safe_error(exc))

        with recommend_tab:
            st.caption("인기 캐릭터가 마음에 안 들 때만 일반 추천 후보를 비교하세요.")
            if st.button(
                "쇼츠용 보이스 추천받기",
                disabled=not tts_ready,
                key="recommend_voices",
            ):
                try:
                    with st.spinner("Typecast 추천 보이스 찾는 중"):
                        candidates = recommend_typecast_voices(preset, limit=5)
                    st.session_state["typecast_candidates"] = candidates
                    st.session_state.pop("voice_preview", None)
                except Exception as exc:
                    st.error(safe_error(exc))

            candidates = st.session_state.get("typecast_candidates", [])
            if candidates:
                labels = {item.voice_id: item.label for item in candidates}
                recommended_id = st.radio(
                    "추천 보이스",
                    [item.voice_id for item in candidates],
                    format_func=lambda vid: labels[vid],
                    key="recommended_voice_id",
                )
                selected = next(
                    item for item in candidates if item.voice_id == recommended_id
                )
                if st.button(
                    "이 추천 보이스 사용",
                    key="use_recommended_voice",
                ):
                    st.session_state["chosen_voice_id"] = selected.voice_id
                    st.session_state["chosen_voice_label"] = selected.name
                    st.session_state["popular_candidate"] = None
                if st.button(
                    "추천 보이스로 같은 문장 듣기",
                    key="preview_recommended_voice",
                ):
                    try:
                        with st.spinner("선택 보이스 샘플 생성 중"):
                            path = preview_voice(
                                preset,
                                speed,
                                voice_id=selected.voice_id,
                            )
                        st.session_state["voice_preview"] = str(path)
                    except Exception as exc:
                        st.error(safe_error(exc))

        selected_voice_id = settings.typecast_voice_id or st.session_state.get("chosen_voice_id")
        chosen_label = st.session_state.get("chosen_voice_label")
        if selected_voice_id:
            st.info(f"전체 영상 사용 보이스: {chosen_label or selected_voice_id}")

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

    st.caption("인기 쇼츠 보이스를 먼저 비교하고, 마음에 드는 음성을 고른 뒤 전체 영상을 생성하세요.")

url = st.text_input("블로그 URL", placeholder="https://blog.naver.com/...")
st.caption("사진과 본문은 사용 권한이 있는 게시물을 입력하세요. 사진 매칭을 위해 축소 이미지도 선택한 AI로 전송합니다.")

if st.button("숏폼 생성", type="primary", disabled=not can_generate):
    if not url.strip():
        st.warning("블로그 URL을 입력해주세요.")
    elif settings.tts_provider == "typecast" and not selected_voice_id:
        st.warning("먼저 Typecast 보이스를 선택해주세요.")
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
