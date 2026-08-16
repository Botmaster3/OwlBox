(function () {
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

  async function api(url, options) {
    const res = await fetch(url, options);
    const body = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(body.error || `HTTP ${res.status}`);
    return body;
  }

  function withErrorToast(fn) {
    return async (...args) => {
      try {
        await fn(...args);
      } catch (err) {
        showToast(err.message, true);
      }
    };
  }

  // -- Spiel-Medien-Pools (Bilder/Klänge/Rätsel) ---------------------------
  // Formerly a tab under Einstellungen ("Spiel") - moved to its own nav
  // entry since managing game media (uploading pictures/sounds/quiz items)
  // isn't really a *setting* the way volume limits or themes are, it's
  // ongoing content management, same category as the Bibliothek/Hinzufügen
  // pages. Memory-Bilder, Sound-Memory-Klänge und Tier-Sound-Quiz-Rätsel
  // sind drei unabhängige Pools, aber strukturell dasselbe: eine Liste
  // laden, pro Eintrag eine Zeile mit eigenem Löschen-Button rendern, nach
  // dem Löschen neu laden. Nur der Upload-Schritt unterscheidet sich genug
  // (Dateizahl, beim Quiz ein zusätzliches Textfeld), um pro Pool
  // eigenständig zu bleiben.
  function createMediaPool({ listUrl, deleteUrl, container, rowClass, emptyHint, rowHtml }) {
    function render(items) {
      container.innerHTML = "";
      emptyHint.hidden = items.length > 0;
      for (const item of items) {
        const row = document.createElement("div");
        row.className = rowClass;
        row.innerHTML = rowHtml(item);
        row.querySelector("[data-delete]").addEventListener("click", withErrorToast(async () => {
          await api(deleteUrl(item), { method: "DELETE" });
          load();
        }));
        container.appendChild(row);
      }
    }
    async function load() {
      try {
        render(await api(listUrl));
      } catch (err) {
        showToast(err.message, true);
      }
    }
    return { render, load };
  }

  // Memory game: image pool.
  const gameImagePool = createMediaPool({
    listUrl: "/api/game/images",
    deleteUrl: (img) => `/api/game/images/${img.id}`,
    container: document.getElementById("game-image-grid"),
    rowClass: "game-image-cell",
    emptyHint: document.getElementById("game-image-empty-hint"),
    rowHtml: (img) => `
      <img src="${img.url}" alt="">
      <button type="button" class="btn danger small" data-delete>🗑</button>
    `,
  });
  const gameImageUpload = document.getElementById("game-image-upload");
  document.getElementById("game-image-upload-btn").addEventListener("click", withErrorToast(async () => {
    const files = Array.from(gameImageUpload.files || []);
    if (files.length === 0) {
      showToast("Bitte zuerst Bilder auswählen.", true);
      return;
    }
    const formData = new FormData();
    files.forEach((f) => formData.append("images", f));
    const images = await api("/api/game/images", { method: "POST", body: formData });
    gameImagePool.render(images);
    gameImageUpload.value = "";
    showToast(`${files.length} Bild(er) hochgeladen.`);
  }));
  gameImagePool.load();

  // Sound-Memory: sound clip pool.
  const soundClipPool = createMediaPool({
    listUrl: "/api/sound/clips",
    deleteUrl: (clip) => `/api/sound/clips/${clip.id}`,
    container: document.getElementById("sound-clip-list"),
    rowClass: "sound-clip-row",
    emptyHint: document.getElementById("sound-clip-empty-hint"),
    rowHtml: (clip) => `
      <audio controls src="${clip.url}"></audio>
      <button type="button" class="btn danger small" data-delete>🗑</button>
    `,
  });
  const soundClipUpload = document.getElementById("sound-clip-upload");
  document.getElementById("sound-clip-upload-btn").addEventListener("click", withErrorToast(async () => {
    const files = Array.from(soundClipUpload.files || []);
    if (files.length === 0) {
      showToast("Bitte zuerst Klänge auswählen.", true);
      return;
    }
    const formData = new FormData();
    files.forEach((f) => formData.append("sounds", f));
    const clips = await api("/api/sound/clips", { method: "POST", body: formData });
    soundClipPool.render(clips);
    soundClipUpload.value = "";
    showToast(`${files.length} Klang/Klänge hochgeladen.`);
  }));
  soundClipPool.load();

  // Tier-Sound-Quiz: picture+sound item pool.
  const quizItemPool = createMediaPool({
    listUrl: "/api/quiz/items",
    deleteUrl: (item) => `/api/quiz/items/${item.id}`,
    container: document.getElementById("quiz-item-list"),
    rowClass: "quiz-item-row",
    emptyHint: document.getElementById("quiz-item-empty-hint"),
    rowHtml: (item) => `
      <img src="${item.image_url}" alt="">
      <audio controls src="${item.sound_url}"></audio>
      <span class="quiz-item-label">${item.label || ""}</span>
      <button type="button" class="btn danger small" data-delete>🗑</button>
    `,
  });
  const quizItemImageInput = document.getElementById("quiz-item-image");
  const quizItemSoundInput = document.getElementById("quiz-item-sound");
  const quizItemLabelInput = document.getElementById("quiz-item-label");
  document.getElementById("quiz-item-upload-btn").addEventListener("click", withErrorToast(async () => {
    const image = quizItemImageInput.files && quizItemImageInput.files[0];
    const sound = quizItemSoundInput.files && quizItemSoundInput.files[0];
    if (!image || !sound) {
      showToast("Bitte Bild und Ton auswählen.", true);
      return;
    }
    const formData = new FormData();
    formData.append("image", image);
    formData.append("sound", sound);
    if (quizItemLabelInput.value.trim()) formData.append("label", quizItemLabelInput.value.trim());
    const items = await api("/api/quiz/items", { method: "POST", body: formData });
    quizItemPool.render(items);
    quizItemImageInput.value = "";
    quizItemSoundInput.value = "";
    quizItemLabelInput.value = "";
    showToast("Rätsel hinzugefügt.");
  }));
  quizItemPool.load();
})();
