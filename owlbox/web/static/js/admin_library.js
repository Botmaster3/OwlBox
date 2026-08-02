(function () {
  const storyList = document.getElementById("story-list");
  const assignOverlay = document.getElementById("assign-overlay");
  const assignStatus = document.getElementById("assign-status");
  const assignCancel = document.getElementById("assign-cancel");
  const simulate = document.getElementById("app").dataset.simulate === "true";

  let assignPoll = null;

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

  function formatDuration(seconds) {
    if (!seconds) return "";
    seconds = Math.floor(seconds);
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return `${m}:${String(s).padStart(2, "0")}`;
  }

  async function api(url, options) {
    const res = await fetch(url, options);
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new Error(body.error || `HTTP ${res.status}`);
    }
    return res.status === 204 ? null : res.json();
  }

  async function loadStories() {
    const stories = await api("/api/stories");
    renderStories(stories);
  }

  function trackRow(story, track, index, total) {
    const li = document.createElement("li");
    li.innerHTML = `
      <span class="track-order">
        <button data-action="up" ${index === 0 ? "disabled" : ""}>▲</button>
        <button data-action="down" ${index === total - 1 ? "disabled" : ""}>▼</button>
      </span>
      <span>${index + 1}. ${track.title || track.filename} ${track.duration ? "(" + formatDuration(track.duration) + ")" : ""}</span>
      <button data-action="delete">🗑</button>
    `;
    li.querySelector('[data-action="up"]').addEventListener("click", () => moveTrack(story, index, -1));
    li.querySelector('[data-action="down"]').addEventListener("click", () => moveTrack(story, index, 1));
    li.querySelector('[data-action="delete"]').addEventListener("click", async () => {
      await api(`/api/stories/${story.id}/tracks/${track.id}`, { method: "DELETE" });
      loadStories();
    });
    return li;
  }

  async function moveTrack(story, index, delta) {
    const ids = story.tracks.map((t) => t.id);
    const target = index + delta;
    if (target < 0 || target >= ids.length) return;
    [ids[index], ids[target]] = [ids[target], ids[index]];
    await api(`/api/stories/${story.id}/tracks/reorder`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ track_ids: ids }),
    });
    loadStories();
  }

  function renderStories(stories) {
    storyList.innerHTML = "";
    if (stories.length === 0) {
      storyList.innerHTML = '<p class="hint">Noch keine Geschichten angelegt. <a href="/admin/add">Jetzt hinzufügen</a>.</p>';
      return;
    }
    for (const story of stories) {
      const row = document.createElement("div");
      row.className = "story-row";
      row.style.flexDirection = "column";
      row.style.alignItems = "stretch";

      const header = document.createElement("div");
      header.className = "story-row";
      header.style.borderBottom = "none";
      header.style.padding = "0";
      header.innerHTML = `
        ${story.cover_url ? `<img src="${story.cover_url}" alt="">` : '<div class="thumb-placeholder">🦉</div>'}
        <div class="story-meta">
          <div class="row-title">${story.title}</div>
          <div class="story-sub">${story.track_count} Titel · ${story.uid ? "Chip: " + story.uid : "kein Chip zugewiesen"}</div>
        </div>
        <div class="story-actions">
          <button class="btn secondary" data-action="assign">Chip zuweisen</button>
          ${story.uid ? '<button class="btn secondary" data-action="unassign">Chip entfernen</button>' : ""}
          <button class="btn secondary" data-action="shuffle">${story.shuffle ? "🔀 an" : "🔀 aus"}</button>
          <button class="btn secondary" data-action="repeat">${story.repeat ? "🔁 an" : "🔁 aus"}</button>
          <button class="btn danger" data-action="delete">Löschen</button>
        </div>
      `;
      header.querySelector('[data-action="assign"]').addEventListener("click", () => startAssign(story));
      const unassignBtn = header.querySelector('[data-action="unassign"]');
      if (unassignBtn) {
        unassignBtn.addEventListener("click", async () => {
          try {
            await api(`/api/stories/${story.id}/unassign`, { method: "POST" });
            showToast("Chip entfernt.");
            loadStories();
          } catch (err) {
            showToast(err.message, true);
          }
        });
      }
      header.querySelector('[data-action="shuffle"]').addEventListener("click", async () => {
        await api(`/api/stories/${story.id}/flags`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ shuffle: !story.shuffle }),
        });
        loadStories();
      });
      header.querySelector('[data-action="repeat"]').addEventListener("click", async () => {
        await api(`/api/stories/${story.id}/flags`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ repeat: !story.repeat }),
        });
        loadStories();
      });
      header.querySelector('[data-action="delete"]').addEventListener("click", async () => {
        if (!confirm(`"${story.title}" wirklich löschen?`)) return;
        try {
          await api(`/api/stories/${story.id}`, { method: "DELETE" });
          showToast(`"${story.title}" gelöscht.`);
          loadStories();
        } catch (err) {
          showToast(err.message, true);
        }
      });

      const tracks = document.createElement("ul");
      tracks.className = "track-list";
      story.tracks.forEach((track, index) => tracks.appendChild(trackRow(story, track, index, story.tracks.length)));

      row.appendChild(header);
      row.appendChild(tracks);
      storyList.appendChild(row);
    }
  }

  function startAssign(story) {
    assignStatus.textContent = `Halte den Chip für "${story.title}" jetzt an die Box…`;
    assignOverlay.hidden = false;

    api("/api/scans/last").then((baseline) => {
      const baselineId = baseline ? baseline.id : 0;
      assignPoll = setInterval(async () => {
        const latest = await api("/api/scans/last");
        if (latest && latest.id !== baselineId) {
          stopAssign();
          try {
            await api(`/api/stories/${story.id}/assign`, {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ uid: latest.uid }),
            });
            showToast(`Chip zugewiesen: ${latest.uid}`);
            loadStories();
          } catch (err) {
            showToast(err.message, true);
          }
        }
      }, 1000);
    });
  }

  function stopAssign() {
    if (assignPoll) clearInterval(assignPoll);
    assignPoll = null;
    assignOverlay.hidden = true;
  }

  assignCancel.addEventListener("click", stopAssign);

  if (simulate) {
    document.getElementById("sim-scan-btn").addEventListener("click", () => {
      const uid = document.getElementById("sim-uid").value.trim();
      if (!uid) return;
      api("/api/dev/simulate-scan", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ uid }),
      });
    });
    document.getElementById("sim-remove-btn").addEventListener("click", () => {
      api("/api/dev/simulate-remove", { method: "POST" });
    });
  }

  loadStories();
})();
