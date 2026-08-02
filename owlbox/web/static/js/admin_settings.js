(function () {
  const status = document.getElementById("system-status");

  async function post(url) {
    const res = await fetch(url, { method: "POST" });
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new Error(body.error || `HTTP ${res.status}`);
    }
  }

  document.getElementById("restart-btn").addEventListener("click", async () => {
    if (!confirm("Pi jetzt neu starten?")) return;
    status.textContent = "Startet neu…";
    try {
      await post("/api/system/restart");
    } catch (err) {
      status.textContent = err.message;
    }
  });

  document.getElementById("shutdown-btn").addEventListener("click", async () => {
    if (!confirm("Pi jetzt herunterfahren? Danach muss er per Stecker/Schalter wieder eingeschaltet werden.")) return;
    status.textContent = "Fährt herunter…";
    try {
      await post("/api/system/shutdown");
    } catch (err) {
      status.textContent = err.message;
    }
  });
})();
