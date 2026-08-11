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

    document.getElementById("info-story-count").textContent = info.library.story_count;
    document.getElementById("info-track-count").textContent = info.library.track_count;
    document.getElementById("info-assigned-count").textContent = info.library.assigned_count;

    document.getElementById("info-version").textContent = info.app.version;
    document.getElementById("info-version-date").textContent = info.app.version_date || "unbekannt";
    document.getElementById("info-mode").textContent = info.app.simulate ? "Simulation" : "Hardware";
    appVersionText = info.app.version_date ? `${info.app.version} vom ${info.app.version_date}` : info.app.version;
  }

  // -- Höraktivität: daily bar chart + trend + top stories for a selectable
  // period (7/14/30 Tage) - its own endpoint (/api/stats/period) rather than
  // bundled into /api/system/info above, since changing the period re-fetches
  // just this card instead of the whole info bundle (uptime, disk, ...).
  const WEEKDAY_SHORT = ["So", "Mo", "Di", "Mi", "Do", "Fr", "Sa"];

  function formatStatsDate(isoDate) {
    // isoDate is a plain "YYYY-MM-DD" (UTC calendar day, see
    // repository.get_daily_listening_breakdown) - Date treats a bare date
    // string as UTC midnight, which matches here, no "Z" needed.
    const d = new Date(isoDate);
    return `${WEEKDAY_SHORT[d.getUTCDay()]}, ${String(d.getUTCDate()).padStart(2, "0")}.${String(d.getUTCMonth() + 1).padStart(2, "0")}.`;
  }

  function renderStatsChart(daily) {
    const svg = document.getElementById("stats-chart");
    const days = daily.length;
    const maxSeconds = Math.max(1, ...daily.map((d) => d.seconds));
    const slot = 100 / days;
    const barWidth = slot * 0.68;
    // Every bar gets a visible sliver even at 0 (0.6 of 40 viewBox units)
    // instead of vanishing completely - a day with genuinely no listening
    // should still read as "a day", not as a gap in the chart.
    const bars = daily
      .map((d, i) => {
        const height = Math.max(0.6, (d.seconds / maxSeconds) * 40);
        const x = i * slot + (slot - barWidth) / 2;
        const y = 40 - height;
        const title = `${formatStatsDate(d.date)}: ${formatListeningDuration(d.seconds)}`;
        return `<rect x="${x.toFixed(2)}" y="${y.toFixed(2)}" width="${barWidth.toFixed(2)}" height="${height.toFixed(2)}" rx="0.6"><title>${title}</title></rect>`;
      })
      .join("");
    svg.innerHTML = bars;
  }

  function renderStatsPeriod(review) {
    const summaryEl = document.getElementById("weekly-review-summary");
    const topEl = document.getElementById("weekly-review-top");

    renderStatsChart(review.daily);

    if (review.total_seconds > 0) {
      let trendText = "";
      const trend = review.trend;
      if (trend && trend.previous_seconds > 0) {
        const pct = Math.round((trend.current_seconds - trend.previous_seconds) / trend.previous_seconds * 100);
        if (pct > 0) trendText = ` (+${pct}% zum vorherigen Zeitraum)`;
        else if (pct < 0) trendText = ` (${pct}% zum vorherigen Zeitraum)`;
        else trendText = " (unverändert zum vorherigen Zeitraum)";
      } else if (trend && trend.current_seconds > 0) {
        trendText = " (im Zeitraum davor wurde noch nichts gehört)";
      }
      summaryEl.textContent =
        `Letzte ${review.days} Tage: ${formatListeningDuration(review.total_seconds)} gehört, ` +
        `${review.total_plays}x eine Geschichte gestartet.${trendText}`;
      topEl.innerHTML = review.top_stories
        .map((s) => `<li>${s.title}${s.is_stream ? " (Livestream)" : ""} - ${formatListeningDuration(s.seconds)}</li>`)
        .join("");
    } else {
      summaryEl.textContent = `In den letzten ${review.days} Tagen wurde noch nichts gehört.`;
      topEl.innerHTML = "";
    }
  }

  async function loadStatsPeriod(days) {
    document.querySelectorAll("#stats-period-toggle button").forEach((btn) => {
      btn.classList.toggle("active", Number(btn.dataset.days) === days);
    });
    try {
      const res = await fetch(`/api/stats/period?days=${days}`);
      renderStatsPeriod(await res.json());
    } catch (err) {
      document.getElementById("weekly-review-summary").textContent = "Konnte Höraktivität nicht laden.";
    }
  }

  document.querySelectorAll("#stats-period-toggle button").forEach((btn) => {
    btn.addEventListener("click", () => loadStatsPeriod(Number(btn.dataset.days)));
  });

  loadStatsPeriod(7);

  // Set once load() has filled it in, so the "already up to date" message below
  // can name the version instead of just saying "some current version".
  let appVersionText = null;

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
        updateStatus.textContent = appVersionText
          ? `Du hast bereits die aktuellste Version installiert (${appVersionText}).`
          : "Du hast bereits die aktuellste Version installiert.";
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

  // load() first so appVersionText is set before the automatic check below
  // names it in the "already current" message. Still just a look, never an
  // install, so this is safe to run without the user asking for it.
  (async () => {
    await load();
    checkForUpdate();
  })();
})();
