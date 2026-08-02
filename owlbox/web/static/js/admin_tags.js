(function () {
  const ACTION_LABELS = window.OWLBOX_ACTION_LABELS || {};

  const scanOverlay = document.getElementById("scan-overlay");
  const scanStatus = document.getElementById("scan-status");
  const scanCancel = document.getElementById("scan-cancel");

  const adminRfidStatus = document.getElementById("admin-rfid-status");
  const adminRfidSetBtn = document.getElementById("admin-rfid-set-btn");
  const adminRfidClearBtn = document.getElementById("admin-rfid-clear-btn");

  const functionTagList = document.getElementById("function-tag-list");
  const functionActionSelect = document.getElementById("function-action");
  const functionTagAddBtn = document.getElementById("function-tag-add-btn");

  const storyTagList = document.getElementById("story-tag-list");

  let scanPoll = null;

  async function api(url, options) {
    const res = await fetch(url, options);
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new Error(body.error || `HTTP ${res.status}`);
    }
    return res.status === 204 ? null : res.json();
  }

  // Shows the "hold a chip against the box" overlay, resolves with the newly
  // scanned uid, or null if the user cancels.
  function scanForUid(statusText) {
    return new Promise((resolve) => {
      scanStatus.textContent = statusText;
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

  // -- admin login chip -----------------------------------------------------

  adminRfidSetBtn.addEventListener("click", async () => {
    const uid = await scanForUid("Halte den Login-Chip jetzt an die Box…");
    if (!uid) return;
    await api("/api/admin/rfid", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ uid }),
    });
    adminRfidStatus.innerHTML = `Hinterlegt: <span class="mono">${uid}</span>`;
    adminRfidClearBtn.hidden = false;
  });

  adminRfidClearBtn.addEventListener("click", async () => {
    if (!confirm("Login-Chip entfernen?")) return;
    await api("/api/admin/rfid", { method: "DELETE" });
    adminRfidStatus.textContent = "Kein Chip hinterlegt.";
    adminRfidClearBtn.hidden = true;
  });

  // -- function tags ---------------------------------------------------------

  async function loadFunctionTags() {
    const tags = await api("/api/function-tags");
    functionTagList.innerHTML = "";
    if (tags.length === 0) {
      functionTagList.innerHTML = '<p class="hint">Noch keine Funktions-Chips angelegt.</p>';
      return;
    }
    for (const tag of tags) {
      const row = document.createElement("div");
      row.className = "story-row";
      row.innerHTML = `
        <div class="story-meta">
          <div class="row-title">${ACTION_LABELS[tag.action] || tag.action}</div>
          <div class="story-sub mono">${tag.uid}</div>
        </div>
        <div class="story-actions">
          <button class="btn danger" data-action="delete">Löschen</button>
        </div>
      `;
      row.querySelector('[data-action="delete"]').addEventListener("click", async () => {
        await api(`/api/function-tags/${encodeURIComponent(tag.uid)}`, { method: "DELETE" });
        loadFunctionTags();
      });
      functionTagList.appendChild(row);
    }
  }

  functionTagAddBtn.addEventListener("click", async () => {
    const action = functionActionSelect.value;
    const label = ACTION_LABELS[action] || action;
    const uid = await scanForUid(`Halte den Chip für "${label}" jetzt an die Box…`);
    if (!uid) return;
    await api("/api/function-tags", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ uid, action }),
    });
    loadFunctionTags();
  });

  // -- story tags (read-only overview) ---------------------------------------

  async function loadStoryTags() {
    const stories = await api("/api/stories");
    const assigned = stories.filter((s) => s.uid);
    storyTagList.innerHTML = "";
    if (assigned.length === 0) {
      storyTagList.innerHTML = '<p class="hint">Noch keiner Geschichte ein Chip zugewiesen.</p>';
      return;
    }
    for (const story of assigned) {
      const row = document.createElement("div");
      row.className = "story-row";
      row.innerHTML = `
        <div class="story-meta">
          <div class="row-title">${story.title}</div>
          <div class="story-sub mono">${story.uid}</div>
        </div>
        <div class="story-actions">
          <button class="btn secondary" data-action="unassign">Entfernen</button>
        </div>
      `;
      row.querySelector('[data-action="unassign"]').addEventListener("click", async () => {
        await api(`/api/stories/${story.id}/unassign`, { method: "POST" });
        loadStoryTags();
      });
      storyTagList.appendChild(row);
    }
  }

  loadFunctionTags();
  loadStoryTags();
})();
