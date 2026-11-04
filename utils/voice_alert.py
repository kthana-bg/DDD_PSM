import base64
import io
import os
import time
import wave

import streamlit as st
from utils.html_embed import embed

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VOICE_DIR = os.path.join(_ROOT, "assets", "voice")
CLIPS_DIR = os.path.join(VOICE_DIR, "clips")
MODEL_PATH = os.path.join(VOICE_DIR, "visionmate-voice.onnx")
DEFAULT_LENGTH_SCALE = 0.92    # below 1.0 speaks a little faster and firmer

DEFAULT_MIN_INTERVAL = 30      # seconds between spoken Warning messages
DANGER_MIN_INTERVAL = 10       # seconds between spoken Danger messages
DEFAULT_VOLUME = 90            # percent

MESSAGES = {
    ("Warning", "eyes"): "Your eyes keep closing. Take a rest soon.",
    ("Warning", "yawn"): "You are yawning too much. Take a rest soon.",
    ("Warning", "nod"): "Your head keeps dropping. Take a rest soon.",
    ("Warning", "mixed"): "You are showing signs of tiredness. Take a rest soon.",
    ("Warning", "hidden"): "I cannot see your face. Sit upright so I can keep watching.",
    ("Danger", "eyes"): "Danger! Your eyes have been closed too long. Pull over safely and rest now!",
    ("Danger", "yawn"): "Danger! You are exhausted. Pull over safely and rest now!",
    ("Danger", "nod"): "Danger! Your head is dropping. Pull over safely and rest now!",
    ("Danger", "mixed"): "Danger! You are too tired to drive. Pull over safely and rest now!",
}
TEST_MESSAGE = "Voice guidance is on. I will tell you when you need to rest, and why."
CLIP_KEYS = [f"{lvl.lower()}_{cause}" for (lvl, cause) in MESSAGES] + ["test"]
LEVEL_RANK = {"Alert": 0, "Warning": 1, "Danger": 2}


def classify_cause(reasons):
    """Map the detector's reason strings to one cause key: eyes, yawn, nod, mixed or hidden."""
    text = " ".join(reasons or []).lower()
    if "not visible" in text:
        return "hidden"
    if "microsleep" in text:
        return "eyes"
    found = [k for k, words in (("eyes", ("eye",)), ("yawn", ("yawn",)), ("nod", ("nod",)))
             if any(w in text for w in words)]
    return found[0] if len(found) == 1 else "mixed"


def build_message(level, name=None, reasons=None):
    """Sentence for the current level that says what was seen and tells the driver to rest. None if nothing to say."""
    if level not in ("Warning", "Danger"):
        return None
    cause = classify_cause(reasons)
    if level == "Danger" and cause == "hidden":
        cause = "mixed"
    return MESSAGES[(level, cause)]


def clip_key(level, reasons=None):
    """File stem of the clip for this alert, e.g. warning_yawn or danger_mixed."""
    cause = classify_cause(reasons)
    if level == "Danger" and cause == "hidden":
        cause = "mixed"
    return f"{level.lower()}_{cause}"


def missing_clips():
    """Clip names that are not in assets/voice/clips/."""
    return [k for k in CLIP_KEYS if not os.path.isfile(os.path.join(CLIPS_DIR, f"{k}.wav"))]


def clips_available():
    try:
        return any(f.lower().endswith(".wav") for f in os.listdir(CLIPS_DIR))
    except OSError:
        return False


@st.cache_resource(show_spinner="Loading voice model...")
def _load_voice():
    if not os.path.isfile(MODEL_PATH):
        raise FileNotFoundError(MODEL_PATH)
    from piper import PiperVoice  # imported here so the app still starts without Piper
    return PiperVoice.load(MODEL_PATH)


def _onnx_error():
    """None if the .onnx voice can be used, otherwise a short reason."""
    if not os.path.isfile(MODEL_PATH):
        return "visionmate-voice.onnx is not in assets/voice/."
    try:
        _load_voice()
        return None
    except ImportError:
        return "The piper-tts package is not installed."
    except Exception as e:  # noqa: BLE001
        return f"The voice model could not be loaded: {e}"


def voice_error():
    """Returns None if voice guidance is usable (.onnx voice or wav clips), otherwise a short reason."""
    if _onnx_error() is None or clips_available():
        return None
    return "No voice found. Put visionmate-voice.onnx (and its .json) in assets/voice/, or wav clips in assets/voice/clips/."


@st.cache_data(show_spinner=False, max_entries=64)
def _synthesize_b64(text, length_scale):
    from piper import SynthesisConfig
    voice = _load_voice()
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        voice.synthesize_wav(text, wf, syn_config=SynthesisConfig(length_scale=length_scale))
    return base64.b64encode(buf.getvalue()).decode("ascii")


@st.cache_data(show_spinner=False, max_entries=16)
def _clip_b64(key):
    path = os.path.join(CLIPS_DIR, f"{key}.wav")
    if not os.path.isfile(path):
        return None
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("ascii")


def build_player_html(b64_wav, volume=0.9, delay_ms=600):
    """HTML snippet that plays the clip on the parent page so it survives Streamlit reruns.

    The short delay lets the existing alert beep finish first. If the browser blocks access to
    the parent page, it falls back to playing inside the iframe.
    """
    vol = max(0.0, min(1.0, float(volume)))
    return f"""
    <script>
    (function() {{
      try {{
        var host = window;
        try {{ if (window.parent && window.parent.document) {{ host = window.parent; }} }} catch (e) {{ host = window; }}
        if (host.__dgVoice) {{ try {{ host.__dgVoice.pause(); }} catch (e) {{}} }}
        var a = new host.Audio("data:audio/wav;base64,{b64_wav}");
        a.volume = {vol};
        host.__dgVoice = a;
        setTimeout(function() {{
          a.play().catch(function(err) {{ console.log("VisionMate voice blocked by browser:", err); }});
        }}, {int(delay_ms)});
      }} catch (e) {{ console.log("VisionMate voice error:", e); }}
    }})();
    </script>
    """


def _setting(key, default):
    return st.session_state.get(key, default)


def speak_clip(key, force_volume=None):
    """Play one clip in the browser. Returns False if the clip file does not exist."""
    b64 = _clip_b64(key)
    if b64 is None:
        return False
    volume = (force_volume if force_volume is not None else _setting("voice_volume", DEFAULT_VOLUME)) / 100.0
    embed(build_player_html(b64, volume), height=0)
    return True


def speak_text(text, force_volume=None):
    """Say one sentence with the .onnx voice. Returns False if that voice is not usable."""
    if _onnx_error() is not None:
        return False
    try:
        b64 = _synthesize_b64(text, float(_setting("voice_length_scale", DEFAULT_LENGTH_SCALE)))
    except Exception as e:  # noqa: BLE001
        print(f"[VOICE] synthesis failed: {e}")
        return False
    volume = (force_volume if force_volume is not None else _setting("voice_volume", DEFAULT_VOLUME)) / 100.0
    embed(build_player_html(b64, volume), height=0)
    return True


def _say(level, reasons, key, text):
    """The .onnx voice first, the wav clip second."""
    return speak_text(text) or speak_clip(key)


def maybe_speak_alert(level, full_name=None, reasons=None):
    """Call this when the beep alert fires. Applies the on/off switch and the minimum interval.

    A Danger alert is allowed through sooner than a Warning, and a rise from Warning to Danger
    is always spoken straight away.
    """
    if level not in ("Warning", "Danger") or not _setting("voice_enabled", True):
        return False
    now = time.time()
    last_time = _setting("voice_last_spoken", 0)
    last_level = _setting("voice_last_level", "Alert")
    escalated = LEVEL_RANK[level] > LEVEL_RANK.get(last_level, 0)
    interval = DANGER_MIN_INTERVAL if level == "Danger" else _setting("voice_min_interval", DEFAULT_MIN_INTERVAL)
    if not escalated and now - last_time < interval:
        return False

    key = clip_key(level, reasons)
    text = build_message(level, reasons=reasons)
    if not _say(level, reasons, key, text):
        return False
    st.session_state["voice_last_text"] = text
    st.session_state["voice_last_spoken"] = now
    st.session_state["voice_last_level"] = level
    st.session_state["voice_msg_counter"] = _setting("voice_msg_counter", 0) + 1
    return True


def render_voice_controls():
    """Small settings panel for the Live Monitoring tab."""
    with st.expander("Voice guidance", expanded=False):
        err = voice_error()
        if err:
            st.session_state["voice_enabled"] = False
            st.warning(f"Voice guidance is unavailable. {err} The beep alert still works.")
            return
        if _onnx_error() is None:
            st.caption("Voice: visionmate-voice.onnx")
            st.slider("Speaking speed (lower is faster)", 0.7, 1.3, DEFAULT_LENGTH_SCALE, 0.02,
                      key="voice_length_scale")
        else:
            st.caption("Voice: pre-recorded clips")
            missing = missing_clips()
            if missing:
                st.warning("Some voice clips are missing: " + ", ".join(missing))

        st.toggle("Speak drowsiness alerts", value=True, key="voice_enabled")
        st.slider("Volume", 0, 100, DEFAULT_VOLUME, key="voice_volume")
        st.slider("Minimum seconds between Warning messages", 10, 120, DEFAULT_MIN_INTERVAL,
                  key="voice_min_interval")

        if st.button("Test voice", key="voice_test"):
            speak_text(TEST_MESSAGE) or speak_clip("test")

        last = st.session_state.get("voice_last_text")
        if last:
            st.caption(f"Last message: {last}")
