#!/usr/bin/env python3
"""
inject_podcast_pill.py — Injects the "Podcast Pill: The Divide" inline player
into the rendered Lux in Tenebris HTML, right below the lead article.

Click the pill → plays inline (no new tab). Click again → pauses.
Progress bar appears during playback. Minimal, Lux-styled.

Usage:
    python3 inject_podcast_pill.py <index.html> <ogg_rel_path> <duration_sec> [--output OUTFILE]

Example:
    python3 inject_podcast_pill.py /tmp/v2/output/index.html podcasts/lead_2026-07-08.ogg 119
"""

import sys
import json
from pathlib import Path


def make_podcast_pill_html(ogg_rel_path: str, duration_sec: int) -> str:
    """Generate the podcast pill HTML block with inline audio player."""
    minutes = duration_sec // 60
    seconds = duration_sec % 60
    duration_str = f"{minutes}:{seconds:02d}"

    return f"""
<div class="podcast-pill">
  <button class="pill-btn" onclick="togglePodcast(this)" title="Play / Pause">
    <svg class="pill-wave" width="14" height="14" viewBox="0 0 14 14" fill="none" xmlns="http://www.w3.org/2000/svg">
      <rect x="1" y="6" width="2" height="5" rx="1" fill="currentColor" opacity="0.5" class="wave-bar b1"/>
      <rect x="4" y="4" width="2" height="8" rx="1" fill="currentColor" opacity="0.7" class="wave-bar b2"/>
      <rect x="7" y="1" width="2" height="12" rx="1" fill="currentColor" class="wave-bar b3"/>
      <rect x="10" y="4" width="2" height="8" rx="1" fill="currentColor" opacity="0.7" class="wave-bar b4"/>
      <rect x="13" y="6" width="2" height="5" rx="1" fill="currentColor" opacity="0.5" class="wave-bar b5"/>
    </svg>
    <span class="pill-label">Podcast Pill</span>
    <span class="pill-divider">·</span>
    <span class="pill-show">The Divide</span>
    <span class="pill-duration">{duration_str}</span>
  </button>
  <audio class="pill-audio" preload="none">
    <source src="{ogg_rel_path}" type="audio/ogg">
  </audio>
  <div class="pill-progress" aria-hidden="true">
    <span class="pill-progress-bar"></span>
  </div>
</div>"""


def make_podcast_css() -> str:
    """Generate podcast pill CSS — inline player (no new tab)."""
    return """
/* ── Podcast Pill (inline player) ──────────── */
.podcast-pill {
  margin: 12px 0 0;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 4px;
  position: relative;
}
.podcast-pill .pill-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 5px 14px 5px 12px;
  border: 1px solid var(--rule);
  border-radius: 20px;
  text-decoration: none;
  color: var(--type);
  font-family: var(--sans);
  font-size: 10px;
  letter-spacing: .06em;
  text-transform: uppercase;
  line-height: 1;
  cursor: pointer;
  background: none;
  transition: border-color .25s ease, color .25s ease;
}
.podcast-pill .pill-btn:hover {
  border-color: var(--lux);
  color: var(--lux);
}
.podcast-pill .pill-btn:focus-visible {
  outline: 1px solid var(--lux);
  outline-offset: 2px;
}
/* Playing state */
.podcast-pill.is-playing .pill-btn {
  border-color: var(--ember);
  color: var(--ember);
}
.podcast-pill .pill-wave {
  flex-shrink: 0;
  animation: pill-pulse 2s ease-in-out infinite;
}
.podcast-pill.is-playing .pill-wave {
  animation: none;
}
.podcast-pill.is-playing .pill-wave .wave-bar {
  animation: pill-bar 0.6s ease-in-out infinite alternate;
  transform-origin: bottom;
}
@keyframes pill-pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: .65; }
}
@keyframes pill-bar {
  0% { transform: scaleY(0.3); }
  100% { transform: scaleY(1); }
}
.podcast-pill .pill-wave .b1 { animation-delay: 0s; }
.podcast-pill .pill-wave .b2 { animation-delay: .1s; }
.podcast-pill .pill-wave .b3 { animation-delay: .2s; }
.podcast-pill .pill-wave .b4 { animation-delay: .3s; }
.podcast-pill .pill-wave .b5 { animation-delay: .4s; }
.podcast-pill .pill-divider { color: var(--muted); margin: 0 1px; }
.podcast-pill .pill-show { color: var(--ember); font-weight: 600; }
.podcast-pill .pill-duration { color: var(--muted); font-weight: 400; }
.podcast-pill .pill-label { color: var(--type-dim); }
/* Progress bar */
.podcast-pill .pill-progress {
  width: 100%;
  height: 2px;
  background: var(--rule);
  border-radius: 1px;
  overflow: hidden;
  opacity: 0;
  transition: opacity .3s ease;
}
.podcast-pill.is-playing .pill-progress,
.podcast-pill.is-paused .pill-progress {
  opacity: 1;
}
.podcast-pill .pill-progress-bar {
  display: block;
  height: 100%;
  width: 0%;
  background: var(--ember);
  border-radius: 1px;
  transition: width .3s linear;
}
/* Hide audio element */
.podcast-pill .pill-audio {
  position: absolute;
  width: 0;
  height: 0;
  opacity: 0;
  pointer-events: none;
}
/* ── End Podcast Pill ──────────────────────── */"""


def make_podcast_js() -> str:
    """Generate JavaScript for inline play/pause toggle."""
    return """
<script>
(function() {
  function togglePodcast(btn) {
    var pill = btn.closest('.podcast-pill');
    if (!pill) return;
    var audio = pill.querySelector('.pill-audio');
    if (!audio) return;
    var bar = pill.querySelector('.pill-progress-bar');
    if (!bar) return;

    if (pill.classList.contains('is-playing')) {
      audio.pause();
      pill.classList.remove('is-playing');
      pill.classList.add('is-paused');
    } else {
      // Pause any other playing podcast on the page
      document.querySelectorAll('.podcast-pill.is-playing').forEach(function(p) {
        if (p !== pill) {
          p.querySelector('.pill-audio').pause();
          p.classList.remove('is-playing', 'is-paused');
        }
      });
      audio.play().then(function() {
        pill.classList.add('is-playing');
        pill.classList.remove('is-paused');
      }).catch(function() {
        // Autoplay blocked — do nothing gracefully
      });
    }
  }

  // Update progress bar during playback
  document.addEventListener('timeupdate', function(e) {
    var audio = e.target;
    if (!audio.classList.contains('pill-audio')) return;
    var pill = audio.closest('.podcast-pill');
    if (!pill) return;
    var bar = pill.querySelector('.pill-progress-bar');
    if (!bar) return;
    if (audio.duration) {
      bar.style.width = ((audio.currentTime / audio.duration) * 100) + '%';
    }
  }, true);

  // When audio ends, reset
  document.addEventListener('ended', function(e) {
    var audio = e.target;
    if (!audio.classList.contains('pill-audio')) return;
    var pill = audio.closest('.podcast-pill');
    if (!pill) return;
    var bar = pill.querySelector('.pill-progress-bar');
    pill.classList.remove('is-playing', 'is-paused');
    if (bar) bar.style.width = '0%';
  }, true);

  window.togglePodcast = togglePodcast;
})();
</script>"""


def inject_podcast(html_content: str, ogg_rel_path: str, duration_sec: int) -> str:
    """Inject podcast pill, CSS, and JS into the rendered HTML."""
    # 1. Inject CSS before </head>
    css_block = f"<style>\n{make_podcast_css().strip()}\n</style>"
    html_content = html_content.replace("</head>", f"{css_block}\n</head>", 1)

    # 2. Inject podcast pill before </article> (the lead article close)
    pill_html = make_podcast_pill_html(ogg_rel_path, duration_sec)
    html_content = html_content.replace(
        "</article>",
        f"{pill_html}\n</article>",
        1
    )

    # 3. Inject JS before </body>
    js_block = f"\n{make_podcast_js().strip()}"
    html_content = html_content.replace("</body>", f"{js_block}\n</body>", 1)

    return html_content


def main():
    if len(sys.argv) < 4:
        print(json.dumps({
            "status": "error",
            "error": "Usage: inject_podcast_pill.py <index.html> <ogg_rel_path> <duration_sec> [--output OUTFILE]"
        }))
        sys.exit(1)

    html_path = Path(sys.argv[1])
    ogg_rel_path = sys.argv[2]
    try:
        duration_sec = int(sys.argv[3])
    except ValueError:
        print(json.dumps({"status": "error", "error": "duration_sec must be an integer"}))
        sys.exit(1)

    output_path = html_path
    if "--output" in sys.argv:
        idx = sys.argv.index("--output")
        if idx + 1 < len(sys.argv):
            output_path = Path(sys.argv[idx + 1])

    if not html_path.exists():
        print(json.dumps({"status": "error", "error": f"HTML file not found: {html_path}"}))
        sys.exit(1)

    content = html_path.read_text(encoding="utf-8")
    result = inject_podcast(content, ogg_rel_path, duration_sec)

    output_path.write_text(result, encoding="utf-8")

    print(json.dumps({
        "status": "ok",
        "injected": True,
        "output": str(output_path),
        "ogg": ogg_rel_path,
        "duration_sec": duration_sec,
        "player": "inline"
    }))


if __name__ == "__main__":
    main()