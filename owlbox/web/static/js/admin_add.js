(function () {
  const AUDIO_EXTENSIONS = [".mp3", ".m4a", ".mp4", ".ogg", ".oga", ".flac", ".wav", ".opus"];
  const IMAGE_EXTENSIONS = [".jpg", ".jpeg", ".png", ".webp"];

  const createForm = document.getElementById("create-form");
  const createError = document.getElementById("create-error");
  const titleInput = document.getElementById("title");
  const coverInput = document.getElementById("cover");
  const coverAutoHint = document.getElementById("cover-auto-hint");
  const filesField = document.getElementById("files-field");
  const folderField = document.getElementById("folder-field");
  const audioFilesInput = document.getElementById("audio_files");
  const audioFolderInput = document.getElementById("audio_folder");
  const folderSummary = document.getElementById("folder-summary");
  const folderHint = document.getElementById("folder-hint");
  const toggleButtons = document.querySelectorAll("#source-toggle .segmented-btn");

  let mode = "files";
  let folderAudioFiles = [];
  let folderCoverFile = null;

  function extOf(filename) {
    const idx = filename.lastIndexOf(".");
    return idx === -1 ? "" : filename.slice(idx).toLowerCase();
  }

  function setMode(newMode) {
    mode = newMode;
    toggleButtons.forEach((btn) => btn.classList.toggle("active", btn.dataset.mode === mode));
    filesField.hidden = mode !== "files";
    folderField.hidden = mode !== "folder";
    folderHint.hidden = mode !== "folder";
    audioFilesInput.required = mode === "files";
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

  createForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    createError.textContent = "";

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

    try {
      const res = await fetch("/api/stories", { method: "POST", body: formData });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.error || `HTTP ${res.status}`);
      }
      window.location.href = "/admin";
    } catch (err) {
      createError.textContent = err.message;
    }
  });

  setMode("files");
})();
