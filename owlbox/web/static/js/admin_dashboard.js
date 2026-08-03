(function () {
  const npCover = document.getElementById("np-cover");
  const npCoverPlaceholder = document.getElementById("np-cover-placeholder");
  const npTitle = document.getElementById("np-title");
  const npTrack = document.getElementById("np-track");
  const npTimePos = document.getElementById("np-time-pos");
  const npTimeDur = document.getElementById("np-time-dur");
  const npProgressRow = document.getElementById("np-progress-row");
  const npProgressFill = document.getElementById("np-progress-fill");
  const npVolumeFill = document.getElementById("np-volume-fill");
  const npUpcoming = document.getElementById("np-upcoming");
  const npUpcomingList = document.getElementById("np-upcoming-list");
  const npSleepTimerBadge = document.getElementById("np-sleep-timer-badge");
  const npSleepTimerRemaining = document.getElementById("np-sleep-timer-remaining");
  let lastCoverUrl = null;

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
    npVolumeFill.style.width = `${Math.max(0, Math.min(100, player.volume || 0))}%`;

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
