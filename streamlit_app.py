from __future__ import annotations

from pathlib import Path

import streamlit as st

from config import settings
from src.pipeline import Pipeline, rerender
from src.preview import preview_voice, safe_error
from src.typecast_voices import browse_typecast_voices, top_shorts_voices
from src.voices import PROFILES, selected_profile

st.set_page_config(
    page_title="AutoShorts",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
    .block-container {max-width: 1180px; padding-top: 2.5rem; padding-bottom: 4rem;}
    [data-testid="stSidebar"] {display: none;}
    .hero {padding: 1.2rem 0 1.8rem 0;}
    .hero h1 {font-size: 2.6rem; margin-bottom: .35rem;}
    .hero p {font-size: 1.05rem; color: #6b7280; margin: 0;}
    .step-label {font-size: .82rem; font-weight: 700; color: #ef4444; letter-spacing: .04em;}
    .voice-card {
        border: 1px solid #e5e7eb; border-radius: 16px; padding: 14px 16px;
        min-height: 150px; background: white;
    }
    .voice-card strong {font-size: 1.05rem;}
    .voice-meta {color:#6b7280; font-size:.88rem; margin-top:.25rem;}
    .chip {
        display:inline-block; padding:3px 8px; margin:4px 4px 0 0;
        border-radius:999px; background:#f3f4f6; font-size:.76rem; color:#4b5563;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="hero">
      <h1>AutoShorts</h1>
      <p>블로그 URL 하나로 사진·대본·음성·자막을 묶어 세로형 숏폼을 만듭니다.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

script_ready = bool(settings.active_api_key)
tts_ready = bool(settings.active_tts_api_key)
can_generate = script_ready and tts_ready

if not script_ready or not tts_ready:
    missing = []
    if not script_ready:
        missing.append(f"{settings.ai_provider.upper()} 대본 API 키")
    if not tts_ready:
        missing.append(f"{settings.tts_provider.upper()} TTS API 키")
    st.error("설정이 필요합니다: " + ", ".join(missing))

# STEP 1
st.markdown('<div class="step-label">STEP 1 · SOURCE</div>', unsafe_allow_html=True)
st.subheader("블로그 링크를 넣어주세요")
url = st.text_input(
    "블로그 URL",
    placeholder="https://blog.naver.com/...",
    label_visibility="collapsed",
)
st.caption("현재 네이버·티스토리·일반 HTML을 지원합니다. 사용 권한이 있는 게시물을 입력하세요.")

st.divider()

# STEP 2
st.markdown('<div class="step-label">STEP 2 · VOICE</div>', unsafe_allow_html=True)
st.subheader("쇼츠에 어울리는 목소리를 고르세요")
st.caption("‘인기순’ 데이터는 공개되지 않아, 현재 API에서 사용 가능한 보이스 중 쇼츠/릴스/리뷰 용도 적합도가 높은 순으로 정렬합니다.")

top_col, settings_col = st.columns([3, 1])

with settings_col:
    with st.expander("음성 설정", expanded=True):
        default, _ = selected_profile()
        names = list(PROFILES)
        preset = st.selectbox(
            "말투",
            names,
            index=names.index(default),
            format_func=lambda key: PROFILES[key].label,
        )
        speed = st.slider("말하기 속도", .90, 1.20, 1.10, .02)
        st.caption(f"TTS: Typecast · {settings.typecast_model}")

with top_col:
    if "shorts_top_voices" not in st.session_state and tts_ready:
        try:
            with st.spinner("쇼츠용 보이스를 고르는 중"):
                st.session_state["shorts_top_voices"] = top_shorts_voices(limit=8)
        except Exception as exc:
            st.error(safe_error(exc))
            st.session_state["shorts_top_voices"] = []

    voices = st.session_state.get("shorts_top_voices", [])
    if st.button("추천 보이스 새로고침", disabled=not tts_ready):
        try:
            with st.spinner("Typecast 보이스 다시 불러오는 중"):
                st.session_state["shorts_top_voices"] = top_shorts_voices(limit=8)
            st.rerun()
        except Exception as exc:
            st.error(safe_error(exc))

selected_voice_id = settings.typecast_voice_id or st.session_state.get("chosen_voice_id")
selected_voice_label = st.session_state.get("chosen_voice_label", "")

if voices:
    cols = st.columns(4)
    for index, voice in enumerate(voices):
        with cols[index % 4]:
            tags = "".join(
                f'<span class="chip">{tag}</span>'
                for tag in voice.shorts_tags
            )
            meta = " · ".join(x for x in (voice.gender, voice.age) if x)
            st.markdown(
                f"""
                <div class="voice-card">
                  <strong>#{index + 1} {voice.name}</strong>
                  <div class="voice-meta">{meta or "Typecast API voice"}</div>
                  <div>{tags}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if voice.preview_url:
                st.audio(voice.preview_url)
            if st.button(
                "선택",
                key=f"pick_top_{voice.voice_id}",
                type="primary" if selected_voice_id == voice.voice_id else "secondary",
                use_container_width=True,
            ):
                st.session_state["chosen_voice_id"] = voice.voice_id
                st.session_state["chosen_voice_label"] = voice.name
                selected_voice_id = voice.voice_id
                selected_voice_label = voice.name
                st.session_state.pop("voice_preview", None)
                st.rerun()

    if selected_voice_id:
        st.success(f"선택한 보이스: {selected_voice_label or selected_voice_id}")
        if st.button("선택한 목소리로 4초 미리듣기", use_container_width=False):
            try:
                with st.spinner("미리듣기 생성 중"):
                    path = preview_voice(preset, speed, voice_id=selected_voice_id)
                st.session_state["voice_preview"] = str(path)
            except Exception as exc:
                st.error(safe_error(exc))
        if st.session_state.get("voice_preview"):
            st.audio(st.session_state["voice_preview"])
else:
    st.warning("현재 계정에서 쇼츠 후보 보이스를 불러오지 못했습니다.")

with st.expander("전체 Typecast 보이스 보기 · 고급"):
    search = st.text_input("검색", placeholder="voice name, review, tiktok ...")
    if st.button("전체 보이스 검색"):
        try:
            st.session_state["all_typecast_voices"] = browse_typecast_voices(
                search=search,
                limit=80,
            )
        except Exception as exc:
            st.error(safe_error(exc))
    all_voices = st.session_state.get("all_typecast_voices", [])
    if all_voices:
        labels = {voice.voice_id: voice.label for voice in all_voices}
        advanced_id = st.selectbox(
            "전체 보이스",
            [voice.voice_id for voice in all_voices],
            format_func=lambda vid: labels[vid],
        )
        if st.button("이 보이스 선택"):
            picked = next(v for v in all_voices if v.voice_id == advanced_id)
            st.session_state["chosen_voice_id"] = picked.voice_id
            st.session_state["chosen_voice_label"] = picked.name
            st.session_state.pop("voice_preview", None)
            st.rerun()

st.divider()

# STEP 3
st.markdown('<div class="step-label">STEP 3 · GENERATE</div>', unsafe_allow_html=True)
st.subheader("숏폼 생성")
ready = can_generate and bool(url.strip()) and bool(selected_voice_id)

summary_cols = st.columns(3)
summary_cols[0].metric("소스", "블로그 URL" if url.strip() else "미입력")
summary_cols[1].metric("보이스", selected_voice_label or "미선택")
summary_cols[2].metric("목표 길이", "60초 미만")

if st.button(
    "숏폼 만들기",
    type="primary",
    use_container_width=True,
    disabled=not ready,
):
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
        status.success("영상 생성 완료")
    except Exception as exc:
        status.error(safe_error(exc))

result = st.session_state.get("result")
if result:
    st.divider()
    st.markdown('<div class="step-label">RESULT</div>', unsafe_allow_html=True)
    st.subheader("완성된 숏폼")
    result_left, result_right = st.columns([2, 1])
    with result_left:
        st.video(result["video"])
    with result_right:
        st.metric("처리 시간", f"{result['elapsed']:.1f}초")
        with st.expander("생성된 대본"):
            st.write(result["script"])
        video = Path(result["video"])
        st.download_button(
            "MP4 저장",
            video.read_bytes(),
            file_name=video.name,
            mime="video/mp4",
            use_container_width=True,
        )
        if st.button("화면만 다시 렌더링", use_container_width=True):
            try:
                with st.spinner("API 호출 없이 화면 다시 만드는 중"):
                    result["video"] = str(rerender(result["run"]))
                st.rerun()
            except Exception as exc:
                st.error(safe_error(exc))
