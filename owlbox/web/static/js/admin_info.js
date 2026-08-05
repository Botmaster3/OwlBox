(function () {
  function formatBytes(bytes) {
    if (bytes == null) return "unbekannt";
    const units = ["B", "KB", "MB", "GB", "TB"];
    let value = bytes;
    let unitIndex = 0;
    while (value >= 1024 && unitIndex < units.length - 1) {
      value /= 1024;
      unitIndex += 1;
    }
    return `${value.toFixed(value >= 10 || unitIndex === 0 ? 0 : 1)} ${units[unitIndex]}`;
  }

  function formatListeningDuration(seconds) {
    seconds = Math.floor(seconds || 0);
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    if (h > 0) return `${h}h ${m}min`;
    if (m > 0) return `${m} Min.`;
    return `${seconds} Sek.`;
  }

  function formatUptime(seconds) {
    if (seconds == null) return "unbekannt";
    const days = Math.floor(seconds / 86400);
    const hours = Math.floor((seconds % 86400) / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const parts = [];
    if (days) parts.push(`${days} Tag(e)`);
    if (hours || days) parts.push(`${hours} Std.`);
    parts.push(`${minutes} Min.`);
    return parts.join(" ");
  }

  // Status-colors a gauge bar (width relative to `max`, color by how close
  // `value` is to the warn/critical thresholds - all three in the same unit).
  function setGauge(fillEl, value, max, warnAt, criticalAt) {
    const pct = max > 0 ? Math.max(0, Math.min(100, (value / max) * 100)) : 0;
    fillEl.style.width = `${pct}%`;
    fillEl.classList.remove("good", "warn", "critical");
    fillEl.classList.add(value >= criticalAt ? "critical" : value >= warnAt ? "warn" : "good");
  }

  async function load() {
    let info;
    try {
      const res = await fetch("/api/system/info");
      info = await res.json();
    } catch (err) {
      return;
    }

    document.getElementById("info-hardware").textContent = info.hardware_model || "unbekannt";
    document.getElementById("info-os").textContent = info.os || "unbekannt";
    document.getElementById("info-uptime").textContent = formatUptime(info.uptime_seconds);

    const cpuTemp = info.cpu_temp_celsius;
    document.getElementById("info-cpu-temp").textContent = cpuTemp != null ? `${cpuTemp.toFixed(1)} °C` : "unbekannt";
    // Raspberry Pi boards start throttling around 80-85 °C, so that's the gauge's ceiling.
    setGauge(document.getElementById("cpu-temp-fill"), cpuTemp || 0, 85, 65, 78);

    const disk = info.disk;
    if (disk) {
      setGauge(document.getElementById("disk-fill"), disk.used_bytes, disk.total_bytes, disk.total_bytes * 0.8, disk.total_bytes * 0.92);
      document.getElementById("disk-text").textContent =
        `${formatBytes(disk.used_bytes)} von ${formatBytes(disk.total_bytes)} belegt (${formatBytes(disk.free_bytes)} frei)`;
    }

    const memory = info.memory;
    if (memory && memory.used_bytes != null) {
      setGauge(document.getElementById("memory-fill"), memory.used_bytes, memory.total_bytes, memory.total_bytes * 0.8, memory.total_bytes * 0.92);
      document.getElementById("memory-text").textContent =
        `${formatBytes(memory.used_bytes)} von ${formatBytes(memory.total_bytes)} belegt`;
    } else {
      document.getElementById("memory-text").textContent = "nicht verfügbar";
    }

    const weekly = info.weekly_review;
    if (weekly) {
      const summaryEl = document.getElementById("weekly-review-summary");
      const topEl = document.getElementById("weekly-review-top");
      if (weekly.total_seconds > 0) {
        summaryEl.textContent =
          `Letzte ${weekly.days} Tage: ${formatListeningDuration(weekly.total_seconds)} gehört, ` +
          `${weekly.total_plays}x eine Geschichte gestartet.`;
        topEl.innerHTML = weekly.top_stories
          .map((s) => `<li>${s.title}${s.is_stream ? " (Livestream)" : ""} - ${formatListeningDuration(s.seconds)}</li>`)
          .join("");
      } else {
        summaryEl.textContent = `In den letzten ${weekly.days} Tagen wurde noch nichts gehört.`;
        topEl.innerHTML = "";
      }
    }

    document.getElementById("info-story-count").textContent = info.library.story_count;
    document.getElementById("info-track-count").textContent = info.library.track_count;
    document.getElementById("info-assigned-count").textContent = info.library.assigned_count;

    document.getElementById("info-version").textContent = info.app.version;
    document.getElementById("info-mode").textContent = info.app.simulate ? "Simulation" : "Hardware";
  }

  load();

  // Update flow is deliberately two steps: checkForUpdate() only ever looks
  // (git fetch, no working-tree changes), installUpdate() is the one thing
  // that actually pulls/restarts - and it only ever runs when the user clicks
  // its button, never automatically.
  const checkBtn = document.getElementById("update-check-btn");
  const installBtn = document.getElementById("update-install-btn");
  const updateStatus = document.getElementById("update-status");

  async function checkForUpdate() {
    checkBtn.disabled = true;
    installBtn.hidden = true;
    updateStatus.textContent = "Prüfe auf Updates…";
    try {
      const res = await fetch("/api/system/update/check");
      const result = await res.json();
      if (!res.ok) {
        updateStatus.textContent = `Prüfung fehlgeschlagen (${result.step}): ${result.output || "unbekannter Fehler"}`;
      } else if (result.update_available) {
        const n = result.commits_behind;
        updateStatus.textContent = `Update verfügbar (${n} neue${n === 1 ? "r" : ""} Commit${n === 1 ? "" : "s"}).`;
        installBtn.hidden = false;
      } else {
        updateStatus.textContent = "OwlBox ist bereits auf dem neuesten Stand.";
      }
    } catch (err) {
      updateStatus.textContent = `Prüfung fehlgeschlagen: ${err.message}`;
    } finally {
      checkBtn.disabled = false;
    }
  }

  installBtn.addEventListener("click", async () => {
    if (!confirm("Update jetzt installieren? Der OwlBox-Dienst wird dazu kurz neu gestartet.")) return;
    checkBtn.disabled = true;
    installBtn.disabled = true;
    updateStatus.textContent = "Installiere Update…";
    try {
      const res = await fetch("/api/system/update", { method: "POST" });
      const result = await res.json();
      if (!res.ok) {
        updateStatus.textContent = `Fehlgeschlagen (${result.step}): ${result.output || "unbekannter Fehler"}`;
        installBtn.disabled = false;
      } else if (result.restarted) {
        updateStatus.textContent = "Update installiert, Dienst startet neu - Seite gleich neu laden.";
        installBtn.hidden = true;
      } else {
        updateStatus.textContent = "Bereits auf dem neuesten Stand.";
        installBtn.hidden = true;
      }
    } catch (err) {
      updateStatus.textContent = `Fehlgeschlagen: ${err.message}`;
      installBtn.disabled = false;
    } finally {
      checkBtn.disabled = false;
    }
  });

  checkBtn.addEventListener("click", checkForUpdate);

  // Checked automatically once when the page loads - still just a look, never
  // an install, so this is safe to run without the user asking for it.
  checkForUpdate();
})();
