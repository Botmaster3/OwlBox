(function () {
  const AUDIO_EXTENSIONS = [".mp3", ".m4a", ".mp4", ".ogg", ".oga", ".flac", ".wav", ".opus"];
  const IMAGE_EXTENSIONS = [".jpg", ".jpeg", ".png", ".webp"];

  const createForm = document.getElementById("create-form");
  const createError = document.getElementById("create-error");
  const titleInput = document.getElementById("title");
  const coverField = document.getElementById("cover-field");
  const coverInput = document.getElementById("cover");
  const coverAutoHint = document.getElementById("cover-auto-hint");
  const filesField = document.getElementById("files-field");
  const folderField = document.getElementById("folder-field");
  const streamField = document.getElementById("stream-field");
  const playlistField = document.getElementById("playlist-field");
  const playlistSelectedField = document.getElementById("playlist-selected-field");
  const audioFilesInput = document.getElementById("audio_files");
  const audioFolderInput = document.getElementById("audio_folder");
  const streamUrlInput = document.getElementById("stream_url");
  const folderSummary = document.getElementById("folder-summary");
  const folderHint = document.getElementById("folder-hint");
  const streamHint = document.getElementById("stream-hint");
  const playlistHint = document.getElementById("playlist-hint");
  const playlistSearch = document.getElementById("playlist-search");
  const playlistAvailable = document.getElementById("playlist-available");
  const playlistSelectedList = document.getElementById("playlist-selected");
  const playlistSelectedCount = document.getElementById("playlist-selected-count");
  const toggleButtons = document.querySelectorAll("#source-toggle .segmented-btn");

  let mode = "files";
  let folderAudioFiles = [];
  let folderCoverFile = null;
  let allTracks = null; // null = not fetched yet
  let selectedTracks = [];

  function formatDuration(seconds) {
    if (!seconds) return "";
    seconds = Math.floor(seconds);
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return ` (${m}:${String(s).padStart(2, "0")})`;
  }

  async function loadAllTracks() {
    if (allTracks !== null) return;
    playlistAvailable.innerHTML = '<p class="hint">Lädt…</p>';
    try {
      const res = await fetch("/api/tracks");
      allTracks = res.ok ? await res.json() : [];
    } catch (err) {
      allTracks = [];
    }
    renderAvailableTracks();
  }

  function renderAvailableTracks() {
    const query = playlistSearch.value.trim().toLowerCase();
    const selectedIds = new Set(selectedTracks.map((t) => t.id));
    const candidates = (allTracks || []).filter((t) => {
      if (selectedIds.has(t.id)) return false;
      if (!query) return true;
      return t.title.toLowerCase().includes(query) || t.story_title.toLowerCase().includes(query);
    });

    playlistAvailable.innerHTML = "";
    if (candidates.length === 0) {
      playlistAvailable.innerHTML = `<p class="hint" style="padding:8px 12px;">${
        allTracks && allTracks.length === 0 ? "Noch keine Titel in der Bibliothek." : "Keine Treffer."
      }</p>`;
      return;
    }
    for (const track of candidates) {
      const row = document.createElement("div");
      row.className = "playlist-track-row";
      row.innerHTML = `
        <div class="playlist-track-info">
          <div class="playlist-track-title">${track.title}${formatDuration(track.duration)}</div>
          <div class="playlist-track-story">${track.story_title}</div>
        </div>
        <button type="button" class="btn secondary small">+ Hinzufügen</button>
      `;
      row.querySelector("button").addEventListener("click", () => {
        selectedTracks.push(track);
        renderAvailableTracks();
        renderSelectedTracks();
      });
      playlistAvailable.appendChild(row);
    }
  }

  function renderSelectedTracks() {
    playlistSelectedCount.textContent = selectedTracks.length;
    playlistSelectedList.innerHTML = "";
    selectedTracks.forEach((track, index) => {
      const li = document.createElement("li");
      li.className = "playlist-track-row";
      li.innerHTML = `
        <span class="track-order">
          <button type="button" data-action="up" ${index === 0 ? "disabled" : ""}>▲</button>
          <button type="button" data-action="down" ${index === selectedTracks.length - 1 ? "disabled" : ""}>▼</button>
        </span>
        <div class="playlist-track-info">
          <div class="playlist-track-title">${index + 1}. ${track.title}${formatDuration(track.duration)}</div>
          <div class="playlist-track-story">${track.story_title}</div>
        </div>
        <button type="button" class="btn secondary small" data-action="remove">Entfernen</button>
      `;
      li.querySelector('[data-action="up"]').addEventListener("click", () => {
        [selectedTracks[index - 1], selectedTracks[index]] = [selectedTracks[index], selectedTracks[index - 1]];
        renderSelectedTracks();
      });
      li.querySelector('[data-action="down"]').addEventListener("click", () => {
        [selectedTracks[index + 1], selectedTracks[index]] = [selectedTracks[index], selectedTracks[index + 1]];
        renderSelectedTracks();
      });
      li.querySelector('[data-action="remove"]').addEventListener("click", () => {
        selectedTracks.splice(index, 1);
        renderSelectedTracks();
        renderAvailableTracks();
      });
      playlistSelectedList.appendChild(li);
    });
  }

  playlistSearch.addEventListener("input", renderAvailableTracks);

  function showToast(message, isError) {
    let toast = document.getElementById("toast");
    if (!toast) {
      toast = document.createElement("div");
      toast.id = "toast";
      toast.className = "toast";
      document.body.appendChild(toast);
    }
    toast.textContent = message;
    toast.classList.toggle("error", !!isError);
    toast.classList.add("show");
    clearTimeout(toast._hideTimeout);
    toast._hideTimeout = setTimeout(() => toast.classList.remove("show"), 2500);
  }

  function extOf(filename) {
    const idx = filename.lastIndexOf(".");
    return idx === -1 ? "" : filename.slice(idx).toLowerCase();
  }

  function setMode(newMode) {
    mode = newMode;
    toggleButtons.forEach((btn) => btn.classList.toggle("active", btn.dataset.mode === mode));
    filesField.hidden = mode !== "files";
    folderField.hidden = mode !== "folder";
    streamField.hidden = mode !== "stream";
    playlistField.hidden = mode !== "playlist";
    playlistSelectedField.hidden = mode !== "playlist";
    coverField.hidden = mode === "playlist";
    folderHint.hidden = mode !== "folder";
    streamHint.hidden = mode !== "stream";
    playlistHint.hidden = mode !== "playlist";
    audioFilesInput.required = mode === "files";
    if (mode === "playlist") loadAllTracks();
  }

  toggleButtons.forEach((btn) => {
    btn.addEventListener("click", () => setMode(btn.dataset.mode));
  });

  audioFolderInput.addEventListener("change", () => {
    const allFiles = Array.from(audioFolderInput.files);
    if (allFiles.length === 0) {
      folderAudioFiles = [];
      folderCoverFile = null;
      folderSummary.textContent = "";
      coverAutoHint.hidden = true;
      return;
    }

    allFiles.sort((a, b) => a.webkitRelativePath.localeCompare(b.webkitRelativePath));

    folderAudioFiles = allFiles.filter((f) => AUDIO_EXTENSIONS.includes(extOf(f.name)));
    const imageCandidates = allFiles.filter((f) => IMAGE_EXTENSIONS.includes(extOf(f.name)));
    folderCoverFile = imageCandidates.find((f) => /^(cover|folder|art)\./i.test(f.name)) || imageCandidates[0] || null;

    folderSummary.textContent =
      `${folderAudioFiles.length} Audiodatei(en) gefunden` + (folderCoverFile ? `, Cover: ${folderCoverFile.name}` : "");

    if (folderCoverFile) {
      coverAutoHint.hidden = false;
      coverAutoHint.textContent = `Automatisch erkannt: ${folderCoverFile.name} (manuelle Auswahl oben überschreibt das)`;
    } else {
      coverAutoHint.hidden = true;
    }

    if (!titleInput.value.trim() && allFiles[0].webkitRelativePath) {
      titleInput.value = allFiles[0].webkitRelativePath.split("/")[0];
    }
  });

  async function submitPlaylist() {
    if (selectedTracks.length === 0) {
      createError.textContent = "Bitte mindestens einen Titel zur Playlist hinzufügen.";
      return false;
    }
    const submitBtn = createForm.querySelector('button[type="submit"]');
    submitBtn.disabled = true;
    try {
      const res = await fetch("/api/stories/from-tracks", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title: titleInput.value,
          track_ids: selectedTracks.map((t) => t.id),
          cover_story_id: selectedTracks[0].story_id,
        }),
      });
      const body = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(body.error || `HTTP ${res.status}`);
      }
      showToast(`"${body.title}" wurde als Playlist angelegt.`);
      setTimeout(() => {
        window.location.href = "/admin/library";
      }, 900);
    } catch (err) {
      createError.textContent = err.message;
      showToast(err.message, true);
      submitBtn.disabled = false;
    }
    return true;
  }

  createForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    createError.textContent = "";

    if (mode === "playlist") {
      await submitPlaylist();
      return;
    }

    const manualCover = coverInput.files[0];
    const formData = new FormData();
    formData.append("title", titleInput.value);

    if (mode === "folder") {
      if (folderAudioFiles.length === 0) {
        createError.textContent = "Der ausgewählte Ordner enthält keine unterstützten Audiodateien.";
        return;
      }
      for (const f of folderAudioFiles) {
        formData.append("audio_files", f, f.name);
      }
      const cover = manualCover || folderCoverFile;
      if (cover) formData.append("cover", cover, cover.name);
    } else if (mode === "stream") {
      const url = streamUrlInput.value.trim();
      if (!url.startsWith("http://") && !url.startsWith("https://")) {
        createError.textContent = "Bitte eine gültige URL eingeben (http:// oder https://).";
        return;
      }
      formData.append("stream_url", url);
      if (manualCover) formData.append("cover", manualCover, manualCover.name);
    } else {
      if (audioFilesInput.files.length === 0) {
        createError.textContent = "Bitte mindestens eine Audiodatei auswählen.";
        return;
      }
      for (const f of audioFilesInput.files) {
        formData.append("audio_files", f, f.name);
      }
      if (manualCover) formData.append("cover", manualCover, manualCover.name);
    }

    const submitBtn = createForm.querySelector('button[type="submit"]');
    submitBtn.disabled = true;
    try {
      const res = await fetch("/api/stories", { method: "POST", body: formData });
      const body = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(body.error || `HTTP ${res.status}`);
      }
      showToast(`"${body.title}" wurde hinzugefügt.`);
      setTimeout(() => {
        window.location.href = "/admin/library";
      }, 900);
    } catch (err) {
      createError.textContent = err.message;
      showToast(err.message, true);
      submitBtn.disabled = false;
    }
  });

  setMode("files");
})();
