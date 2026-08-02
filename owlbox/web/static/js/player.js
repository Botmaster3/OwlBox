(function () {
  const coverImg = document.getElementById("cover");
  const coverPlaceholder = document.getElementById("cover-placeholder");
  const titleEl = document.getElementById("title");
  const timePosEl = document.getElementById("time-pos");
  const timeDurEl = document.getElementById("time-dur");
  const progressFill = document.getElementById("progress-fill");
  const toggleBtn = document.getElementById("btn-toggle");
  const nextBtn = document.getElementById("btn-next");
  const prevBtn = document.getElementById("btn-prev");
  const volumeSlider = document.getElementById("volume");
  const unknownBanner = document.getElementById("unknown-banner");

  let lastCoverUrl = null;
  let volumeBeingDragged = false;

  function formatTime(seconds) {
    seconds = Math.max(0, Math.floor(seconds || 0));
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return `${m}:${String(s).padStart(2, "0")}`;
  }

  function post(url, body) {
    return fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: body ? JSON.stringify(body) : undefined,
    });
  }

  function applyState(state) {
    const story = state.story;
    const player = state.player || {};

    if (story) {
      titleEl.textContent = story.title;
    } else if (state.unknown_tag) {
      titleEl.textContent = "Unbekannter Chip";
    } else {
      titleEl.textContent = "Kein Chip aufgelegt";
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

    toggleBtn.textContent = player.playing ? "⏸" : "▶️";

    if (!volumeBeingDragged) {
      volumeSlider.value = player.volume != null ? player.volume : volumeSlider.value;
    }

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

  toggleBtn.addEventListener("click", () => post("/api/control/toggle"));
  nextBtn.addEventListener("click", () => post("/api/control/next"));
  prevBtn.addEventListener("click", () => post("/api/control/prev"));

  volumeSlider.addEventListener("pointerdown", () => (volumeBeingDragged = true));
  volumeSlider.addEventListener("change", () => {
    post("/api/control/volume", { level: parseInt(volumeSlider.value, 10) });
    volumeBeingDragged = false;
  });

  poll();
})();
