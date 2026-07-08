# Podcast Pill — Inline Player Design

## Architecture

The podcast pill is injected by `inject_podcast_pill.py` as a post-process step AFTER `render.py` completes. It is NOT part of the template or the render pipeline — standalone, swappable, removable.

## HTML structure injected

Inside the lead `<article>` element, right before `</article>`:

```html
<div class="podcast-pill">
  <button class="pill-btn" onclick="togglePodcast(this)">
    <svg class="pill-wave">...</svg>
    <span class="pill-label">Podcast Pill</span>
    <span class="pill-divider">·</span>
    <span class="pill-show">The Divide</span>
    <span class="pill-duration">1:59</span>
  </button>
  <audio class="pill-audio" preload="none">
    <source src="podcasts/lead_2026-07-08.ogg" type="audio/ogg">
  </audio>
  <div class="pill-progress">
    <span class="pill-progress-bar"></span>
  </div>
</div>
```

## CSS — uses ONLY Lux CSS variables

| Element | Key style | Variable |
|---------|-----------|----------|
| `.podcast-pill .pill-btn` | border, text, font | `var(--rule)`, `var(--type)`, `var(--sans)` |
| `.podcast-pill .pill-btn:hover` | border+text shift | `var(--lux)` |
| `.podcast-pill.is-playing .pill-btn` | playing accent | `var(--ember)` |
| `.podcast-pill .pill-show` | show name | `var(--ember)` + `font-weight: 600` |
| `.podcast-pill .pill-label` | label text | `var(--type-dim)` |
| `.podcast-pill .pill-duration` | duration | `var(--muted)` |
| `.podcast-pill .pill-divider` | separator | `var(--muted)` |
| `.podcast-pill .pill-progress-bar` | progress fill | `var(--ember)` |
| `.podcast-pill .pill-progress` | progress track | `var(--rule)` |
| `@keyframes pill-bar` | bar animation | bars scale Y 0.3–1.0, 0.6s alternate |

## JS — inline, no dependencies

- **`togglePodcast(btn)`**: finds sibling `<audio>`, toggles play/pause, manages `.is-playing` / `.is-paused` class. Mutes any OTHER `.podcast-pill.is-playing` on the page (only one plays at a time).
- **`timeupdate` event delegation**: `document.addEventListener('timeupdate', ..., true)` updates the progress bar width as percentage of `audio.currentTime / audio.duration`.
- **`ended` event**: resets to initial state, clears progress bar.
- **No external libraries.** ~40 lines, no build step.

## State classes on `.podcast-pill`

| Class | Meaning |
|-------|---------|
| `is-playing` | Audio is actively playing. Waveform bars animate. Border = `--ember` |
| `is-paused` | Audio was playing but paused. Waveform returns to pulse. Border = default |
| *(none)* | Initial state (never played). Waveform pulses gently |

## Waveform animation

- **Idle/paused:** `@keyframes pill-pulse` — entire SVG fades 1.0→0.65→1.0 over 2s
- **Playing:** each `.wave-bar` independently animates with `@keyframes pill-bar` — scaleY 0.3→1.0, staggered delays (0s, 0.1s, 0.2s, 0.3s, 0.4s)
- **Hover on pill-btn:** waveform animation freezes (no transition gap)

## Key design decisions

1. **`<button>` not `<a>`** — ensures no page navigation on click. The `onclick` handler is inline for maximal compatibility; there is no external JS file.
2. **`preload="none"`** — the audio file is NOT downloaded until the user clicks. Zero bandwidth impact for readers who don't click the pill.
3. **Progress bar** — 2px thin, full-width under the pill, hidden until playback starts. Shows at a glance how far into the podcast you are.
4. **Single-play constraint** — only one pill plays at a time. Clicking a second pill (future use) pauses the first automatically.
5. **Graceful degradation** — if JS is disabled, the pill remains as a styled `<button>` that does nothing. No broken links, no errors.
