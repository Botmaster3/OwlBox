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
    document.getElementById("info-mode").textContent = info.app.simulate ? "Simulation" : "Hardware";
  }

  load();
})();
