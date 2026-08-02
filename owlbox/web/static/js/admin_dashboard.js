(function () {
  const npCover = document.getElementById("np-cover");
  const npCoverPlaceholder = document.getElementById("np-cover-placeholder");
  const npTitle = document.getElementById("np-title");
  const npTrack = document.getElementById("np-track");
  const npTimePos = document.getElementById("np-time-pos");
  const npTimeDur = document.getElementById("np-time-dur");
  const npProgressFill = document.getElementById("np-progress-fill");
  const npVolumeFill = document.getElementById("np-volume-fill");
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

    if (story && story.track_title) {
      npTrack.textContent = story.track_title;
      npTrack.hidden = false;
    } else {
      npTrack.hidden = true;
    }

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
