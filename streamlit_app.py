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
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
    :root {
      --ink: #151922;
      --muted: #6b7280;
      --line: #e8ebf0;
      --soft: #f7f8fb;
      --accent: #ff4d4f;
    }
    .stApp {
      background:
        radial-gradient(circle at 8% 4%, rgba(255,77,79,.08), transparent 26%),
        radial-gradient(circle at 92% 8%, rgba(89,126,247,.09), transparent 24%),
        #ffffff;
    }
    .block-container {
      max-width: 1200px;
      padding-top: 1.8rem;
      padding-bottom: 4rem;
    }
    [data-testid="stSidebar"] {display: none;}

    .topbar {
      display:flex;
      align-items:center;
      justify-content:space-between;
      padding:.35rem 0 1.2rem;
    }
    .brand {
      display:flex;
      align-items:center;
      gap:.7rem;
      font-weight:800;
      font-size:1.1rem;
      letter-spacing:-.02em;
    }
    .brand-mark {
      width:30px;height:30px;border-radius:10px;
      display:grid;place-items:center;
      background:linear-gradient(135deg,#ff5f5f,#ff8a5c);
      color:white;font-size:.82rem;font-weight:900;
      box-shadow:0 8px 20px rgba(255,77,79,.22);
    }
    .beta {
      font-size:.7rem;font-weight:800;padding:4px 8px;border-radius:999px;
      background:#fff0f0;color:#ef4444;border:1px solid #ffdada;
    }

    .eyebrow {
      display:inline-flex;
      align-items:center;
      gap:.45rem;
      padding:6px 10px;
      border:1px solid #e9dcdc;
      background:rgba(255,255,255,.82);
      border-radius:999px;
      font-size:.78rem;
      font-weight:700;
      color:#b43d3f;
      margin-bottom:1rem;
    }
    .hero-copy h1 {
      font-size:3.72rem;
      line-height:1.03;
      letter-spacing:-.055em;
      margin:.1rem 0 1rem;
      color:var(--ink);
    }
    .hero-copy .accent {color:#ff4d4f;}
    .hero-copy p {
      color:var(--muted);
      font-size:1.08rem;
      line-height:1.7;
      max-width:610px;
      margin:0 0 1.2rem;
    }
    .trust-row {
      display:flex;flex-wrap:wrap;gap:.55rem;margin-top:.85rem;
    }
    .trust-chip {
      padding:7px 10px;border-radius:999px;background:#f6f7f9;
      border:1px solid #eceef2;color:#4b5563;font-size:.78rem;font-weight:700;
    }

    .preview-shell {
      min-height:510px;
      border:1px solid rgba(226,230,238,.9);
      border-radius:28px;
      background:
        radial-gradient(circle at 30% 10%, rgba(255,196,196,.45), transparent 32%),
        radial-gradient(circle at 85% 25%, rgba(173,200,255,.45), transparent 30%),
        linear-gradient(180deg,#fbfcff,#f5f7fb);
      position:relative;
      overflow:hidden;
      padding:26px;
      box-shadow:0 26px 70px rgba(29,36,50,.10);
    }
    .floating-note {
      position:absolute;
      top:28px;left:24px;
      background:white;border:1px solid #eceef2;border-radius:14px;
      padding:10px 12px;box-shadow:0 10px 30px rgba(30,35,45,.08);
      font-size:.78rem;font-weight:750;color:#394150;
    }
    .phone {
      width:245px;height:430px;
      border:8px solid #171b24;
      border-radius:34px;
      background:#111827;
      position:absolute;
      right:35px;top:42px;
      box-shadow:0 28px 55px rgba(17,24,39,.25);
      overflow:hidden;
    }
    .phone-notch {
      width:82px;height:18px;border-radius:0 0 12px 12px;
      background:#171b24;margin:0 auto;
    }
    .video-scene {
      height:260px;
      background:
        linear-gradient(180deg,rgba(17,24,39,.05),rgba(17,24,39,.12)),
        linear-gradient(135deg,#f4b38a,#f26b5b 42%,#603b68 100%);
      position:relative;
    }
    .plate {
      width:125px;height:125px;border-radius:50%;
      background:#f7ead7;border:8px solid rgba(255,255,255,.85);
      position:absolute;left:52px;top:62px;
      box-shadow:0 10px 30px rgba(68,41,34,.18);
    }
    .food {
      width:88px;height:70px;border-radius:48% 52% 44% 56%;
      background:linear-gradient(135deg,#8e4c2d,#d09255);
      position:absolute;left:71px;top:88px;
    }
    .caption-box {
      position:absolute;left:16px;right:16px;bottom:14px;
      background:rgba(8,12,20,.78);backdrop-filter:blur(10px);
      color:white;border-radius:12px;padding:10px 12px;
      font-weight:850;font-size:.86rem;line-height:1.45;text-align:center;
    }
    .phone-lower {padding:18px 16px;color:#e5e7eb;}
    .phone-kicker {color:#ffbe9b;font-size:.68rem;font-weight:800;}
    .phone-title {font-size:1.02rem;font-weight:850;margin-top:5px;line-height:1.35;}
    .timeline {
      height:5px;border-radius:999px;background:#303846;margin-top:18px;overflow:hidden;
    }
    .timeline > div {height:100%;width:64%;background:#ff6b6b;border-radius:999px;}
    .phone-meta {font-size:.68rem;color:#aeb6c4;margin-top:10px;display:flex;justify-content:space-between;}

    .mini-card {
      position:absolute;
      left:28px;bottom:32px;
      width:185px;
      border-radius:18px;background:rgba(255,255,255,.96);
      border:1px solid #e8ebf0;
      padding:14px;
      box-shadow:0 18px 42px rgba(30,35,45,.10);
    }
    .mini-card b {font-size:.82rem;}
    .mini-line {height:7px;border-radius:999px;background:#edf0f4;margin-top:9px;}
    .mini-line.short {width:68%;}

    .section {
      margin-top:2rem;
      padding-top:1.4rem;
    }
    .section-head {
      display:flex;align-items:flex-start;justify-content:space-between;gap:2rem;
      margin-bottom:1rem;
    }
    .section-kicker {
      color:#ef4444;font-size:.74rem;font-weight:850;letter-spacing:.08em;
      margin-bottom:.35rem;
    }
    .section-title {
      font-size:1.65rem;font-weight:850;letter-spacing:-.035em;color:var(--ink);
    }
    .section-copy {
      color:var(--muted);font-size:.9rem;line-height:1.55;
      max-width:360px;text-align:right;padding-top:.25rem;
    }

    .panel {
      border:1px solid var(--line);
      background:rgba(255,255,255,.94);
      border-radius:22px;
      padding:20px;
      box-shadow:0 10px 32px rgba(30,35,45,.045);
    }
    .style-card {
      border:1px solid var(--line);
      background:#fff;
      border-radius:18px;
      padding:15px 16px;
      min-height:118px;
    }
    .style-card b {font-size:1rem;color:var(--ink);}
    .style-card p {margin:.45rem 0 0;color:var(--muted);font-size:.86rem;line-height:1.5;}
    .style-icon {font-size:1.2rem;margin-bottom:.55rem;}
    .voice-feature {
      display:flex;gap:.8rem;align-items:center;
      border:1px solid var(--line);border-radius:18px;padding:15px 16px;background:#fff;
    }
    .voice-dot {
      width:40px;height:40px;border-radius:50%;
      background:linear-gradient(135deg,#ff6969,#ffc27a);
      display:grid;place-items:center;color:white;font-weight:900;
    }
    .voice-feature b {display:block;font-size:.96rem;}
    .voice-feature span {color:var(--muted);font-size:.82rem;}

    .flow-strip {
      display:grid;grid-template-columns:repeat(4,1fr);gap:10px;
      margin-top:1rem;
    }
    .flow-item {
      border:1px solid #eceef2;background:#fafbfc;border-radius:14px;
      padding:12px 13px;
    }
    .flow-item small {color:#ef4444;font-weight:850;}
    .flow-item b {display:block;margin-top:4px;font-size:.88rem;}

    .ready-box {
      border-radius:18px;padding:17px 18px;
      background:linear-gradient(135deg,#fff8f7,#f6f9ff);
      border:1px solid #e8ebf0;
    }
    .ready-box strong {font-size:1rem;}
    .ready-box span {color:#687183;font-size:.85rem;line-height:1.5;}

    .st-key-hero_preview {
      min-height:500px;
      border:1px solid rgba(226,230,238,.9);
      border-radius:28px;
      background:
        radial-gradient(circle at 30% 10%, rgba(255,196,196,.40), transparent 32%),
        radial-gradient(circle at 85% 25%, rgba(173,200,255,.42), transparent 30%),
        linear-gradient(180deg,#fbfcff,#f5f7fb);
      padding:22px 24px 26px;
      box-shadow:0 26px 70px rgba(29,36,50,.10);
    }
    .st-key-hero_preview [data-testid="stVideo"] {
      width:250px !important;
      max-width:250px !important;
      margin:10px auto 0;
      border:8px solid #171b24;
      border-radius:34px;
      overflow:hidden;
      background:#111827;
      box-shadow:0 28px 55px rgba(17,24,39,.24);
    }
    .st-key-hero_preview [data-testid="stVideo"] video {
      aspect-ratio:9 / 16;
      object-fit:cover;
      background:#111827;
    }
    .live-preview-label {
      display:inline-flex;align-items:center;gap:.4rem;
      padding:8px 11px;border-radius:12px;background:rgba(255,255,255,.94);
      border:1px solid #e8ebf0;font-size:.78rem;font-weight:800;color:#394150;
      box-shadow:0 8px 24px rgba(30,35,45,.07);
    }
    .live-preview-meta {
      text-align:center;color:#7a8291;font-size:.76rem;margin-top:.55rem;
    }

    @media (max-width: 850px) {
      .hero-copy h1 {font-size:2.65rem;}
      .preview-shell {min-height:430px;margin-top:1rem;}
      .phone {transform:scale(.86);transform-origin:top right;right:18px;}
      .flow-strip {grid-template-columns:repeat(2,1fr);}
      .section-head {display:block;}
      .section-copy {max-width:none;text-align:left;margin-top:.5rem;}
      .st-key-hero_preview {min-height:auto;margin-top:1rem;}
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="topbar">
      <div class="brand"><div class="brand-mark">AS</div>AutoShorts <span class="beta">BETA</span></div>
      <div style="font-size:.82rem;color:#7a8291;font-weight:650;">BLOG → SHORTS</div>
    </div>
    """,
    unsafe_allow_html=True,
)

script_ready = bool(settings.active_api_key)
tts_ready = bool(settings.active_tts_api_key)
can_generate = script_ready and tts_ready

STYLE_OPTIONS = {
    "맛집·체험": {
        "preset": "food_vlog",
        "icon": "🍜",
        "description": "방문 경험과 핵심 포인트를 빠르게 보여주는 리뷰형",
    },
    "제품 리뷰": {
        "preset": "bright",
        "icon": "📦",
        "description": "제품의 특징과 사용감을 짧고 경쾌하게 설명",
    },
    "여행·일상": {
        "preset": "bright",
        "icon": "🧳",
        "description": "사진 흐름을 살린 가볍고 편안한 브이로그형",
    },
    "정보형": {
        "preset": "calm",
        "icon": "💡",
        "description": "핵심 정보를 차분하고 또렷하게 전달",
    },
}

def latest_generated_video() -> Path | None:
    """Use the newest real AutoShorts render for the hero preview when available."""
    result = st.session_state.get("result")
    if isinstance(result, dict):
        current = Path(result.get("video", ""))
        if current.is_file() and current.suffix.lower() == ".mp4":
            return current

    output_dir = Path("output")
    if not output_dir.exists():
        return None

    candidates = [
        path for path in output_dir.rglob("*.mp4")
        if path.is_file()
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda path: path.stat().st_mtime)


if not can_generate:
    st.info("현재 로컬 개발 설정에서 음성/대본 API 연결을 확인해주세요.")

hero_left, hero_right = st.columns([1.04, .96], gap="large", vertical_alignment="center")

with hero_left:
    st.markdown(
        """
        <div class="hero-copy">
          <div class="eyebrow">AI BLOG TO SHORTS</div>
          <h1>블로그 하나면,<br><span class="accent">쇼츠 초안까지 한 번에.</span></h1>
          <p>본문을 읽고, 사진을 고르고, 대본·음성·자막까지 자동으로 구성합니다.
          복잡한 편집 없이 링크부터 시작하세요.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    url = st.text_input(
        "블로그 URL",
        placeholder="https://blog.naver.com/...",
        label_visibility="collapsed",
    )
    st.caption("네이버 · 티스토리 · 일반 웹페이지 지원")

    st.markdown(
        """
        <div class="trust-row">
          <span class="trust-chip">60초 미만</span>
          <span class="trust-chip">9:16 세로 영상</span>
          <span class="trust-chip">대본 자동 생성</span>
          <span class="trust-chip">사진 자동 매칭</span>
          <span class="trust-chip">한국어 자막</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

with hero_right:
    live_video = latest_generated_video()
    if live_video:
        with st.container(key="hero_preview"):
            st.markdown(
                '<div class="live-preview-label">▶ 실제 AutoShorts 생성 영상</div>',
                unsafe_allow_html=True,
            )
            st.video(
                str(live_video),
                autoplay=True,
                muted=True,
                loop=True,
            )
            st.markdown(
                '<div class="live-preview-meta">최근 생성된 실제 결과물을 자동으로 보여줍니다.</div>',
                unsafe_allow_html=True,
            )
    else:
        st.markdown(
            """
            <div class="preview-shell">
              <div class="floating-note">✨ 결과물 미리보기</div>
              <div class="phone">
                <div class="phone-notch"></div>
                <div class="video-scene">
                  <div class="plate"></div>
                  <div class="food"></div>
                  <div class="caption-box">쇼츠를 한 번 생성하면<br>실제 결과가 여기에 재생돼요.</div>
                </div>
                <div class="phone-lower">
                  <div class="phone-kicker">AUTO SHORTS</div>
                  <div class="phone-title">블로그 사진과 글이<br>세로형 리뷰 영상으로</div>
                  <div class="timeline"><div></div></div>
                  <div class="phone-meta"><span>PREVIEW</span><span>9:16</span></div>
                </div>
              </div>
              <div class="mini-card">
                <b>첫 영상 생성 후</b>
                <div class="mini-line"></div>
                <div class="mini-line short"></div>
                <div style="margin-top:10px;font-size:.73rem;color:#687183;">이 영역이 실제 영상으로 교체됩니다.</div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

st.markdown('<div class="section">', unsafe_allow_html=True)
st.markdown(
    """
    <div class="section-head">
      <div>
        <div class="section-kicker">STYLE</div>
        <div class="section-title">어떤 느낌의 쇼츠로 만들까요?</div>
      </div>
      <div class="section-copy">콘텐츠 성격에 맞게 대본 톤과 사진 흐름이 달라집니다.</div>
    </div>
    """,
    unsafe_allow_html=True,
)

style_name = st.radio(
    "영상 스타일",
    list(STYLE_OPTIONS),
    horizontal=True,
    label_visibility="collapsed",
)
style = STYLE_OPTIONS[style_name]
preset = style["preset"]

style_cols = st.columns(4)
for idx, (name, option) in enumerate(STYLE_OPTIONS.items()):
    with style_cols[idx]:
        active = name == style_name
        st.markdown(
            f"""
            <div class="style-card" style="border-color:{'#ffb1b1' if active else '#e8ebf0'};background:{'#fff8f8' if active else '#fff'};">
              <div class="style-icon">{option["icon"]}</div>
              <b>{name}</b>
              <p>{option["description"]}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
st.markdown('</div>', unsafe_allow_html=True)

st.markdown('<div class="section">', unsafe_allow_html=True)
st.markdown(
    """
    <div class="section-head">
      <div>
        <div class="section-kicker">VOICE</div>
        <div class="section-title">목소리는 간단하게.</div>
      </div>
      <div class="section-copy">기본 한국어 쇼츠 음성은 하나로 유지하고 속도만 가볍게 조절합니다.</div>
    </div>
    """,
    unsafe_allow_html=True,
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

    # Keep the selected voice opaque to the end user; provider changes should not alter the UI.

with st.container(border=True):
    voice_col, control_col = st.columns([1.38, .62], gap="large", vertical_alignment="center")

    with voice_col:
        st.markdown(
            """
            <div class="voice-feature">
              <div class="voice-dot">▶</div>
              <div><b>자연스러운 한국어 쇼츠 음성</b><span>한 가지 기본 음성으로 일관된 결과물을 만듭니다.</span></div>
            </div>
            """,
            unsafe_allow_html=True,
        )
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

    with control_col:
        speed = st.slider(
            "말하기 속도",
            min_value=.96,
            max_value=1.16,
            value=1.08,
            step=.02,
            help="쇼츠에 맞게 기본값을 조금 빠르게 설정했습니다.",
        )

st.markdown('</div>', unsafe_allow_html=True)

st.markdown(
    """
    <div class="flow-strip">
      <div class="flow-item"><small>01</small><b>본문 분석</b></div>
      <div class="flow-item"><small>02</small><b>사진 매칭</b></div>
      <div class="flow-item"><small>03</small><b>대본·음성</b></div>
      <div class="flow-item"><small>04</small><b>자막·렌더링</b></div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown('<div class="section">', unsafe_allow_html=True)
st.markdown(
    """
    <div class="section-head">
      <div>
        <div class="section-kicker">CREATE</div>
        <div class="section-title">준비됐어요.</div>
      </div>
      <div class="section-copy">링크와 스타일만 확인하고 바로 생성하세요.</div>
    </div>
    """,
    unsafe_allow_html=True,
)

ready = can_generate and bool(url.strip())
st.markdown(
    f"""
    <div class="ready-box">
      <strong>{style_name} · 한국어 음성</strong><br>
      <span>60초 미만 · 1080×1920 · 사진 자동 구성 · 대본/자막 자동 생성</span>
    </div>
    """,
    unsafe_allow_html=True,
)

if st.button(
    "쇼츠 만들기",
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

st.markdown('</div>', unsafe_allow_html=True)

result = st.session_state.get("result")
if result:
    st.markdown('<div class="section">', unsafe_allow_html=True)
    st.markdown(
        """
        <div class="section-head">
          <div>
            <div class="section-kicker">RESULT</div>
            <div class="section-title">완성된 숏폼</div>
          </div>
          <div class="section-copy">바로 확인하고 저장하거나 화면만 다시 만들 수 있습니다.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    result_left, result_right = st.columns([1.15, .85], gap="large")
    with result_left:
        st.video(result["video"])
    with result_right:
        st.markdown('<div class="panel">', unsafe_allow_html=True)
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

        with st.expander("대본 보기"):
            st.write(result["script"])

        if st.button("화면만 다시 만들기", use_container_width=True):
            try:
                with st.spinner("화면을 다시 구성하는 중"):
                    result["video"] = str(rerender(result["run"]))
                st.rerun()
            except Exception as exc:
                st.error(safe_error(exc))
        st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
