from __future__ import annotations

from pathlib import Path

import streamlit as st

from config import settings
from src.pipeline import Pipeline, rerender
from src.preview import preview_voice, safe_error
from src.typecast_voices import top_korean_shorts_voices

st.set_page_config(
    page_title="AutoShorts",
    page_icon="🎬",
    layout="centered",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
    .block-container {
        max-width: 860px;
        padding-top: 3rem;
        padding-bottom: 5rem;
    }
    [data-testid="stSidebar"] {display: none;}
    .hero {
        text-align: center;
        padding: 1.5rem 0 2.2rem;
    }
    .hero h1 {
        font-size: 3rem;
        margin: 0 0 .55rem;
        letter-spacing: -.04em;
    }
    .hero p {
        margin: 0;
        color: #6b7280;
        font-size: 1.08rem;
    }
    .step {
        margin-top: 1.25rem;
        font-size: .78rem;
        font-weight: 800;
        letter-spacing: .08em;
        color: #ef4444;
    }
    .soft-card {
        border: 1px solid #e5e7eb;
        border-radius: 18px;
        padding: 18px 20px;
        background: #fff;
        margin-bottom: .75rem;
    }
    .soft-card strong {font-size: 1.02rem;}
    .soft-card p {
        color: #6b7280;
        margin: .4rem 0 0;
        font-size: .92rem;
    }
    .ready-box {
        border-radius: 18px;
        padding: 18px 20px;
        background: #f8fafc;
        border: 1px solid #e5e7eb;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="hero">
      <h1>AutoShorts</h1>
      <p>블로그 링크 하나로 60초 안의 세로형 숏폼을 자동으로 만듭니다.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

script_ready = bool(settings.active_api_key)
tts_ready = bool(settings.active_tts_api_key)
can_generate = script_ready and tts_ready

STYLE_OPTIONS = {
    "맛집·체험 리뷰": {
        "preset": "food_vlog",
        "description": "방문 경험과 핵심 포인트를 빠르게 보여주는 리뷰형",
    },
    "제품 리뷰": {
        "preset": "bright",
        "description": "제품의 특징과 사용감을 짧고 경쾌하게 설명",
    },
    "여행·일상": {
        "preset": "bright",
        "description": "사진 흐름을 살린 가볍고 편안한 브이로그형",
    },
    "정보형": {
        "preset": "calm",
        "description": "핵심 정보를 차분하고 또렷하게 전달",
    },
}

if not can_generate:
    st.info("현재 로컬 개발 설정에서 음성/대본 API 연결을 확인해주세요.")

st.markdown('<div class="step">STEP 1</div>', unsafe_allow_html=True)
st.subheader("블로그 링크")
url = st.text_input(
    "블로그 URL",
    placeholder="https://blog.naver.com/...",
    label_visibility="collapsed",
)
st.caption("네이버 · 티스토리 · 일반 웹페이지를 지원합니다.")

st.divider()

st.markdown('<div class="step">STEP 2</div>', unsafe_allow_html=True)
st.subheader("영상 스타일")
style_name = st.radio(
    "영상 스타일",
    list(STYLE_OPTIONS),
    horizontal=True,
    label_visibility="collapsed",
)
style = STYLE_OPTIONS[style_name]
preset = style["preset"]
st.markdown(
    f"""
    <div class="soft-card">
      <strong>{style_name}</strong>
      <p>{style["description"]}</p>
    </div>
    """,
    unsafe_allow_html=True,
)

st.divider()

st.markdown('<div class="step">STEP 3</div>', unsafe_allow_html=True)
st.subheader("목소리")
st.markdown(
    """
    <div class="soft-card">
      <strong>자연스러운 한국어 쇼츠 음성</strong>
      <p>서비스 기본 목소리 1개를 사용합니다. 음성 엔진이나 모델명은 사용자가 신경 쓰지 않아도 됩니다.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

speed = st.slider(
    "말하기 속도",
    min_value=.96,
    max_value=1.16,
    value=1.08,
    step=.02,
    help="쇼츠에 맞게 기본값을 조금 빠르게 설정했습니다.",
)

def resolve_service_voice() -> str:
    existing = st.session_state.get("service_voice_id")
    existing_preset = st.session_state.get("service_voice_preset")
    if existing and existing_preset == preset:
        return existing

    candidates = top_korean_shorts_voices(preset=preset, limit=1)
    if not candidates:
        raise RuntimeError("현재 사용할 수 있는 한국어 음성을 찾지 못했습니다.")

    voice = candidates[0]
    st.session_state["service_voice_id"] = voice.voice_id
    st.session_state["service_voice_preset"] = preset
    st.session_state["service_voice_name"] = voice.name
    return voice.voice_id


if st.button("목소리 미리듣기", disabled=not tts_ready):
    try:
        with st.spinner("한국어 음성 샘플을 만드는 중"):
            voice_id = resolve_service_voice()
            path = preview_voice(preset, speed, voice_id=voice_id)
        st.session_state["service_preview"] = str(path)
    except Exception as exc:
        st.error(safe_error(exc))

if st.session_state.get("service_preview"):
    st.audio(st.session_state["service_preview"])

st.divider()

st.markdown('<div class="step">STEP 4</div>', unsafe_allow_html=True)
st.subheader("숏폼 만들기")

ready = can_generate and bool(url.strip())
st.markdown(
    f"""
    <div class="ready-box">
      <strong>{style_name}</strong><br>
      <span>목표 길이: 60초 미만 · 세로형 1080×1920 · 한국어 음성</span>
    </div>
    """,
    unsafe_allow_html=True,
)

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
        voice_id = resolve_service_voice()
        result = Pipeline(
            progress_callback=on_progress,
            preset=preset,
            speed=speed,
            voice_id=voice_id,
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
    st.markdown('<div class="step">RESULT</div>', unsafe_allow_html=True)
    st.subheader("완성된 숏폼")
    st.video(result["video"])

    info_a, info_b = st.columns(2)
    info_a.metric("처리 시간", f"{result['elapsed']:.1f}초")
    info_b.metric("영상 형식", "1080 × 1920")

    video = Path(result["video"])
    st.download_button(
        "MP4 저장",
        video.read_bytes(),
        file_name=video.name,
        mime="video/mp4",
        use_container_width=True,
    )

    col_a, col_b = st.columns(2)
    with col_a:
        with st.expander("대본 보기"):
            st.write(result["script"])
    with col_b:
        if st.button("화면만 다시 만들기", use_container_width=True):
            try:
                with st.spinner("화면을 다시 구성하는 중"):
                    result["video"] = str(rerender(result["run"]))
                st.rerun()
            except Exception as exc:
                st.error(safe_error(exc))
