(function () {
  const npCover = document.getElementById("np-cover");
  const npCoverPlaceholder = document.getElementById("np-cover-placeholder");
  const npTitle = document.getElementById("np-title");
  const npTrack = document.getElementById("np-track");
  const npTimePos = document.getElementById("np-time-pos");
  const npTimeRemaining = document.getElementById("np-time-remaining");
  const npProgressRow = document.getElementById("np-progress-row");
  const npProgressBar = document.getElementById("np-progress-bar");
  const npProgressFill = document.getElementById("np-progress-fill");
  const npUpcoming = document.getElementById("np-upcoming");
  const npUpcomingList = document.getElementById("np-upcoming-list");
  const npSleepTimerBadge = document.getElementById("np-sleep-timer-badge");
  const npSleepTimerRemaining = document.getElementById("np-sleep-timer-remaining");
  const npAutoSleepBadge = document.getElementById("np-auto-sleep-badge");
  const npBtnShuffle = document.getElementById("np-btn-shuffle");
  const npBtnPrev = document.getElementById("np-btn-prev");
  const npBtnToggle = document.getElementById("np-btn-toggle");
  const npBtnNext = document.getElementById("np-btn-next");
  const npRepeatToggle = document.getElementById("np-repeat-toggle");
  const npRepeatButtons = npRepeatToggle.querySelectorAll(".segmented-btn");
  const npVolumeInput = document.getElementById("np-volume");
  const npVolumeValue = document.getElementById("np-volume-value");
  const npBrightnessInput = document.getElementById("np-brightness");
  const npBrightnessValue = document.getElementById("np-brightness-value");
  const npWifiBars = document.querySelectorAll("#np-wifi-bars .wifi-bar");
  const npWifiLabel = document.getElementById("np-wifi-label");
  const hotspotBanner = document.getElementById("hotspot-banner");
  const hotspotSsidEl = document.getElementById("hotspot-ssid");
  const hotspotPasswordEl = document.getElementById("hotspot-password");
  const hotspotUrlEl = document.getElementById("hotspot-url");
  const npVuBars = document.querySelectorAll("#np-vu-meter .vu-bar");
  let lastCoverUrl = null;
  let volumeSliderBeingDragged = false;
  let brightnessSliderBeingDragged = false;
  let vuTimer = null;
  let lastDuration = 0;
  let currentStory = null;

  // Decorative "is audio playing" animation, not a real audio-level analysis -
  // mpv doesn't expose one over the IPC socket we already talk to it through.
  function setVuPlaying(playing) {
    if (playing) {
      if (vuTimer) return;
      vuTimer = setInterval(() => {
        npVuBars.forEach((bar) => {
          bar.style.height = `${12 + Math.random() * 85}%`;
        });
      }, 130);
    } else if (vuTimer) {
      clearInterval(vuTimer);
      vuTimer = null;
      npVuBars.forEach((bar) => {
        bar.style.height = "12%";
      });
    }
  }

  async function postJson(url, body) {
    await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  }

  npBtnPrev.addEventListener("click", () => fetch("/api/control/prev", { method: "POST" }));
  npBtnToggle.addEventListener("click", () => fetch("/api/control/toggle", { method: "POST" }));
  npBtnNext.addEventListener("click", () => fetch("/api/control/next", { method: "POST" }));

  npBtnShuffle.addEventListener("click", () => {
    if (!currentStory) return;
    postJson(`/api/stories/${currentStory.id}/flags`, { shuffle: !currentStory.shuffle });
  });

  npRepeatButtons.forEach((btn) => {
    btn.addEventListener("click", () => {
      if (!currentStory) return;
      postJson(`/api/stories/${currentStory.id}/flags`, { repeat: btn.dataset.mode });
    });
  });

  npProgressBar.addEventListener("click", (event) => {
    if (lastDuration <= 0) return;
    const rect = npProgressBar.getBoundingClientRect();
    const ratio = Math.max(0, Math.min(1, (event.clientX - rect.left) / rect.width));
    const seconds = ratio * lastDuration;
    // Reflect the new position immediately instead of waiting for the next poll tick.
    npProgressFill.style.width = `${ratio * 100}%`;
    npTimePos.textContent = formatTime(seconds);
    npTimeRemaining.textContent = `-${formatTime(lastDuration - seconds)}`;
    postJson("/api/control/seek", { seconds });
  });

  npVolumeInput.addEventListener("input", () => {
    volumeSliderBeingDragged = true;
    npVolumeValue.textContent = npVolumeInput.value;
  });
  npVolumeInput.addEventListener("change", async () => {
    await postJson("/api/settings/volume", { current_volume: parseInt(npVolumeInput.value, 10) });
    volumeSliderBeingDragged = false;
  });

  npBrightnessInput.addEventListener("input", () => {
    brightnessSliderBeingDragged = true;
    npBrightnessValue.textContent = npBrightnessInput.value;
  });
  npBrightnessInput.addEventListener("change", async () => {
    await postJson("/api/settings/brightness", { brightness: parseInt(npBrightnessInput.value, 10) });
    brightnessSliderBeingDragged = false;
  });

  const FUNCTION_LABELS = {
    play: "Play",
    pause: "Pause",
    toggle_pause: "Play/Pause umschalten",
    next: "Weiter",
    previous: "Zurück",
    volume_up: "Lauter",
    volume_down: "Leiser",
    wifi_on: "WLAN an",
    wifi_off: "WLAN aus",
    sleep_timer_15: "Einschlaf-Timer 15 Min",
    sleep_timer_30: "Einschlaf-Timer 30 Min",
    sleep_timer_45: "Einschlaf-Timer 45 Min",
    sleep_timer_60: "Einschlaf-Timer 60 Min",
    sleep_timer_cancel: "Einschlaf-Timer abbrechen",
    restart: "Pi neu starten",
    shutdown: "Pi herunterfahren",
  };

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
    npWifiBars.forEach((bar, index) => {
      bar.classList.remove("active", "good", "warn", "critical");
      if (index < activeBars) {
        bar.classList.add("active", cls);
      }
    });
    if (!wifi.enabled) {
      npWifiLabel.textContent = "Aus";
    } else if (typeof wifi.signal !== "number") {
      npWifiLabel.textContent = "Getrennt";
    } else {
      npWifiLabel.textContent = `${wifi.signal}%`;
    }
  }

  function applyHotspotBanner(wifi) {
    wifi = wifi || {};
    if (!wifi.hotspot_active) {
      hotspotBanner.hidden = true;
      return;
    }
    hotspotSsidEl.textContent = wifi.hotspot_ssid;
    hotspotPasswordEl.textContent = wifi.hotspot_password;
    const port = window.location.port ? `:${window.location.port}` : "";
    hotspotUrlEl.textContent = `http://${wifi.hotspot_ip}${port}/admin`;
    hotspotBanner.hidden = false;
  }

  function formatTime(seconds) {
    seconds = Math.max(0, Math.floor(seconds || 0));
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return `${m}:${String(s).padStart(2, "0")}`;
  }

  function applyState(state) {
    const story = state.story;
    const player = state.player || {};
    currentStory = story;

    // Shuffle/Repeat only make sense for a local track list, not a
    // livestream (no fixed playlist to shuffle or loop) or when nothing is
    // loaded at all (there'd be no story id to send the change to).
    const shuffleRepeatUsable = !!(story && !story.is_stream);
    npBtnShuffle.disabled = !shuffleRepeatUsable;
    npBtnShuffle.classList.toggle("active", shuffleRepeatUsable && story.shuffle);
    const activeRepeatMode = shuffleRepeatUsable ? story.repeat : "off";
    npRepeatButtons.forEach((btn) => {
      btn.disabled = !shuffleRepeatUsable;
      btn.classList.toggle("active", btn.dataset.mode === activeRepeatMode);
    });

    if (story) {
      npTitle.textContent = story.title;
    } else if (state.function_tag) {
      npTitle.textContent = `Funktions-Chip: ${FUNCTION_LABELS[state.function_tag] || state.function_tag}`;
    } else if (state.unknown_tag) {
      npTitle.textContent = "Unbekannter Chip aufgelegt";
    } else {
      npTitle.textContent = "Kein Chip aufgelegt";
    }

    if (story && story.is_stream) {
      npTrack.textContent = "🔴 Live-Stream";
      npTrack.hidden = false;
    } else if (story && story.track_title) {
      npTrack.textContent = story.track_title;
      npTrack.hidden = false;
    } else {
      npTrack.hidden = true;
    }
    npProgressRow.hidden = !!(story && story.is_stream);

    const coverUrl = story && story.cover_url ? story.cover_url : null;
    if (coverUrl !== lastCoverUrl) {
      lastCoverUrl = coverUrl;
      if (coverUrl) {
        npCover.src = coverUrl;
        npCover.hidden = false;
        npCoverPlaceholder.hidden = true;
      } else {
        npCover.hidden = true;
        npCoverPlaceholder.hidden = false;
      }
    }

    const timePos = player.time_pos || 0;
    const duration = player.duration || 0;
    lastDuration = duration;
    npTimePos.textContent = formatTime(timePos);
    npTimeRemaining.textContent = `-${formatTime(duration - timePos)}`;
    npProgressFill.style.width = duration > 0 ? `${Math.min(100, (timePos / duration) * 100)}%` : "0%";
    applyWifi(state.wifi);
    applyHotspotBanner(state.wifi);
    setVuPlaying(!!player.playing);
    // Shows the action the button performs, not the current state - a
    // pause icon while playing (clicking it pauses), a play icon
    // otherwise. ⏯️ (the combined play/pause glyph the button used to
    // show unconditionally) has spotty font support and doesn't say which
    // way it's about to switch, unlike swapping between the two here.
    npBtnToggle.textContent = player.playing ? "⏸️ Pause" : "▶️ Play";

    if (!volumeSliderBeingDragged) {
      npVolumeInput.value = player.volume || 0;
      npVolumeValue.textContent = player.volume || 0;
    }

    const settings = state.settings || {};
    if (!brightnessSliderBeingDragged && typeof settings.brightness === "number") {
      npBrightnessInput.min = settings.min_brightness;
      npBrightnessInput.max = settings.max_brightness;
      npBrightnessInput.value = settings.brightness;
      npBrightnessValue.textContent = settings.brightness;
    }

    const trackList = (story && story.tracks) || [];
    if (trackList.length === 0) {
      npUpcoming.hidden = true;
    } else {
      npUpcoming.hidden = false;
      npUpcomingList.innerHTML = trackList
        .map((title, index) => `<li class="${index === story.current_track_index ? "current" : ""}">${title}</li>`)
        .join("");
    }

    const sleepTimer = state.sleep_timer || {};
    if (sleepTimer.active) {
      npSleepTimerBadge.hidden = false;
      npSleepTimerRemaining.textContent = formatTime(sleepTimer.remaining_seconds);
    } else {
      npSleepTimerBadge.hidden = true;
    }

    const autoSleep = state.auto_sleep || {};
    npAutoSleepBadge.hidden = !autoSleep.active;
  }

  async function poll() {
    try {
      const res = await fetch("/api/state");
      if (res.ok) applyState(await res.json());
    } catch (err) {
      // network hiccup, just try again next tick
    } finally {
      setTimeout(poll, 1000);
    }
  }

  poll();
})();
