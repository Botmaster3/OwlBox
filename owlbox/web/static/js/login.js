(function () {
  const scanOverlay = document.getElementById("scan-overlay");
  const scanCancel = document.getElementById("scan-cancel");
  const rfidLoginBtn = document.getElementById("rfid-login-btn");
  const rfidLoginStatus = document.getElementById("rfid-login-status");

  let scanPoll = null;

  async function api(url, options) {
    const res = await fetch(url, options);
    const body = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(body.error || `HTTP ${res.status}`);
    return body;
  }

  function scanForUid() {
    return new Promise((resolve) => {
      scanOverlay.hidden = false;

      const cleanup = () => {
        if (scanPoll) clearInterval(scanPoll);
        scanPoll = null;
        scanOverlay.hidden = true;
        scanCancel.onclick = null;
      };

      scanCancel.onclick = () => {
        cleanup();
        resolve(null);
      };

      api("/api/scans/last").then((baseline) => {
        const baselineId = baseline ? baseline.id : 0;
        scanPoll = setInterval(async () => {
          const latest = await api("/api/scans/last");
          if (latest && latest.id !== baselineId) {
            cleanup();
            resolve(latest.uid);
          }
        }, 1000);
      });
    });
  }

  rfidLoginBtn.addEventListener("click", async () => {
    rfidLoginStatus.textContent = "";
    const uid = await scanForUid();
    if (!uid) return;
    try {
      await api("/api/auth/rfid-login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ uid }),
      });
      window.location.href = "/admin";
    } catch (err) {
      rfidLoginStatus.textContent = err.message;
    }
  });
})();
