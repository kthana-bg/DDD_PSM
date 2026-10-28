import base64
import io
import json
import os
import time
import wave

import streamlit as st
from utils.html_embed import embed

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VOICE_DIR = os.path.join(_ROOT, "assets", "voice")
MODEL_PATH = os.path.join(VOICE_DIR, "visionmate-voice.onnx")
SETTINGS_PATH = os.path.join(VOICE_DIR, "voice_settings.json")
CLIPS_DIR = os.path.join(VOICE_DIR, "clips")

DEFAULT_LENGTH_SCALE = 1.0
DEFAULT_MIN_INTERVAL = 30      # seconds between spoken messages
DEFAULT_VOLUME = 80            # percent

MESSAGES = {
    ("Warning", "eyes"): "Your eyes are closing more often than normal. Please take a rest soon.",
    ("Warning", "yawn"): "You are yawning a lot. Please take a rest soon.",
    ("Warning", "nod"): "Your head keeps dropping. Please take a rest soon.",
    ("Warning", "mixed"): "You are showing several signs of tiredness. Please take a rest soon.",
    ("Warning", "hidden"): "I cannot see your face. Please sit upright so I can keep watching.",
    ("Danger", "eyes"): "Danger. Your eyes have been closed too long. Pull over safely and rest now.",
    ("Danger", "yawn"): "Danger. You are yawning heavily and look very tired. Pull over safely and rest now.",
    ("Danger", "nod"): "Danger. Your head is dropping. Pull over safely and rest now.",
    ("Danger", "mixed"): "Danger. You are showing serious signs of sleepiness. Pull over safely and rest now.",
}
TEST_MESSAGE = "Voice guidance is on. I will tell you when you need to rest, and why."


def classify_cause(reasons):
    """Map the detector's reason strings to one cause key: eyes, yawn, nod, mixed or hidden."""
    text = " ".join(reasons or []).lower()
    if "not visible" in text:
        return "hidden"
    found = [k for k, words in (("eyes", ("eye", "microsleep")), ("yawn", ("yawn",)), ("nod", ("nod",)))
             if any(w in text for w in words)]
    if "microsleep" in text:
        return "eyes"
    return found[0] if len(found) == 1 else "mixed"


def first_name(full_name):
    if not full_name:
        return None
    token = str(full_name).strip().split()[0] if str(full_name).strip() else ""
    token = "".join(ch for ch in token if ch.isalpha())
    return token.capitalize() if token else None


def personalise(text, name):
    if not name:
        return text
    return f"{name}, {text[0].lower()}{text[1:]}"


def build_message(level, name=None, reasons=None):
    """Sentence for the current level that says what was seen and tells the driver to rest. None if nothing to say."""
    if level not in ("Warning", "Danger"):
        return None
    cause = classify_cause(reasons)
    if level == "Danger" and cause == "hidden":
        cause = "mixed"
    return personalise(MESSAGES[(level, cause)], name)


def clip_key(level, reasons=None):
    """File stem of the pre-recorded clip for this alert, e.g. warning_yawn or danger_mixed."""
    cause = classify_cause(reasons)
    if level == "Danger" and cause == "hidden":
        cause = "mixed"
    return f"{level.lower()}_{cause}"


def clips_available():
    try:
        return any(f.lower().endswith(".wav") for f in os.listdir(CLIPS_DIR))
    except OSError:
        return False


@st.cache_data(show_spinner=False, max_entries=32)
def _clip_b64(key):
    path = os.path.join(CLIPS_DIR, f"{key}.wav")
    if not os.path.exists(path):
        return None
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("ascii")


def speak_clip(key, force_volume=None):
    """Play a pre-rendered clip. Returns False if the clip file does not exist."""
    b64 = _clip_b64(key)
    if b64 is None:
        return False
    volume = (force_volume if force_volume is not None else _setting("voice_volume", DEFAULT_VOLUME)) / 100.0
    embed(build_player_html(b64, volume), height=0)
    return True


def build_player_html(b64_wav, volume=0.8, delay_ms=600):
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


# ----------------------------------------------------------------------------
# Model loading and synthesis
# ----------------------------------------------------------------------------
@st.cache_resource(show_spinner="Loading voice model...")
def _load_voice():
    if not os.path.exists(MODEL_PATH):
        raise FileNotFoundError(f"Voice model not found at {MODEL_PATH}")
    from piper import PiperVoice  # imported lazily so the app still starts without Piper
    return PiperVoice.load(MODEL_PATH)


def get_length_scale():
    try:
        with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
            return float(json.load(f).get("length_scale", DEFAULT_LENGTH_SCALE))
    except Exception:
        return DEFAULT_LENGTH_SCALE


def voice_error():
    """Returns None if voice guidance is usable, otherwise a short reason string."""
    if clips_available():
        return None
    try:
        _load_voice()
        return None
    except FileNotFoundError:
        return "Voice model files are missing from assets/voice/."
    except ImportError:
        return "The piper-tts package is not installed."
    except Exception as e:  # noqa: BLE001
        return f"Voice model could not be loaded: {e}"


@st.cache_data(show_spinner=False, max_entries=64)
def _synthesize_b64(text, length_scale):
    from piper import SynthesisConfig
    voice = _load_voice()
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        voice.synthesize_wav(text, wf, syn_config=SynthesisConfig(length_scale=length_scale))
    data = buf.getvalue()
    with wave.open(io.BytesIO(data), "rb") as wf:
        duration = wf.getnframes() / float(wf.getframerate())
    return base64.b64encode(data).decode("ascii"), duration


# ----------------------------------------------------------------------------
# Streamlit-facing API
# ----------------------------------------------------------------------------
def _setting(key, default):
    return st.session_state.get(key, default)


def speak(text, force_volume=None):
    """Synthesise and play one message. Returns True if it was sent to the browser."""
    if voice_error() is not None:
        return False
    try:
        b64, _ = _synthesize_b64(text, get_length_scale())
    except Exception as e:  # noqa: BLE001
        print(f"[VOICE] synthesis failed: {e}")
        return False
    volume = (force_volume if force_volume is not None else _setting("voice_volume", DEFAULT_VOLUME)) / 100.0
    embed(build_player_html(b64, volume), height=0)
    st.session_state["voice_last_text"] = text
    return True


def maybe_speak_alert(level, full_name=None, reasons=None):
    """Call this when the beep alert fires. Applies the on/off switch and the minimum interval."""
    if not _setting("voice_enabled", True):
        return False
    now = time.time()
    if now - _setting("voice_last_spoken", 0) < _setting("voice_min_interval", DEFAULT_MIN_INTERVAL):
        return False

    name = first_name(full_name) if _setting("voice_use_name", False) else None
    counter = _setting("voice_msg_counter", 0)
    if not name and clips_available():
        if speak_clip(clip_key(level, reasons)):
            st.session_state["voice_last_text"] = build_message(level, reasons=reasons)
            st.session_state["voice_last_spoken"] = now
            st.session_state["voice_msg_counter"] = counter + 1
            return True
    text = build_message(level, name=name, reasons=reasons)
    if text is None:
        return False

    if speak(text):
        st.session_state["voice_last_spoken"] = now
        st.session_state["voice_msg_counter"] = counter + 1
        return True
    return False


def render_voice_controls():
    """Small settings panel for the Live Monitoring tab."""
    with st.expander("Voice guidance", expanded=False):
        err = voice_error()
        if err:
            st.session_state["voice_enabled"] = False
            st.warning(f"Voice guidance is unavailable. {err} The beep alert still works.")
            return

        col_a, col_b = st.columns(2)
        with col_a:
            st.toggle("Speak drowsiness alerts", value=True, key="voice_enabled")
        with col_b:
            st.toggle("Use my name (may sound odd with a custom voice)", value=False, key="voice_use_name")

        st.slider("Volume", 0, 100, DEFAULT_VOLUME, key="voice_volume")
        st.slider("Minimum seconds between voice messages", 10, 120, DEFAULT_MIN_INTERVAL,
                  key="voice_min_interval")

        if st.button("Test voice", key="voice_test"):
            if not speak_clip("test"):
                name = first_name((st.session_state.get("user") or {}).get("full_name")) \
                    if _setting("voice_use_name", False) else None
                speak(personalise(TEST_MESSAGE, name))

        last = st.session_state.get("voice_last_text")
        if last:
            st.caption(f"Last message: {last}")
