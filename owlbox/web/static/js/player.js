(function () {
  const coverImg = document.getElementById("cover");
  const coverPlaceholder = document.getElementById("cover-placeholder");
  const storyTitleEl = document.getElementById("story-title");
  const trackTitleEl = document.getElementById("track-title");
  const timePosEl = document.getElementById("time-pos");
  const timeDurEl = document.getElementById("time-dur");
  const progressRow = document.getElementById("progress-row");
  const progressFill = document.getElementById("progress-fill");
  const volumeFill = document.getElementById("volume-fill");
  const unknownBanner = document.getElementById("unknown-banner");
  const playerEl = document.querySelector(".player");
  const parentModeEl = document.getElementById("parent-mode");
  const parentModeLabelEl = document.getElementById("parent-mode-label");
  const parentModeQrEl = document.getElementById("parent-mode-qr");
  const sleepTimerBadge = document.getElementById("sleep-timer-badge");
  const sleepTimerRemaining = document.getElementById("sleep-timer-remaining");
  const splashEl = document.getElementById("splash");
  const brightnessOsd = document.getElementById("brightness-osd");
  const brightnessOsdValue = document.getElementById("brightness-osd-value");

  let lastCoverUrl = null;
  let parentModeActive = false;
  let hasScannedTag = false;
  let lastBrightness = null;
  let brightnessOsdTimer = null;

  function showBrightnessOsd(percent) {
    brightnessOsdValue.textContent = percent;
    brightnessOsd.hidden = false;
    clearTimeout(brightnessOsdTimer);
    brightnessOsdTimer = setTimeout(() => {
      brightnessOsd.hidden = true;
    }, 2000);
  }

  function formatTime(seconds) {
    seconds = Math.max(0, Math.floor(seconds || 0));
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return `${m}:${String(s).padStart(2, "0")}`;
  }

  function applyState(state) {
    // Shown regardless of splash/parent-mode/tag state, since brightness can
    // change (via the encoder or the web UI) at any time.
    const settings = state.settings || {};
    if (typeof settings.brightness === "number") {
      if (lastBrightness !== null && settings.brightness !== lastBrightness) {
        showBrightnessOsd(settings.brightness);
      }
      lastBrightness = settings.brightness;
    }

    const story = state.story;
    const player = state.player || {};
    const parentMode = state.parent_mode || { active: false, label: null };

    // On boot, show the OwlBox splash (owl + name) instead of the "no chip"
    // now-playing view - it only goes away once any chip (story, function, or
    // parent tag) has actually been read, and stays gone for the rest of this
    // page load even after that chip is removed again.
    if (!hasScannedTag) {
      if (!state.uid) {
        return;
      }
      hasScannedTag = true;
      splashEl.hidden = true;
    }

    // Parent mode (a "Vater"/"Mutter" chip is on the reader) shows a QR code to
    // the login page instead of the normal now-playing view - never revealed to
    // kids scanning story or function tags.
    if (parentMode.active !== parentModeActive) {
      parentModeActive = parentMode.active;
      if (parentModeActive) {
        // Generate the QR code fresh at the moment the chip is scanned - the IP it
        // encodes may have changed since the last time a parent tag was placed, and
        // the kiosk page itself never reloads on its own to pick that up otherwise.
        parentModeQrEl.src = `/login-qr.svg?t=${Date.now()}`;
      }
    }
    parentModeEl.hidden = !parentModeActive;
    playerEl.hidden = parentModeActive;
    if (parentModeActive) {
      parentModeLabelEl.textContent = `Eltern-Modus: ${parentMode.label}`;
      return;
    }

    if (story) {
      storyTitleEl.textContent = story.title;
    } else if (state.unknown_tag) {
      storyTitleEl.textContent = "Unbekannter Chip";
    } else {
      storyTitleEl.textContent = "Kein Chip aufgelegt";
    }

    if (story && story.is_stream) {
      trackTitleEl.textContent = "🔴 Live-Stream";
      trackTitleEl.hidden = false;
    } else if (story && story.track_title) {
      trackTitleEl.textContent = story.track_title;
      trackTitleEl.hidden = false;
    } else {
      trackTitleEl.hidden = true;
    }
    progressRow.hidden = !!(story && story.is_stream);

    const coverUrl = story && story.cover_url ? story.cover_url : null;
    if (coverUrl !== lastCoverUrl) {
      lastCoverUrl = coverUrl;
      if (coverUrl) {
        coverImg.src = coverUrl;
        coverImg.hidden = false;
        coverPlaceholder.hidden = true;
      } else {
        coverImg.hidden = true;
        coverPlaceholder.hidden = false;
      }
    }

    const timePos = player.time_pos || 0;
    const duration = player.duration || 0;
    timePosEl.textContent = formatTime(timePos);
    timeDurEl.textContent = formatTime(duration);
    progressFill.style.width = duration > 0 ? `${Math.min(100, (timePos / duration) * 100)}%` : "0%";

    volumeFill.style.width = `${Math.max(0, Math.min(100, player.volume || 0))}%`;

    unknownBanner.hidden = !state.unknown_tag;

    const sleepTimer = state.sleep_timer || {};
    if (sleepTimer.active) {
      sleepTimerBadge.hidden = false;
      sleepTimerRemaining.textContent = formatTime(sleepTimer.remaining_seconds);
    } else {
      sleepTimerBadge.hidden = true;
    }
  }

  async function poll() {
    try {
      const res = await fetch("/api/state");
      if (res.ok) {
        applyState(await res.json());
      }
    } catch (err) {
      // network hiccup, just try again next tick
    } finally {
      setTimeout(poll, 1000);
    }
  }

  poll();
})();
