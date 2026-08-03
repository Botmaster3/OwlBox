(function () {
  const coverImg = document.getElementById("cover");
  const coverPlaceholder = document.getElementById("cover-placeholder");
  const storyTitleEl = document.getElementById("story-title");
  const trackTitleEl = document.getElementById("track-title");
  const timePosEl = document.getElementById("time-pos");
  const timeRemainingEl = document.getElementById("time-remaining");
  const progressRow = document.getElementById("progress-row");
  const upcomingEl = document.getElementById("upcoming");
  const upcomingListEl = document.getElementById("upcoming-list");
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
  const brightnessOsdFill = document.getElementById("brightness-osd-fill");
  const wifiBars = document.querySelectorAll("#wifi-bars .wifi-bar");
  const wifiLabel = document.getElementById("wifi-label");
  const vuBars = document.querySelectorAll("#vu-meter .vu-bar");

  let lastCoverUrl = null;
  let parentModeActive = false;
  let hasScannedTag = false;
  let lastBrightness = null;
  let brightnessOsdTimer = null;
  let vuTimer = null;

  // Decorative "is audio playing" animation, not a real audio-level analysis -
  // mpv doesn't expose one over the IPC socket we already talk to it through.
  function setVuPlaying(playing) {
    if (playing) {
      if (vuTimer) return;
      vuTimer = setInterval(() => {
        vuBars.forEach((bar) => {
          bar.style.height = `${12 + Math.random() * 85}%`;
        });
      }, 130);
    } else if (vuTimer) {
      clearInterval(vuTimer);
      vuTimer = null;
      vuBars.forEach((bar) => {
        bar.style.height = "12%";
      });
    }
  }

  // Fill percentage of a value relative to a [min, max] range, e.g. how full
  // the brightness/volume bar should look given the configured limits rather
  // than the raw 0-100 value.
  function relativePercent(value, min, max) {
    if (max <= min) return 0;
    return Math.max(0, Math.min(100, ((value - min) / (max - min)) * 100));
  }

  function showBrightnessOsd(percent, min, max) {
    brightnessOsdValue.textContent = percent;
    brightnessOsdFill.style.width = `${relativePercent(percent, min, max)}%`;
    brightnessOsd.hidden = false;
    clearTimeout(brightnessOsdTimer);
    brightnessOsdTimer = setTimeout(() => {
      brightnessOsd.hidden = true;
    }, 2000);
  }

  // Traffic-light coloring: green from a solid connection, yellow once it's
  // getting weak, red when it's barely usable or there's no connection at all.
  function wifiSignalClass(enabled, signal) {
    if (!enabled || typeof signal !== "number") return "critical";
    if (signal >= 60) return "good";
    if (signal >= 30) return "warn";
    return "critical";
  }

  function applyWifi(wifi) {
    wifi = wifi || {};
    const cls = wifiSignalClass(wifi.enabled, wifi.signal);
    const activeBars =
      wifi.enabled && typeof wifi.signal === "number"
        ? Math.min(4, Math.max(0, Math.ceil((wifi.signal / 100) * 4)))
        : 0;
    wifiBars.forEach((bar, index) => {
      bar.classList.remove("active", "good", "warn", "critical");
      if (index < activeBars) {
        bar.classList.add("active", cls);
      }
    });
    if (!wifi.enabled) {
      wifiLabel.textContent = "Aus";
    } else if (typeof wifi.signal !== "number") {
      wifiLabel.textContent = "Getrennt";
    } else {
      wifiLabel.textContent = `${wifi.signal}%`;
    }
  }

  function formatTime(seconds) {
    seconds = Math.max(0, Math.floor(seconds || 0));
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return `${m}:${String(s).padStart(2, "0")}`;
  }

  function applyState(state) {
    // Shown regardless of splash/parent-mode/tag state, like a phone's own
    // status bar - the brightness OSD change-detection needs it up here too.
    const settings = state.settings || {};
    if (typeof settings.brightness === "number") {
      if (lastBrightness !== null && settings.brightness !== lastBrightness) {
        showBrightnessOsd(settings.brightness, settings.min_brightness, settings.max_brightness);
      }
      lastBrightness = settings.brightness;
    }
    applyWifi(state.wifi);

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
    timeRemainingEl.textContent = `-${formatTime(duration - timePos)}`;
    progressFill.style.width = duration > 0 ? `${Math.min(100, (timePos / duration) * 100)}%` : "0%";

    const trackList = (story && story.tracks) || [];
    if (trackList.length === 0) {
      upcomingEl.hidden = true;
    } else {
      upcomingEl.hidden = false;
      upcomingListEl.innerHTML = trackList
        .map((title, index) => `<li class="${index === story.current_track_index ? "current" : ""}">${title}</li>`)
        .join("");
    }

    volumeFill.style.width = `${relativePercent(player.volume || 0, 0, settings.max_volume || 100)}%`;
    setVuPlaying(!!player.playing);

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
