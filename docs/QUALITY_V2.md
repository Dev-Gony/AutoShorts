# AutoShorts: voice and visual quality v2

## What changed and why (2026-09-19)

The earlier output was a basic photo slideshow with un-directed TTS. Its Gemini subtitles used character-count ratios rather than measured speech boundaries. A default-font fix alone did not solve the user's complaints about natural speech, cropped captions and overall short-form presentation.

This revision changes the generation and rendering path together. It is not a claim of parity with a commercial service.

### Voice direction

- `food_vlog`: Puck, conversational restaurant/product review delivery.
- `bright`: Aoede, brighter relaxed vlog delivery.
- `calm`: Sulafat, warm informative delivery.
- `VOICE_SPEED` defaults to 1.06; the supported range is 0.9–1.2. FFmpeg changes tempo without changing pitch.
- The script is rewritten as short, complete spoken scenes instead of formal report-style prose.
- Gemini presets intentionally choose their voice instead of the legacy `GEMINI_TTS_VOICE=Kore` value. OpenAI retains its configured voice and uses the selected delivery instructions where supported.
- Style prompts request emphasis, variation in intonation and phrase-level rhythm. They are model instructions, not a guarantee of naturalness or accent quality.

### Timing

Each short scene is spoken separately. The actual normalized PCM frame count defines that scene's subtitle start/end. An 80ms pause separates utterances. Letter-count timing is removed. This is utterance-level timing, not word-level forced alignment. The model can still pronounce names incorrectly or introduce inconsistencies between utterances; those require listening validation.

### Visual design

- Pixel-measured two-line subtitle cards, bold Korean fonts, rounded translucent backing and a highlighted phrase.
- The glyph bounding box is used when drawing text, so ascenders/descenders are not clipped by a guessed text-image height.
- Captions end at 75% of the frame height, with conservative side margins. This is a project layout choice, not a guarantee for every platform's player overlay.
- The full photo is fitted over a blurred full-frame extension; restrained zoom and short crossfades provide motion without pretending the photos are filmed video.
- The Gemini script planner receives validated 384px thumbnails and chooses an image for each scene. Incorrect matching remains possible.
- Missing/invalid media stops the run before AI generation instead of producing a gray screen.

## Run it on an existing checkout

Keep your current `.env` and API key. Do not overwrite them from `.env.example`.

```bash
git pull --ff-only
python -m pip install -r requirements.txt
python -m streamlit run streamlit_app.py
```

In the sidebar, choose a voice style and use **짧은 음성 먼저 듣기** before generating the full video. The preview makes a real TTS call; it is not a built-in demo recording. Repeating the same sample/settings reuses its cache.

CLI equivalents:

```bash
python app.py --preview-voice --voice food_vlog
python app.py --preview-voice --voice bright
python app.py --voice food_vlog
```

The sample WAV is saved under `output/voice_preview_<preset>.wav`.

For an already completed **v2** run, changing only the visuals does not require more API calls:

```bash
python app.py --rerender latest
```

Older runs without `manifest.json` need one new generation. Existing MP4 files are not modified automatically.

## Fonts

Fonts are not bundled or redistributed. Installed Pretendard Bold/ExtraBold is preferred on Windows, otherwise Malgun Gothic Bold is used. Linux checks Nanum/Noto fonts. Set a local font explicitly when desired:

```env
AUTOSHORTS_FONT=C:/Windows/Fonts/malgunbd.ttf
VOICE_PRESET=food_vlog
VOICE_SPEED=1.06
```

The selected font must support the actual caption glyphs. Unsupported glyphs fail preflight rather than silently becoming boxes. The developer's screenshot-based layout preview uses a locally installed Nanum font; a Windows fallback can look different.

## Costs, limits and verification boundaries

A normal plan uses 6–10 utterances (at most 12), so it makes more TTS requests than the old single-call narration. Model quotas and rate limits may interrupt it, especially on a free tier. Successful utterances are cached by text/model/voice/style/speed; the application does not switch to another paid provider automatically. A newly regenerated script may differ and therefore miss old cache entries.

The 180-second end-to-end target remains a target, not a measured guarantee. Each v2 run records stage timings and `kpi_180s_met` in its manifest. A short renderer benchmark is not an end-to-end benchmark.

Verified separately:

- Unit tests: plan schema, caption bounds, font failure, timing, PCM format, cache and no-media behavior.
- Real render test: an actual MP4 with H.264/AAC, expected dimensions, visible image content, and first/last-frame PNGs.
- SDK contract tests use installed Google SDK configuration objects with mocked responses; they do not call a paid API.
- Local 1080x1920 six-second rendering check: 8.359 seconds in the development environment, using cropped user screenshots and a test tone. It verifies layout/encoding only, not voice quality.
- No live Gemini/OpenAI voice was generated or listened to in the development environment. The supplied input consisted of screenshots, not a playable audio/video file.

## Benchmark references

SuperShorts' public page presents the blog URL → script/caption/voice → vertical short workflow. Its internal TTS provider, proprietary voices and implementation details are not assumed or copied.

- SuperShorts public product/sample page: https://www.supershorts.co.kr/
- Google Gemini speech generation, style control and supported voices: https://ai.google.dev/gemini-api/docs/speech-generation
- Google API rate-limit guidance: https://ai.google.dev/gemini-api/docs/rate-limits
- MoviePy TextClip metrics reference: https://zulko.github.io/moviepy/reference/reference/moviepy.video.VideoClip.TextClip.html

Only owned/licensed source text and photos should be processed. Validated thumbnails are transmitted to the selected AI for scene matching; image downloads, audio caches and generated files remain on the local computer.
