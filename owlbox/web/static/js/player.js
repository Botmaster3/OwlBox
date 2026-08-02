(function () {
  const coverImg = document.getElementById("cover");
  const coverPlaceholder = document.getElementById("cover-placeholder");
  const storyTitleEl = document.getElementById("story-title");
  const trackTitleEl = document.getElementById("track-title");
  const timePosEl = document.getElementById("time-pos");
  const timeDurEl = document.getElementById("time-dur");
  const progressFill = document.getElementById("progress-fill");
  const volumeFill = document.getElementById("volume-fill");
  const unknownBanner = document.getElementById("unknown-banner");

  let lastCoverUrl = null;

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
      storyTitleEl.textContent = story.title;
    } else if (state.unknown_tag) {
      storyTitleEl.textContent = "Unbekannter Chip";
    } else {
      storyTitleEl.textContent = "Kein Chip aufgelegt";
    }

    if (story && story.track_title) {
      trackTitleEl.textContent = story.track_title;
      trackTitleEl.hidden = false;
    } else {
      trackTitleEl.hidden = true;
    }

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
