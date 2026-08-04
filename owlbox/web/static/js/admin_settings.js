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
          await api("/api/settings/theme", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ theme: id }),
          });
        } catch (err) {
          showToast(err.message, true);
        }
      });
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
      autoSleepMinutesInput.value = state.settings.auto_sleep_minutes;
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

  loadVolumeSettingsOnce();
  pollState();
  refreshWifiStatus();
  loadKnownNetworks();
})();
