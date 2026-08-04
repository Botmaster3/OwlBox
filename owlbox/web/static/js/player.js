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
  const sleepModeEl = document.getElementById("sleep-mode");
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
  const statusBarEl = document.getElementById("status-bar");
  const hotspotBanner = document.getElementById("hotspot-banner");
  const hotspotSsidEl = document.getElementById("hotspot-ssid");
  const hotspotPasswordEl = document.getElementById("hotspot-password");
  const hotspotUrlEl = document.getElementById("hotspot-url");
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

  function applyHotspotBanner(wifi) {
    wifi = wifi || {};
    if (!wifi.hotspot_active) {
      hotspotBanner.hidden = true;
      statusBarEl.hidden = false;
      return;
    }
    hotspotSsidEl.textContent = wifi.hotspot_ssid;
    hotspotPasswordEl.textContent = wifi.hotspot_password;
    const port = window.location.port ? `:${window.location.port}` : "";
    hotspotUrlEl.textContent = `http://${wifi.hotspot_ip}${port}/admin`;
    hotspotBanner.hidden = false;
    // The banner already covers WiFi state plus what to do about it - showing
    // both at once is redundant and there isn't room for both on a small screen.
    statusBarEl.hidden = true;
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
    // Applied even before any tag is scanned (splash screen) and regardless
    // of parent-mode/sleep-mode - the kiosk page loads once and stays open
    // for days, so a theme changed from Einstellungen needs to reach it live
    // rather than only on the next full page reload.
    if (settings.theme && document.documentElement.dataset.theme !== settings.theme) {
      document.documentElement.dataset.theme = settings.theme;
    }
    // Only visible on the Weihnachten theme, but a kiosk left open overnight
    // into a new Advent Sunday should still see the new candle lit live.
    const adventCandles = String(settings.advent_candles);
    if (typeof settings.advent_candles === "number" && document.documentElement.dataset.adventCandles !== adventCandles) {
      document.documentElement.dataset.adventCandles = adventCandles;
      // Nudge a reflow so the animated wreath overlay (html::after) is
      // guaranteed to pick up the new candle count right away rather than
      // waiting for its next unrelated style change.
      void document.documentElement.offsetHeight;
    }
    if (typeof settings.brightness === "number") {
      if (lastBrightness !== null && settings.brightness !== lastBrightness) {
        showBrightnessOsd(settings.brightness, settings.min_brightness, settings.max_brightness);
      }
      lastBrightness = settings.brightness;
    }
    applyWifi(state.wifi);
    applyHotspotBanner(state.wifi);

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

    // Auto-sleep: the story has been paused long enough that the box shows a
    // sleeping owl instead of the now-playing view. Raising the volume,
    // pressing play/pause, or scanning a tag wakes it back up (engine-side) -
    // the state then simply stops reporting auto_sleep.active on the next poll.
    const autoSleep = state.auto_sleep || { active: false };
    sleepModeEl.hidden = !autoSleep.active;
    if (autoSleep.active) {
      playerEl.hidden = true;
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

  // The Weihnachten wreath decoration (html::before/::after) is sized and
  // positioned in CSS to stay clear of the Player's .info column (title,
  // progress/volume bars, track list, sleep-timer badge) for typical
  // content, but that's a guess based on common cases, not a guarantee - on
  // a small kiosk display, a chaptered story plus a running sleep timer can
  // still push .info's bottom edge into the wreath's space. Checked live
  // every poll (rather than only once on load) since that combination can
  // appear or disappear while a story is already playing.
  function updateWreathOverlap() {
    if (document.documentElement.dataset.theme !== "weihnachten") {
      document.documentElement.removeAttribute("data-wreath-clash");
      return;
    }
    const infoEl = document.querySelector(".info");
    const rect = infoEl ? infoEl.getBoundingClientRect() : null;
    // rect.bottom is 0 while .info isn't actually shown (e.g. still on the
    // splash screen, or hidden behind parent-mode/auto-sleep) - never hide
    // the wreath on account of stale/absent layout.
    const safeBottom = window.innerHeight * 0.96 - 45;
    if (rect && rect.bottom > 0 && rect.bottom > safeBottom) {
      document.documentElement.setAttribute("data-wreath-clash", "1");
    } else {
      document.documentElement.removeAttribute("data-wreath-clash");
    }
  }

  async function poll() {
    try {
      const res = await fetch("/api/state");
      if (res.ok) {
        applyState(await res.json());
        updateWreathOverlap();
      }
    } catch (err) {
      // network hiccup, just try again next tick
    } finally {
      setTimeout(poll, 1000);
    }
  }

  poll();
})();
