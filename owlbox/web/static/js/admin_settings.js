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

  // -- tabs ---------------------------------------------------------------
  // Real tabs, not anchor-jump-to-scroll: exactly one .settings-panel is
  // ever in the visible flow (the rest sit behind [hidden]), so switching
  // never scrolls the page. Still reads/writes the #section-<name> hash so
  // an existing bookmark/link opens on the right tab, it just no longer
  // relies on native anchor-scroll to get there.

  (function () {
    const tabs = Array.from(document.querySelectorAll(".settings-tab"));
    const panels = Array.from(document.querySelectorAll(".settings-panel"));
    const names = panels.map((panel) => panel.dataset.panel);

    function activate(name) {
      tabs.forEach((tab) => tab.classList.toggle("active", tab.dataset.panel === name));
      panels.forEach((panel) => { panel.hidden = panel.dataset.panel !== name; });
    }

    const fromHash = location.hash.replace(/^#section-/, "");
    activate(names.includes(fromHash) ? fromHash : names[0]);

    tabs.forEach((tab) => {
      tab.addEventListener("click", () => {
        activate(tab.dataset.panel);
        history.replaceState(null, "", "#section-" + tab.dataset.panel);
      });
    });
  })();

  // -- system (restart/shutdown) ---------------------------------------------

  const systemStatus = document.getElementById("system-status");

  document.getElementById("restart-btn").addEventListener("click", async () => {
    if (!confirm("Pi jetzt neu starten?")) return;
    systemStatus.textContent = "Startet neu…";
    try {
      await api("/api/system/restart", { method: "POST" });
    } catch (err) {
      systemStatus.textContent = err.message;
    }
  });

  document.getElementById("shutdown-btn").addEventListener("click", async () => {
    if (!confirm("Pi jetzt herunterfahren? Danach muss er per Stecker/Schalter wieder eingeschaltet werden.")) return;
    systemStatus.textContent = "Fährt herunter…";
    try {
      await api("/api/system/shutdown", { method: "POST" });
    } catch (err) {
      systemStatus.textContent = err.message;
    }
  });

  // -- hostname -----------------------------------------------------------

  const hostnameCurrent = document.getElementById("hostname-current");
  const hostnameInput = document.getElementById("hostname-input");
  const hostnameStatus = document.getElementById("hostname-status");

  (async () => {
    try {
      const data = await api("/api/system/hostname");
      hostnameCurrent.textContent = data.hostname;
      hostnameInput.value = data.hostname;
    } catch (err) {
      hostnameCurrent.textContent = "unbekannt";
    }
  })();

  document.getElementById("hostname-save-btn").addEventListener("click", async () => {
    hostnameStatus.textContent = "Ändert…";
    try {
      const data = await api("/api/system/hostname", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ hostname: hostnameInput.value }),
      });
      hostnameCurrent.textContent = data.hostname;
      hostnameInput.value = data.hostname;
      hostnameStatus.textContent = `Gespeichert als „${data.hostname}“ - für volle Erreichbarkeit im Netzwerk jetzt neu starten.`;
    } catch (err) {
      hostnameStatus.textContent = err.message;
    }
  });

  // -- volume -----------------------------------------------------------------

  const currentVolumeInput = document.getElementById("current-volume");
  const currentVolumeValue = document.getElementById("current-volume-value");
  const maxVolumeInput = document.getElementById("max-volume");
  const volumeStepInput = document.getElementById("volume-step");
  const volumeSaveBtn = document.getElementById("volume-save-btn");

  let volumeSliderBeingDragged = false;

  currentVolumeInput.addEventListener("input", () => {
    volumeSliderBeingDragged = true;
    currentVolumeValue.textContent = currentVolumeInput.value;
  });
  currentVolumeInput.addEventListener("change", async () => {
    try {
      await api("/api/settings/volume", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ current_volume: parseInt(currentVolumeInput.value, 10) }),
      });
    } catch (err) {
      showToast(err.message, true);
    }
    volumeSliderBeingDragged = false;
  });

  volumeSaveBtn.addEventListener("click", async () => {
    try {
      const settings = await api("/api/settings/volume", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          max_volume: parseInt(maxVolumeInput.value, 10),
          volume_step: parseInt(volumeStepInput.value, 10),
        }),
      });
      // Reflect back the server's (clamped) values in case the input was out of range.
      maxVolumeInput.value = settings.max_volume;
      volumeStepInput.value = settings.volume_step;
      showToast("Lautstärke-Einstellungen gespeichert.");
    } catch (err) {
      showToast(err.message, true);
    }
  });

  // -- design theme ---------------------------------------------------------

  const themePicker = document.getElementById("theme-picker");
  const themeAutoStatus = document.getElementById("theme-auto-status");
  const themeAutoCheckboxes = document.querySelectorAll(".theme-auto-checkbox");
  const customThemeEditor = document.getElementById("custom-theme-editor");
  const customThemeInputs = customThemeEditor ? customThemeEditor.querySelectorAll("[data-custom-var]") : [];
  const customBarRadiusSelect = document.getElementById("custom-bar-radius");
  const customThemeSaveBtn = document.getElementById("custom-theme-save-btn");

  // Built from the picker's own swatch labels rather than duplicating the
  // German theme names in JS - one source of truth (the Jinja template).
  const themeLabels = {};
  if (themePicker) {
    themePicker.querySelectorAll("[data-theme-id]").forEach((btn) => {
      const labelEl = btn.querySelector(".theme-swatch-label span");
      if (labelEl) themeLabels[btn.dataset.themeId] = labelEl.textContent;
    });
  }

  function themeLabel(id) {
    return themeLabels[id] || id;
  }

  // The "custom" theme's colors live as inline CSS custom properties on
  // <html> (see base.html/web/__init__.py) instead of a static per-theme
  // CSS block, since they're user-supplied - applied/cleared here the same
  // way, so switching to/away from "custom" updates this page live too,
  // not just the kiosk display.
  const CUSTOM_THEME_VAR_NAMES = [
    "bg", "panel", "accent", "accent-dim", "text", "text-dim", "border", "input-bg", "on-accent", "bar-radius",
  ];
  function applyCustomThemeVars(theme, colors) {
    if (theme === "custom" && colors) {
      for (const [key, value] of Object.entries(colors)) {
        document.documentElement.style.setProperty(`--${key.replace(/_/g, "-")}`, value);
      }
    } else {
      CUSTOM_THEME_VAR_NAMES.forEach((name) => document.documentElement.style.removeProperty(`--${name}`));
    }
  }

  function applyThemeSettings(settings) {
    document.documentElement.dataset.theme = settings.theme;
    applyCustomThemeVars(settings.theme, settings.custom_theme_colors);
    if (themePicker) {
      themePicker.querySelectorAll("[data-theme-id]").forEach((btn) => {
        btn.classList.toggle("active", btn.dataset.themeId === settings.theme);
      });
    }
    themeAutoCheckboxes.forEach((checkbox) => {
      checkbox.checked = !!settings.auto_theme_enabled[checkbox.dataset.themeId];
    });
    if (themeAutoStatus) {
      const favorite = `<strong>${themeLabel(settings.manual_theme)}</strong>`;
      const hint = "Ein Klick auf ein Design unten wählt es sofort aus.";
      themeAutoStatus.innerHTML = settings.seasonal_theme_active
        ? `🎉 Gerade automatisch aktiv: <strong>${themeLabel(settings.seasonal_theme_active)}</strong> - dein gespeicherter Favorit ${favorite} läuft danach weiter. ${hint}`
        : `Gerade ist keine automatische Zeit aktiv - es gilt dein gespeicherter Favorit ${favorite}. ${hint}`;
    }
  }

  if (themePicker) {
    themePicker.querySelectorAll("[data-theme-id]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const id = btn.dataset.themeId;
        // Apply immediately for instant feedback, persist in the background -
        // a theme choice isn't destructive, so there's nothing to gain from
        // waiting on the round-trip before showing the new look.
        document.documentElement.dataset.theme = id;
        themePicker.querySelectorAll("[data-theme-id]").forEach((other) => {
          other.classList.toggle("active", other === btn);
        });
        try {
          const settings = await api("/api/settings/theme", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ theme: id }),
          });
          applyThemeSettings(settings);
        } catch (err) {
          showToast(err.message, true);
        }
      });
    });
  }

  themeAutoCheckboxes.forEach((checkbox) => {
    checkbox.addEventListener("change", async () => {
      const enabled = checkbox.checked;
      try {
        const settings = await api("/api/settings/theme/auto", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ theme: checkbox.dataset.themeId, enabled }),
        });
        applyThemeSettings(settings);
      } catch (err) {
        checkbox.checked = !enabled;
        showToast(err.message, true);
      }
    });
  });

  if (customThemeSaveBtn) {
    customThemeSaveBtn.addEventListener("click", async () => {
      try {
        const colors = {};
        customThemeInputs.forEach((input) => {
          colors[input.dataset.customVar] = input.value;
        });
        if (customBarRadiusSelect) colors.bar_radius = customBarRadiusSelect.value;
        const settings = await api("/api/settings/theme/custom", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(colors),
        });
        applyThemeSettings(settings);
        showToast("Eigenes Design gespeichert und aktiviert.");
      } catch (err) {
        showToast(err.message, true);
      }
    });
  }

  // -- acoustic feedback (scan chimes) -------------------------------------

  const chimeVolumePercentInput = document.getElementById("chime-volume-percent");
  const chimeTypeInputs = {
    known: document.getElementById("chime-type-known"),
    unknown: document.getElementById("chime-type-unknown"),
    function: document.getElementById("chime-type-function"),
    startup: document.getElementById("chime-type-startup"),
    shutdown: document.getElementById("chime-type-shutdown"),
  };
  const chimeSaveBtn = document.getElementById("chime-save-btn");

  chimeSaveBtn.addEventListener("click", async () => {
    try {
      const chimeEnabled = {};
      for (const [name, input] of Object.entries(chimeTypeInputs)) {
        chimeEnabled[name] = input.checked;
      }
      const settings = await api("/api/settings/chime", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          chime_volume_percent: parseInt(chimeVolumePercentInput.value, 10),
          chime_enabled: chimeEnabled,
        }),
      });
      chimeVolumePercentInput.value = settings.chime_volume_percent;
      for (const [name, input] of Object.entries(chimeTypeInputs)) {
        input.checked = settings.chime_enabled[name];
      }
      showToast("Akustisches Feedback gespeichert.");
    } catch (err) {
      showToast(err.message, true);
    }
  });

  const chimeTestStatus = document.getElementById("chime-test-status");

  async function testChime(name, button) {
    const originalText = button.textContent;
    button.disabled = true;
    chimeTestStatus.textContent = "Spielt…";
    try {
      await api("/api/settings/chime/test", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name,
          chime_volume_percent: parseInt(chimeVolumePercentInput.value, 10),
        }),
      });
      chimeTestStatus.textContent = "";
    } catch (err) {
      chimeTestStatus.textContent = err.message;
    } finally {
      button.disabled = false;
      button.textContent = originalText;
    }
  }

  document.getElementById("chime-test-btn").addEventListener("click", (e) => {
    testChime("known", e.currentTarget);
  });

  document.querySelectorAll("[data-chime-test]").forEach((btn) => {
    btn.addEventListener("click", () => testChime(btn.dataset.chimeTest, btn));
  });

  // -- display brightness -------------------------------------------------

  const currentBrightnessInput = document.getElementById("current-brightness");
  const currentBrightnessValue = document.getElementById("current-brightness-value");
  const minBrightnessInput = document.getElementById("min-brightness");
  const maxBrightnessInput = document.getElementById("max-brightness");
  const brightnessStepInput = document.getElementById("brightness-step");
  const brightnessSaveBtn = document.getElementById("brightness-save-btn");

  let brightnessSliderBeingDragged = false;

  currentBrightnessInput.addEventListener("input", () => {
    brightnessSliderBeingDragged = true;
    currentBrightnessValue.textContent = currentBrightnessInput.value;
  });
  currentBrightnessInput.addEventListener("change", async () => {
    try {
      await api("/api/settings/brightness", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ brightness: parseInt(currentBrightnessInput.value, 10) }),
      });
    } catch (err) {
      showToast(err.message, true);
    }
    brightnessSliderBeingDragged = false;
  });

  brightnessSaveBtn.addEventListener("click", async () => {
    try {
      const settings = await api("/api/settings/brightness", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          min_brightness: parseInt(minBrightnessInput.value, 10),
          max_brightness: parseInt(maxBrightnessInput.value, 10),
          brightness_step: parseInt(brightnessStepInput.value, 10),
        }),
      });
      // Reflect back the server's (clamped) values in case the input was out of range.
      minBrightnessInput.value = settings.min_brightness;
      maxBrightnessInput.value = settings.max_brightness;
      brightnessStepInput.value = settings.brightness_step;
      currentBrightnessInput.min = settings.min_brightness;
      currentBrightnessInput.max = settings.max_brightness;
      currentBrightnessInput.value = settings.brightness;
      currentBrightnessValue.textContent = settings.brightness;
      showToast("Helligkeits-Grenzen gespeichert.");
    } catch (err) {
      showToast(err.message, true);
    }
  });

  // -- night mode -----------------------------------------------------------

  const nightBrightnessInput = document.getElementById("night-brightness");
  const nightBrightnessSaveBtn = document.getElementById("night-brightness-save-btn");
  const nightModeToggleBtn = document.getElementById("night-mode-toggle-btn");
  let nightModeActive = false;

  function renderNightModeToggle() {
    nightModeToggleBtn.textContent = `🌙 Nachtmodus: ${nightModeActive ? "An" : "Aus"}`;
    nightModeToggleBtn.classList.toggle("active", nightModeActive);
  }

  nightBrightnessSaveBtn.addEventListener("click", async () => {
    try {
      const settings = await api("/api/settings/brightness", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ night_brightness: parseInt(nightBrightnessInput.value, 10) }),
      });
      nightBrightnessInput.value = settings.night_brightness;
      showToast("Nachtmodus-Helligkeit gespeichert.");
    } catch (err) {
      showToast(err.message, true);
    }
  });

  nightModeToggleBtn.addEventListener("click", async () => {
    try {
      const settings = await api("/api/settings/brightness", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ night_mode_active: !nightModeActive }),
      });
      nightModeActive = settings.night_mode_active;
      renderNightModeToggle();
      currentBrightnessInput.value = settings.brightness;
      currentBrightnessValue.textContent = settings.brightness;
    } catch (err) {
      showToast(err.message, true);
    }
  });

  // -- Memory game: image pool --------------------------------------------

  const gameImageUpload = document.getElementById("game-image-upload");
  const gameImageUploadBtn = document.getElementById("game-image-upload-btn");
  const gameImageGrid = document.getElementById("game-image-grid");
  const gameImageEmptyHint = document.getElementById("game-image-empty-hint");

  function renderGameImages(images) {
    gameImageGrid.innerHTML = "";
    gameImageEmptyHint.hidden = images.length > 0;
    for (const img of images) {
      const cell = document.createElement("div");
      cell.className = "game-image-cell";
      cell.innerHTML = `
        <img src="${img.url}" alt="">
        <button type="button" class="btn danger small" data-delete-image="${img.id}">🗑</button>
      `;
      cell.querySelector("[data-delete-image]").addEventListener("click", async () => {
        try {
          await api(`/api/game/images/${img.id}`, { method: "DELETE" });
          loadGameImages();
        } catch (err) {
          showToast(err.message, true);
        }
      });
      gameImageGrid.appendChild(cell);
    }
  }

  async function loadGameImages() {
    try {
      renderGameImages(await api("/api/game/images"));
    } catch (err) {
      // ignore - tab may just not be visible yet on first load
    }
  }

  gameImageUploadBtn.addEventListener("click", async () => {
    const files = Array.from(gameImageUpload.files || []);
    if (files.length === 0) {
      showToast("Bitte zuerst Bilder auswählen.", true);
      return;
    }
    const formData = new FormData();
    files.forEach((f) => formData.append("images", f));
    try {
      const images = await api("/api/game/images", { method: "POST", body: formData });
      renderGameImages(images);
      gameImageUpload.value = "";
      showToast(`${files.length} Bild(er) hochgeladen.`);
    } catch (err) {
      showToast(err.message, true);
    }
  });

  loadGameImages();

  // -- Sound-Memory: sound clip pool ---------------------------------------

  const soundClipUpload = document.getElementById("sound-clip-upload");
  const soundClipUploadBtn = document.getElementById("sound-clip-upload-btn");
  const soundClipList = document.getElementById("sound-clip-list");
  const soundClipEmptyHint = document.getElementById("sound-clip-empty-hint");

  function renderSoundClips(clips) {
    soundClipList.innerHTML = "";
    soundClipEmptyHint.hidden = clips.length > 0;
    for (const clip of clips) {
      const row = document.createElement("div");
      row.className = "sound-clip-row";
      row.innerHTML = `
        <audio controls src="${clip.url}"></audio>
        <button type="button" class="btn danger small" data-delete-clip="${clip.id}">🗑</button>
      `;
      row.querySelector("[data-delete-clip]").addEventListener("click", async () => {
        try {
          await api(`/api/sound/clips/${clip.id}`, { method: "DELETE" });
          loadSoundClips();
        } catch (err) {
          showToast(err.message, true);
        }
      });
      soundClipList.appendChild(row);
    }
  }

  async function loadSoundClips() {
    try {
      renderSoundClips(await api("/api/sound/clips"));
    } catch (err) {
      // ignore - tab may just not be visible yet on first load
    }
  }

  soundClipUploadBtn.addEventListener("click", async () => {
    const files = Array.from(soundClipUpload.files || []);
    if (files.length === 0) {
      showToast("Bitte zuerst Klänge auswählen.", true);
      return;
    }
    const formData = new FormData();
    files.forEach((f) => formData.append("sounds", f));
    try {
      const clips = await api("/api/sound/clips", { method: "POST", body: formData });
      renderSoundClips(clips);
      soundClipUpload.value = "";
      showToast(`${files.length} Klang/Klänge hochgeladen.`);
    } catch (err) {
      showToast(err.message, true);
    }
  });

  loadSoundClips();

  // -- Tier-Sound-Quiz: picture+sound item pool ----------------------------

  const quizItemImageInput = document.getElementById("quiz-item-image");
  const quizItemSoundInput = document.getElementById("quiz-item-sound");
  const quizItemLabelInput = document.getElementById("quiz-item-label");
  const quizItemUploadBtn = document.getElementById("quiz-item-upload-btn");
  const quizItemList = document.getElementById("quiz-item-list");
  const quizItemEmptyHint = document.getElementById("quiz-item-empty-hint");

  function renderQuizItems(items) {
    quizItemList.innerHTML = "";
    quizItemEmptyHint.hidden = items.length > 0;
    for (const item of items) {
      const row = document.createElement("div");
      row.className = "quiz-item-row";
      row.innerHTML = `
        <img src="${item.image_url}" alt="">
        <audio controls src="${item.sound_url}"></audio>
        <span class="quiz-item-label">${item.label || ""}</span>
        <button type="button" class="btn danger small" data-delete-item="${item.id}">🗑</button>
      `;
      row.querySelector("[data-delete-item]").addEventListener("click", async () => {
        try {
          await api(`/api/quiz/items/${item.id}`, { method: "DELETE" });
          loadQuizItems();
        } catch (err) {
          showToast(err.message, true);
        }
      });
      quizItemList.appendChild(row);
    }
  }

  async function loadQuizItems() {
    try {
      renderQuizItems(await api("/api/quiz/items"));
    } catch (err) {
      // ignore - tab may just not be visible yet on first load
    }
  }

  quizItemUploadBtn.addEventListener("click", async () => {
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
    try {
      const items = await api("/api/quiz/items", { method: "POST", body: formData });
      renderQuizItems(items);
      quizItemImageInput.value = "";
      quizItemSoundInput.value = "";
      quizItemLabelInput.value = "";
      showToast("Rätsel hinzugefügt.");
    } catch (err) {
      showToast(err.message, true);
    }
  });

  loadQuizItems();

  // -- auto-sleep (sleeping-owl screen) ----------------------------------

  const autoSleepStatus = document.getElementById("auto-sleep-status");
  const autoSleepMinutesInput = document.getElementById("auto-sleep-minutes");
  const autoSleepSaveBtn = document.getElementById("auto-sleep-save-btn");

  autoSleepSaveBtn.addEventListener("click", async () => {
    try {
      const settings = await api("/api/settings/auto-sleep", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ auto_sleep_minutes: parseInt(autoSleepMinutesInput.value, 10) }),
      });
      autoSleepMinutesInput.value = settings.auto_sleep_minutes;
      showToast("Automatischer Ruhemodus gespeichert.");
    } catch (err) {
      showToast(err.message, true);
    }
  });

  // -- sleep timer --------------------------------------------------------

  const sleepTimerStatus = document.getElementById("sleep-timer-status");
  const sleepTimerCustom = document.getElementById("sleep-timer-custom");
  const sleepTimerStartBtn = document.getElementById("sleep-timer-start-btn");
  const sleepTimerCancelBtn = document.getElementById("sleep-timer-cancel-btn");

  function formatMinutesSeconds(totalSeconds) {
    const m = Math.floor(totalSeconds / 60);
    const s = totalSeconds % 60;
    return `${m}:${String(s).padStart(2, "0")}`;
  }

  async function startTimer(minutes) {
    try {
      await api("/api/sleep-timer", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ minutes }),
      });
      showToast(`Einschlaf-Timer über ${minutes} Minuten gestartet.`);
    } catch (err) {
      showToast(err.message, true);
    }
  }

  document.querySelectorAll("[data-minutes]").forEach((btn) => {
    btn.addEventListener("click", () => startTimer(parseFloat(btn.dataset.minutes)));
  });

  sleepTimerStartBtn.addEventListener("click", () => {
    const minutes = parseFloat(sleepTimerCustom.value);
    if (!minutes || minutes <= 0) {
      showToast("Bitte eine gültige Minutenzahl eingeben.", true);
      return;
    }
    startTimer(minutes);
  });

  sleepTimerCancelBtn.addEventListener("click", async () => {
    try {
      await api("/api/sleep-timer", { method: "DELETE" });
      showToast("Einschlaf-Timer abgebrochen.");
    } catch (err) {
      showToast(err.message, true);
    }
  });

  // -- Weckmodus (daily alarm) ---------------------------------------------

  const alarmStatus = document.getElementById("alarm-status");
  const alarmEnabledInput = document.getElementById("alarm-enabled");
  const alarmTimeInput = document.getElementById("alarm-time");
  const alarmStorySelect = document.getElementById("alarm-story");
  const alarmFadeSecondsInput = document.getElementById("alarm-fade-seconds");
  const alarmSaveBtn = document.getElementById("alarm-save-btn");

  async function loadAlarmStoryOptions() {
    try {
      const stories = await api("/api/stories");
      for (const story of stories) {
        const option = document.createElement("option");
        option.value = story.id;
        option.textContent = story.title;
        alarmStorySelect.appendChild(option);
      }
    } catch (err) {
      // ignore - the dropdown just stays at its placeholder option
    }
  }

  function renderAlarmStatus(alarm) {
    if (!alarm.enabled) {
      alarmStatus.textContent = "Weckmodus aus.";
    } else if (alarm.story_title) {
      alarmStatus.textContent = `Weckmodus: ${alarm.time} Uhr - „${alarm.story_title}“.`;
    } else {
      alarmStatus.textContent = `Weckmodus: ${alarm.time} Uhr - keine Geschichte ausgewählt (wird nicht auslösen).`;
    }
  }

  alarmSaveBtn.addEventListener("click", async () => {
    try {
      const alarm = await api("/api/settings/alarm", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          alarm_enabled: alarmEnabledInput.checked,
          alarm_time: alarmTimeInput.value || "07:00",
          alarm_story_id: alarmStorySelect.value || null,
          alarm_fade_seconds: parseInt(alarmFadeSecondsInput.value, 10) || 0,
        }),
      });
      renderAlarmStatus(alarm);
      showToast("Weckmodus gespeichert.");
    } catch (err) {
      showToast(err.message, true);
    }
  });

  // -- wifi ---------------------------------------------------------------

  const wifiStatus = document.getElementById("wifi-status");
  const wifiToggleBtn = document.getElementById("wifi-toggle-btn");
  const wifiScanBtn = document.getElementById("wifi-scan-btn");
  const wifiNetworks = document.getElementById("wifi-networks");
  const wifiConnectField = document.getElementById("wifi-connect-field");
  const wifiConnectSsid = document.getElementById("wifi-connect-ssid");
  const wifiPassword = document.getElementById("wifi-password");
  const wifiConnectBtn = document.getElementById("wifi-connect-btn");
  const wifiConnectStatus = document.getElementById("wifi-connect-status");
  const hotspotBanner = document.getElementById("hotspot-banner");
  const hotspotSsidEl = document.getElementById("hotspot-ssid");
  const hotspotPasswordEl = document.getElementById("hotspot-password");
  const hotspotUrlEl = document.getElementById("hotspot-url");

  let wifiEnabled = true;
  let selectedSsid = null;

  // The recovery hotspot's state lives on the engine (see engine.py), not in
  // network.get_status() - fed from the state poll below instead of a
  // separate fetch loop.
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

  async function refreshWifiStatus() {
    try {
      const status = await api("/api/network/status");
      wifiEnabled = status.enabled;
      wifiToggleBtn.textContent = wifiEnabled ? "WLAN ausschalten" : "WLAN einschalten";
      wifiStatus.textContent = !wifiEnabled
        ? "WLAN ist ausgeschaltet."
        : status.connected_ssid
        ? `Verbunden mit "${status.connected_ssid}"${status.ip_address ? " · " + status.ip_address : ""}`
        : "Nicht verbunden.";
    } catch (err) {
      wifiStatus.textContent = "Status konnte nicht geladen werden.";
    }
  }

  wifiToggleBtn.addEventListener("click", async () => {
    try {
      await api("/api/network/wifi-power", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ enabled: !wifiEnabled }),
      });
      setTimeout(refreshWifiStatus, 1500);
    } catch (err) {
      showToast(err.message, true);
    }
  });

  wifiScanBtn.addEventListener("click", async () => {
    wifiNetworks.innerHTML = '<p class="hint">Suche…</p>';
    try {
      const networks = await api("/api/network/scan");
      wifiNetworks.innerHTML = "";
      if (networks.length === 0) {
        wifiNetworks.innerHTML = '<p class="hint">Keine Netzwerke gefunden.</p>';
        return;
      }
      for (const net of networks) {
        const row = document.createElement("div");
        row.className = "story-row";
        row.innerHTML = `
          <div class="story-meta">
            <div class="row-title">${net.ssid}</div>
            <div class="story-sub">${net.signal != null ? net.signal + "%" : ""}</div>
          </div>
          <div class="story-actions">
            <button class="btn secondary" type="button">Verbinden</button>
          </div>
        `;
        row.querySelector("button").addEventListener("click", () => {
          selectedSsid = net.ssid;
          wifiConnectSsid.textContent = net.ssid;
          wifiConnectField.hidden = false;
          wifiConnectStatus.textContent = "";
          wifiPassword.focus();
        });
        wifiNetworks.appendChild(row);
      }
    } catch (err) {
      wifiNetworks.innerHTML = "";
      showToast(err.message, true);
    }
  });

  wifiConnectBtn.addEventListener("click", async () => {
    if (!selectedSsid) return;
    wifiConnectStatus.textContent = "Verbinde…";
    try {
      const result = await api("/api/network/connect", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ssid: selectedSsid, password: wifiPassword.value }),
      });
      wifiConnectStatus.textContent = result.message || "Verbunden.";
      showToast(`Mit "${selectedSsid}" verbunden.`);
      wifiConnectField.hidden = true;
      wifiPassword.value = "";
      refreshWifiStatus();
      loadKnownNetworks();
    } catch (err) {
      wifiConnectStatus.textContent = err.message;
    }
  });

  // Max-volume/step and min/max-brightness are edit-and-save fields, not live
  // telemetry - only ever populated once up front, never overwritten by the
  // recurring poll below (which would otherwise race a user's in-progress edit
  // or an unsaved change right back to whatever the server currently has).
  async function loadVolumeSettingsOnce() {
    try {
      const state = await api("/api/state");
      maxVolumeInput.value = state.settings.max_volume;
      volumeStepInput.value = state.settings.volume_step;
      chimeVolumePercentInput.value = state.settings.chime_volume_percent;
      for (const [name, input] of Object.entries(chimeTypeInputs)) {
        input.checked = state.settings.chime_enabled[name];
      }
      minBrightnessInput.value = state.settings.min_brightness;
      maxBrightnessInput.value = state.settings.max_brightness;
      brightnessStepInput.value = state.settings.brightness_step;
      currentBrightnessInput.min = state.settings.min_brightness;
      currentBrightnessInput.max = state.settings.max_brightness;
      nightBrightnessInput.value = state.settings.night_brightness;
      nightModeActive = state.settings.night_mode_active;
      renderNightModeToggle();
      autoSleepMinutesInput.value = state.settings.auto_sleep_minutes;

      await loadAlarmStoryOptions();
      alarmEnabledInput.checked = state.alarm.enabled;
      alarmTimeInput.value = state.alarm.time;
      alarmStorySelect.value = state.alarm.story_id || "";
      alarmFadeSecondsInput.value = state.alarm.fade_seconds;
      renderAlarmStatus(state.alarm);

      applyMultiroomState(state.multiroom);
    } catch (err) {
      // ignore, fields keep their HTML defaults
    }
  }

  // -- periodic refresh of live values (current volume, sleep timer) --------

  async function pollState() {
    try {
      const state = await api("/api/state");
      if (!volumeSliderBeingDragged) {
        currentVolumeInput.value = state.player.volume;
        currentVolumeValue.textContent = state.player.volume;
      }

      if (!brightnessSliderBeingDragged) {
        currentBrightnessInput.value = state.settings.brightness;
        currentBrightnessValue.textContent = state.settings.brightness;
      }

      // Live, not edit-and-save like min/max_brightness above - the physical
      // encoder button can flip this at any moment, independent of whatever
      // this page happens to be showing.
      if (state.settings.night_mode_active !== nightModeActive) {
        nightModeActive = state.settings.night_mode_active;
        renderNightModeToggle();
      }

      applyHotspotBanner(state.wifi);

      if (state.sleep_timer.active) {
        sleepTimerStatus.textContent = `Noch ${formatMinutesSeconds(state.sleep_timer.remaining_seconds)} bis zur Pause.`;
        sleepTimerCancelBtn.hidden = false;
      } else {
        sleepTimerStatus.textContent = "Kein Timer aktiv.";
        sleepTimerCancelBtn.hidden = true;
      }

      autoSleepStatus.textContent = state.auto_sleep.active
        ? "😴 Die Eule schläft gerade - aufwecken per Lautstärke, Play/Pause oder RFID-Tag."
        : "Wache Eule.";

      // Live, not edit-and-save - a newer Hauptbox showing up elsewhere on
      // the network can flip this box back off automatically at any moment
      // (see Engine._check_multiroom), independent of anything happening on
      // this page. Only touches the checkbox when the persisted value
      // actually changed, so it never fights an in-progress, not-yet-saved
      // click the same tick it happens.
      if (state.multiroom.master_enabled !== multiroomMasterCheckbox.checked) {
        multiroomMasterCheckbox.checked = state.multiroom.master_enabled;
      }
      renderMultiroomStatus(state.multiroom);
    } catch (err) {
      // ignore, try again next tick
    } finally {
      setTimeout(pollState, 1000);
    }
  }

  // -- known/saved wifi networks ---------------------------------------------

  const wifiKnownList = document.getElementById("wifi-known-list");

  async function loadKnownNetworks() {
    try {
      const networks = await api("/api/network/known");
      wifiKnownList.innerHTML = "";
      if (networks.length === 0) {
        wifiKnownList.innerHTML = '<p class="hint">Noch keine bekannten Netzwerke.</p>';
        return;
      }
      for (const net of networks) {
        const row = document.createElement("div");
        row.className = "story-row";
        row.innerHTML = `
          <div class="story-meta">
            <div class="row-title">${net.name}${net.active ? " (verbunden)" : ""}</div>
          </div>
          <div class="story-actions">
            ${net.active ? "" : '<button class="btn secondary" data-action="connect">Verbinden</button>'}
            <button class="btn danger" data-action="forget">Entfernen</button>
          </div>
        `;
        const connectBtn = row.querySelector('[data-action="connect"]');
        if (connectBtn) {
          connectBtn.addEventListener("click", async () => {
            connectBtn.disabled = true;
            connectBtn.textContent = "Verbinde…";
            try {
              const result = await api(`/api/network/known/${encodeURIComponent(net.name)}/connect`, { method: "POST" });
              showToast(result.message || `Mit "${net.name}" verbunden.`);
              refreshWifiStatus();
              loadKnownNetworks();
            } catch (err) {
              showToast(err.message, true);
              connectBtn.disabled = false;
              connectBtn.textContent = "Verbinden";
            }
          });
        }
        row.querySelector('[data-action="forget"]').addEventListener("click", async () => {
          if (!confirm(`Netzwerk "${net.name}" wirklich entfernen?`)) return;
          try {
            await api(`/api/network/known/${encodeURIComponent(net.name)}`, { method: "DELETE" });
            showToast("Netzwerk entfernt.");
            loadKnownNetworks();
          } catch (err) {
            showToast(err.message, true);
          }
        });
        wifiKnownList.appendChild(row);
      }
    } catch (err) {
      wifiKnownList.innerHTML = '<p class="hint">Bekannte Netzwerke konnten nicht geladen werden.</p>';
    }
  }

  // -- peers (andere OwlBoxen im Netzwerk) -----------------------------------
  // Primarily live mDNS discovery (see GET /api/peers) - the manual form
  // below is only a fallback for when that doesn't reach a box.

  const peerList = document.getElementById("peer-list");
  const peerNameInput = document.getElementById("peer-name-input");
  const peerHostInput = document.getElementById("peer-host-input");
  const peerStatus = document.getElementById("peer-status");

  async function loadPeers() {
    try {
      const peers = await api("/api/peers");
      peerList.innerHTML = "";
      if (peers.length === 0) {
        peerList.innerHTML = '<p class="hint">Noch keine anderen Boxen im Netzwerk gefunden.</p>';
        return;
      }
      for (const peer of peers) {
        const li = document.createElement("li");
        li.className = "peer-row";
        li.innerHTML = `
          <span class="peer-status-dot ${peer.reachable ? "online" : "offline"}"
            title="${peer.reachable ? "Erreichbar" : "Nicht erreichbar"}"></span>
          <span class="peer-name">${peer.name}${peer.master_enabled ? " 🔊 Hauptbox" : ""}</span>
          <span class="peer-host mono">${peer.host}</span>
          <a class="btn secondary small" href="http://${peer.host}:5000/admin" target="_blank" rel="noopener">Öffnen</a>
          ${peer.id != null ? '<button class="btn danger small" data-action="delete">Entfernen</button>' : ""}
        `;
        const deleteBtn = li.querySelector('[data-action="delete"]');
        if (deleteBtn) {
          deleteBtn.addEventListener("click", async () => {
            if (!confirm(`"${peer.name}" aus der Liste entfernen?`)) return;
            try {
              await api(`/api/peers/${peer.id}`, { method: "DELETE" });
              loadPeers();
            } catch (err) {
              showToast(err.message, true);
            }
          });
        }
        peerList.appendChild(li);
      }
    } catch (err) {
      peerList.innerHTML = '<p class="hint">Konnte andere Boxen nicht laden.</p>';
    }
  }

  document.getElementById("peer-add-btn").addEventListener("click", async () => {
    const name = peerNameInput.value.trim();
    const host = peerHostInput.value.trim();
    if (!name || !host) {
      peerStatus.textContent = "Name und Host/IP werden benötigt.";
      return;
    }
    peerStatus.textContent = "Fügt hinzu…";
    try {
      await api("/api/peers", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, host }),
      });
      peerNameInput.value = "";
      peerHostInput.value = "";
      peerStatus.textContent = "";
      loadPeers();
    } catch (err) {
      peerStatus.textContent = err.message;
    }
  });

  // -- Mehrraum-Wiedergabe (Snapcast) -----------------------------------------
  // Two switches: a master on/off for the whole subsystem (feature_enabled -
  // lets a household that doesn't want this at all turn it off completely,
  // no network scanning, no Snapcast) and, only meaningful while that's on,
  // "ist diese Box die Hauptbox". Every other box figures out on its own, via
  // the peer list above, whether to follow it (see Engine._check_multiroom).
  // Nothing to pick here for a Slave-Box.

  const multiroomFeatureCheckbox = document.getElementById("multiroom-feature-checkbox");
  const multiroomMasterCheckbox = document.getElementById("multiroom-master-checkbox");
  const multiroomMasterField = document.getElementById("multiroom-master-field");
  const multiroomStatus = document.getElementById("multiroom-status");
  const multiroomSaveStatus = document.getElementById("multiroom-save-status");

  function updateMultiroomFieldVisibility() {
    multiroomMasterField.hidden = !multiroomFeatureCheckbox.checked;
  }
  multiroomFeatureCheckbox.addEventListener("change", updateMultiroomFieldVisibility);

  function renderMultiroomStatus(multiroom) {
    // master_enabled alone (not effective_role) decides the "Hauptbox"
    // branch - the server always clears master_enabled in the very same
    // step as handing the role to a newer peer (see Engine._check_multiroom's
    // yield logic), so "I asked to be Hauptbox" and "a newer one outranked
    // me" can never both be true here at once. When master_enabled is true
    // but effective_role isn't "master" yet, that's purely an OS-level
    // application failure (systemctl, ...) - still "Diese Box ist die
    // Hauptbox" is the honest description of what was actually asked for,
    // with the reason it hasn't taken effect appended below.
    if (!multiroom.feature_enabled) {
      multiroomStatus.textContent = "Mehrraum-Wiedergabe ist deaktiviert.";
    } else if (multiroom.master_enabled) {
      multiroomStatus.textContent = "Diese Box ist die Hauptbox.";
    } else if (multiroom.effective_role === "slave" && multiroom.following_name) {
      multiroomStatus.textContent = `Folgt automatisch der Hauptbox „${multiroom.following_name}“.`;
    } else {
      multiroomStatus.textContent = "Mehrraum-Wiedergabe ist aktiv (keine Hauptbox im Netzwerk gefunden).";
    }
    if (multiroom.error) {
      multiroomStatus.textContent += ` (${multiroom.error})`;
    }
  }

  function applyMultiroomState(multiroom) {
    multiroomFeatureCheckbox.checked = multiroom.feature_enabled;
    multiroomMasterCheckbox.checked = multiroom.master_enabled;
    updateMultiroomFieldVisibility();
    renderMultiroomStatus(multiroom);
  }

  document.getElementById("multiroom-save-btn").addEventListener("click", async () => {
    multiroomSaveStatus.textContent = "Speichert…";
    try {
      const result = await api("/api/multiroom", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          feature_enabled: multiroomFeatureCheckbox.checked,
          master_enabled: multiroomMasterCheckbox.checked,
        }),
      });
      applyMultiroomState(result.multiroom);
      multiroomSaveStatus.textContent = "Gespeichert - für volle Wirkung jetzt neu starten (Einstellungen > System).";
    } catch (err) {
      multiroomSaveStatus.textContent = err.message;
    }
  });

  loadVolumeSettingsOnce();
  pollState();
  refreshWifiStatus();
  loadKnownNetworks();
  loadPeers();
})();
