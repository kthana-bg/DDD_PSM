"""Graded alerts: a soft beep for Warning, a louder alarm for Danger."""
import time
from typing import Optional

from utils.html_embed import embed

WARN_REPEAT_S = 12.0
DANGER_REPEAT_S = 5.0
_RANK = {"Alert": 0, "Warning": 1, "Danger": 2}


class AlertManager:
    """Decides when a sound should play. Escalations play at once; a level that persists repeats."""

    def __init__(self, warn_repeat_s: float = WARN_REPEAT_S, danger_repeat_s: float = DANGER_REPEAT_S):
        self.warn_repeat_s, self.danger_repeat_s = warn_repeat_s, danger_repeat_s
        self.reset()

    def reset(self):
        self._last_level = "Alert"
        self._last_play = 0.0
        self._cleared = False

    def pop_cleared(self) -> bool:
        """True once after the level drops back to Alert, so the page can stop any sound still playing."""
        c, self._cleared = self._cleared, False
        return c

    def update(self, level: str, now: Optional[float] = None) -> Optional[str]:
        now = time.time() if now is None else now
        if level == "Alert":
            self._cleared = self._cleared or self._last_level != "Alert"
            self._last_level = "Alert"
            return None
        escalated = _RANK[level] > _RANK[self._last_level]
        repeat = self.danger_repeat_s if level == "Danger" else self.warn_repeat_s
        due = escalated or (now - self._last_play) >= repeat
        self._last_level = level
        if not due:
            return None
        self._last_play = now
        return "loud" if level == "Danger" else "soft"


def _script(kind: str, volume: float) -> str:
    vol = max(0.0, min(1.0, float(volume)))
    if kind == "loud":
        tones, dur, wave, gain = [880, 1175, 880], 0.14, "square", 0.55 * vol + 0.15
    else:
        tones, dur, wave, gain = [660], 0.16, "sine", 0.22 * vol
    return f"""
    <script>/* {time.time()} */
    (function() {{
      try {{
        var host = window;
        try {{ if (window.parent && window.parent.document) {{ host = window.parent; }} }} catch (e) {{ host = window; }}
        var AC = host.AudioContext || host.webkitAudioContext;
        if (!host.__dgAudio) {{ host.__dgAudio = new AC(); }}
        var ctx = host.__dgAudio; if (ctx.state === 'suspended') {{ ctx.resume(); }}
        (host.__dgOsc || []).forEach(function(o) {{ try {{ o.stop(); }} catch (e) {{}} }});
        host.__dgOsc = [];
        var t = ctx.currentTime + 0.02, tones = {tones}, dur = {dur};
        tones.forEach(function(f, i) {{
          var o = ctx.createOscillator(), g = ctx.createGain();
          host.__dgOsc.push(o);
          o.type = '{wave}'; o.frequency.value = f; g.gain.value = {gain:.3f};
          o.connect(g); g.connect(ctx.destination);
          var s = t + i * (dur + 0.05); o.start(s); o.stop(s + dur);
        }});
      }} catch (e) {{ console.log('VisionMate sound blocked:', e); }}
    }})();
    </script>
    """


def play_alert(kind: str, volume: float = 0.8):
    """kind: 'soft' (Warning) or 'loud' (Danger)."""
    embed(_script(kind, volume), height=0)


def stop_alert():
    """Cut off any beep or spoken message that is still playing (used when the level returns to Alert)."""
    embed("""
    <script>/* %s */
    (function() {
      try {
        var host = window;
        try { if (window.parent && window.parent.document) { host = window.parent; } } catch (e) { host = window; }
        (host.__dgOsc || []).forEach(function(o) { try { o.stop(); } catch (e) {} });
        host.__dgOsc = [];
        if (host.__dgVoice) { try { host.__dgVoice.pause(); } catch (e) {} }
      } catch (e) {}
    })();
    </script>
    """ % time.time(), height=0)
