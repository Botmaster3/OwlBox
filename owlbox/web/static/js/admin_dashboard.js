(function () {
  const npCover = document.getElementById("np-cover");
  const npCoverPlaceholder = document.getElementById("np-cover-placeholder");
  const npTitle = document.getElementById("np-title");
  const npTrack = document.getElementById("np-track");
  const npTimePos = document.getElementById("np-time-pos");
  const npTimeDur = document.getElementById("np-time-dur");
  const npProgressRow = document.getElementById("np-progress-row");
  const npProgressFill = document.getElementById("np-progress-fill");
  const npUpcoming = document.getElementById("np-upcoming");
  const npUpcomingList = document.getElementById("np-upcoming-list");
  const npSleepTimerBadge = document.getElementById("np-sleep-timer-badge");
  const npSleepTimerRemaining = document.getElementById("np-sleep-timer-remaining");
  const npBtnPrev = document.getElementById("np-btn-prev");
  const npBtnToggle = document.getElementById("np-btn-toggle");
  const npBtnNext = document.getElementById("np-btn-next");
  const npVolumeInput = document.getElementById("np-volume");
  const npVolumeValue = document.getElementById("np-volume-value");
  const npBrightnessInput = document.getElementById("np-brightness");
  const npBrightnessValue = document.getElementById("np-brightness-value");
  const npWifiFill = document.getElementById("np-wifi-fill");
  const npWifiLabel = document.getElementById("np-wifi-label");
  let lastCoverUrl = null;
  let volumeSliderBeingDragged = false;
  let brightnessSliderBeingDragged = false;

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
    npWifiFill.classList.remove("good", "warn", "critical");
    npWifiFill.classList.add(wifiSignalClass(wifi.enabled, wifi.signal));
    if (!wifi.enabled) {
      npWifiFill.style.width = "0%";
      npWifiLabel.textContent = "Aus";
    } else if (typeof wifi.signal !== "number") {
      npWifiFill.style.width = "0%";
      npWifiLabel.textContent = "Getrennt";
    } else {
      npWifiFill.style.width = `${Math.max(0, Math.min(100, wifi.signal))}%`;
      npWifiLabel.textContent = `${wifi.signal}%`;
    }
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
    npTimePos.textContent = formatTime(timePos);
    npTimeDur.textContent = formatTime(duration);
    npProgressFill.style.width = duration > 0 ? `${Math.min(100, (timePos / duration) * 100)}%` : "0%";
    applyWifi(state.wifi);

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

    const upcoming = (story && story.upcoming_tracks) || [];
    if (upcoming.length === 0) {
      npUpcoming.hidden = true;
    } else {
      npUpcoming.hidden = false;
      npUpcomingList.innerHTML = upcoming.map((title) => `<li>${title}</li>`).join("");
    }

    const sleepTimer = state.sleep_timer || {};
    if (sleepTimer.active) {
      npSleepTimerBadge.hidden = false;
      npSleepTimerRemaining.textContent = formatTime(sleepTimer.remaining_seconds);
    } else {
      npSleepTimerBadge.hidden = true;
    }
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
