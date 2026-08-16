(function () {
  const storyList = document.getElementById("story-list");
  const librarySearch = document.getElementById("library-search");
  const librarySort = document.getElementById("library-sort");
  const filterChipGroup = document.getElementById("filter-chip-group");
  const filterTypeGroup = document.getElementById("filter-type-group");
  const addTracksInput = document.getElementById("add-tracks-input");
  const changeCoverInput = document.getElementById("change-cover-input");
  const assignOverlay = document.getElementById("assign-overlay");
  const assignStatus = document.getElementById("assign-status");
  const assignCancel = document.getElementById("assign-cancel");
  const simulate = document.getElementById("app").dataset.simulate === "true";

  let assignPoll = null;
  // Full list from the last /api/stories fetch, kept around so the search
  // box can filter/re-render instantly without a round-trip on every
  // keystroke - loadStories() (a full refetch) still runs after anything
  // that actually changes data (add/delete/reorder/etc.).
  let allStories = [];
  // The story a "+ Weitere Tracks" click targets - set right before the
  // shared #add-tracks-input's file dialog opens, read back once a
  // selection comes in (see addTracksInput's "change" handler below).
  let addTracksTargetId = null;
  // Same idea as addTracksTargetId above, for the shared #change-cover-input.
  let changeCoverTargetId = null;
  // Cross-story track selection for "aus Bibliothek zur Playlist
  // hinzufügen" (mirrors the picker on Hinzufügen, but starting from
  // tracks already visible here instead of a separate search). Array, not
  // a Set, so playlist order matches the order tracks were checked in.
  let selectedTracks = [];

  // Sort/filter state, persisted across reloads so the chosen view survives
  // a page refresh - purely a display concern, never sent to the backend.
  const LIBRARY_VIEW_KEY = "owlbox.library.view";
  let libraryView = { sort: "added-desc", chip: "all", type: "all" };
  try {
    const saved = JSON.parse(localStorage.getItem(LIBRARY_VIEW_KEY) || "{}");
    libraryView = Object.assign(libraryView, saved);
  } catch (err) {
    /* corrupt/old value - fall back to defaults above */
  }
  function saveLibraryView() {
    try {
      localStorage.setItem(LIBRARY_VIEW_KEY, JSON.stringify(libraryView));
    } catch (err) {
      /* private mode / storage full - view choice just won't survive a reload */
    }
  }

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

  // Hörstatistik: total listening time as "2h 14min" rather than mm:ss.
  function formatListeningDuration(seconds) {
    seconds = Math.floor(seconds || 0);
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    if (h > 0) return `${h}h ${m}min`;
    if (m > 0) return `${m} Min.`;
    return `${seconds} Sek.`;
  }

  // SQLite's datetime('now') returns "YYYY-MM-DD HH:MM:SS" in UTC with no
  // timezone marker - Date needs that spelled out to parse it consistently.
  function parseSqliteTimestamp(sqliteTimestamp) {
    if (!sqliteTimestamp) return null;
    return new Date(sqliteTimestamp.replace(" ", "T") + "Z").getTime();
  }

  function formatRelativeTime(sqliteTimestamp) {
    const ts = parseSqliteTimestamp(sqliteTimestamp);
    if (ts === null) return null;
    const diffSeconds = Math.max(0, (Date.now() - ts) / 1000);
    if (diffSeconds < 60) return "gerade eben";
    if (diffSeconds < 3600) return `vor ${Math.floor(diffSeconds / 60)} Min.`;
    if (diffSeconds < 86400) return `vor ${Math.floor(diffSeconds / 3600)} Std.`;
    return `vor ${Math.floor(diffSeconds / 86400)} Tag(en)`;
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
    allStories = stories;
    // A track can have vanished since the last render (its story or the
    // track itself got deleted, possibly cascaded away as part of some
    // other playlist) - drop it from the pending selection too, otherwise
    // "+ Playlist erstellen" would submit a stale, now-invalid track_id.
    const liveTrackIds = new Set(stories.flatMap((s) => (s.tracks || []).map((t) => t.id)));
    const prevCount = selectedTracks.length;
    selectedTracks = selectedTracks.filter((t) => liveTrackIds.has(t.id));
    if (selectedTracks.length !== prevCount) updateSelectionBar();
    renderFilteredStories();
  }

  // Sum of a story's own track lengths - not story.total_seconds, which is
  // accumulated *listened* time (Hörstatistik), a completely different
  // number. A livestream has no fixed length at all, hence null.
  function storyDurationSeconds(story) {
    if (story.stream_url) return null;
    return (story.tracks || []).reduce((sum, t) => sum + (t.duration || 0), 0);
  }

  function matchesQuery(story, query) {
    if (!query) return true;
    if (story.title.toLowerCase().includes(query)) return true;
    if (story.uid && story.uid.toLowerCase().includes(query)) return true;
    return (story.tracks || []).some((t) => (t.title || t.filename || "").toLowerCase().includes(query));
  }

  function matchesFilters(story) {
    if (libraryView.chip === "assigned" && !story.uid) return false;
    if (libraryView.chip === "unassigned" && story.uid) return false;
    if (libraryView.type === "stories" && story.stream_url) return false;
    if (libraryView.type === "streams" && !story.stream_url) return false;
    return true;
  }

  // Livestreams have no fixed length (storyDurationSeconds returns null for
  // them) - they're always pushed to the end of a length sort, in either
  // direction, rather than sorted as if their length were 0.
  function sortStories(stories, sortKey) {
    const arr = stories.slice();
    const byTitle = (a, b) => a.title.localeCompare(b.title, "de");
    const byDuration = (dir) => (a, b) => {
      const da = storyDurationSeconds(a);
      const db = storyDurationSeconds(b);
      if (da === null && db === null) return byTitle(a, b);
      if (da === null) return 1;
      if (db === null) return -1;
      return dir * (da - db);
    };
    switch (sortKey) {
      case "title-asc":
        arr.sort(byTitle);
        break;
      case "title-desc":
        arr.sort((a, b) => byTitle(b, a));
        break;
      case "duration-asc":
        arr.sort(byDuration(1));
        break;
      case "duration-desc":
        arr.sort(byDuration(-1));
        break;
      case "plays-desc":
        arr.sort((a, b) => b.play_count - a.play_count || byTitle(a, b));
        break;
      case "last-played-desc":
        arr.sort((a, b) => (parseSqliteTimestamp(b.last_played_at) || 0) - (parseSqliteTimestamp(a.last_played_at) || 0));
        break;
      case "added-asc":
        arr.sort((a, b) => (parseSqliteTimestamp(a.created_at) || 0) - (parseSqliteTimestamp(b.created_at) || 0));
        break;
      case "added-desc":
      default:
        arr.sort((a, b) => (parseSqliteTimestamp(b.created_at) || 0) - (parseSqliteTimestamp(a.created_at) || 0));
    }
    return arr;
  }

  // Client-side only - allStories is already the full, current list (kept
  // in sync by loadStories()), so search/sort/filter never need their own
  // round-trip, just a re-render of what's already in memory.
  function renderFilteredStories() {
    const query = librarySearch.value.trim().toLowerCase();
    const filtered = allStories.filter((s) => matchesFilters(s) && matchesQuery(s, query));
    renderStories(sortStories(filtered, libraryView.sort), allStories.length > 0);
  }
  librarySearch.addEventListener("input", renderFilteredStories);
  librarySort.addEventListener("change", () => {
    libraryView.sort = librarySort.value;
    saveLibraryView();
    renderFilteredStories();
  });

  function wireSegmentedFilter(group, stateKey) {
    group.querySelectorAll(".segmented-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        libraryView[stateKey] = btn.dataset.value;
        group.querySelectorAll(".segmented-btn").forEach((b) => b.classList.toggle("active", b === btn));
        saveLibraryView();
        renderFilteredStories();
      });
    });
  }
  wireSegmentedFilter(filterChipGroup, "chip");
  wireSegmentedFilter(filterTypeGroup, "type");

  // Apply the restored (or default) view state to the controls themselves,
  // so the very first render already matches what loadStories() will show -
  // otherwise the dropdown/buttons would silently disagree with the list
  // until the user touches one of them.
  librarySort.value = libraryView.sort;
  [
    [filterChipGroup, "chip"],
    [filterTypeGroup, "type"],
  ].forEach(([group, stateKey]) => {
    group.querySelectorAll(".segmented-btn").forEach((btn) => {
      btn.classList.toggle("active", btn.dataset.value === libraryView[stateKey]);
    });
  });

  const statsTotalPlays = document.getElementById("stats-total-plays");
  const statsTotalTime = document.getElementById("stats-total-time");
  const statsTopList = document.getElementById("stats-top-list");

  async function loadStats() {
    const stats = await api("/api/library/stats");
    statsTotalPlays.textContent = stats.total_plays;
    statsTotalTime.textContent = formatListeningDuration(stats.total_seconds);

    statsTopList.innerHTML = "";
    if (stats.top_stories.length === 0) {
      statsTopList.innerHTML = '<p class="hint">Noch keine Geschichte oder kein Livestream wurde abgespielt.</p>';
      return;
    }
    const list = document.createElement("ol");
    list.className = "np-upcoming-list";
    for (const s of stats.top_stories) {
      const li = document.createElement("li");
      const kind = s.is_stream ? "🔴 Livestream" : "Geschichte";
      li.textContent = `${s.title} - ${kind} · ${s.play_count}x gespielt · ${formatListeningDuration(s.total_seconds)}`;
      list.appendChild(li);
    }
    statsTopList.appendChild(list);
  }

  function trackRow(story, track, index, total) {
    const label = `${track.title || track.filename}`;
    const li = document.createElement("li");
    li.innerHTML = `
      <input type="checkbox" class="track-select" title="Für Playlist auswählen">
      <span class="track-order">
        <button data-action="up" ${index === 0 ? "disabled" : ""}>▲</button>
        <button data-action="down" ${index === total - 1 ? "disabled" : ""}>▼</button>
      </span>
      <span>${index + 1}. ${label} ${track.duration ? "(" + formatDuration(track.duration) + ")" : ""}</span>
      <button data-action="delete">🗑</button>
    `;
    const checkbox = li.querySelector(".track-select");
    checkbox.checked = selectedTracks.some((t) => t.id === track.id);
    checkbox.addEventListener("change", () => {
      if (checkbox.checked) {
        if (!selectedTracks.some((t) => t.id === track.id)) {
          selectedTracks.push({ id: track.id, label: `${label} - ${story.title}` });
        }
      } else {
        selectedTracks = selectedTracks.filter((t) => t.id !== track.id);
      }
      updateSelectionBar();
    });
    li.querySelector('[data-action="up"]').addEventListener("click", () => moveTrack(story, index, -1));
    li.querySelector('[data-action="down"]').addEventListener("click", () => moveTrack(story, index, 1));
    li.querySelector('[data-action="delete"]').addEventListener("click", async () => {
      await api(`/api/stories/${story.id}/tracks/${track.id}`, { method: "DELETE" });
      selectedTracks = selectedTracks.filter((t) => t.id !== track.id);
      updateSelectionBar();
      loadStories();
    });
    return li;
  }

  function updateSelectionBar() {
    let bar = document.getElementById("playlist-selection-bar");
    if (selectedTracks.length === 0) {
      if (bar) bar.hidden = true;
      document.body.classList.remove("has-playlist-selection");
      return;
    }
    document.body.classList.add("has-playlist-selection");
    if (!bar) {
      bar = document.createElement("div");
      bar.id = "playlist-selection-bar";
      bar.className = "playlist-selection-bar";
      document.body.appendChild(bar);
    }
    bar.hidden = false;
    bar.innerHTML = `
      <span class="playlist-selection-count">${selectedTracks.length} Titel ausgewählt</span>
      <button class="btn secondary small" id="clear-selection-btn" type="button">Auswahl aufheben</button>
      <button class="btn small" id="create-playlist-btn" type="button">+ Playlist erstellen</button>
    `;
    bar.querySelector("#clear-selection-btn").addEventListener("click", () => {
      selectedTracks = [];
      updateSelectionBar();
      renderCurrentSelectionState();
    });
    bar.querySelector("#create-playlist-btn").addEventListener("click", createPlaylistFromSelection);
  }

  // Selection lives outside the DOM the story rows get replaced with on every
  // loadStories() call, so after the list re-renders the checkboxes need to
  // be told which of the (freshly created) inputs should already be ticked.
  function renderCurrentSelectionState() {
    document.querySelectorAll(".track-list .track-select").forEach((cb) => {
      // trackRow() already sets .checked from selectedTracks at creation
      // time; this only runs after a manual "Auswahl aufheben" click,
      // where the DOM still exists and just needs unticking.
      cb.checked = false;
    });
  }

  async function createPlaylistFromSelection() {
    const title = (prompt("Name der neuen Playlist:") || "").trim();
    if (!title) return;
    try {
      const body = await api("/api/stories/from-tracks", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title, track_ids: selectedTracks.map((t) => t.id) }),
      });
      showToast(`Playlist "${body.title}" mit ${selectedTracks.length} Titel(n) erstellt.`);
      selectedTracks = [];
      updateSelectionBar();
      loadStories();
    } catch (err) {
      showToast(err.message, true);
    }
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

  function renderStories(stories, libraryHasAnyStories) {
    storyList.innerHTML = "";
    if (stories.length === 0) {
      storyList.innerHTML = libraryHasAnyStories
        ? '<p class="hint">Keine Geschichte passt zur aktuellen Suche/Filterung.</p>'
        : '<p class="hint">Noch keine Geschichten angelegt. <a href="/admin/add">Jetzt hinzufügen</a>.</p>';
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
      const subtitle = story.stream_url
        ? `🔴 Livestream · ${story.stream_url} · ${story.uid ? "Chip: " + story.uid : "kein Chip zugewiesen"}`
        : `${story.track_count} Titel · ${story.uid ? "Chip: " + story.uid : "kein Chip zugewiesen"}`;
      const relPlayed = formatRelativeTime(story.last_played_at);
      const statsLine =
        story.play_count > 0
          ? `${story.play_count}x gespielt · ${formatListeningDuration(story.total_seconds)} gehört · zuletzt ${relPlayed}`
          : "Noch nicht abgespielt";
      header.innerHTML = `
        ${story.cover_url ? `<img src="${story.cover_url}" alt="">` : '<div class="thumb-placeholder">🦉</div>'}
        <div class="story-meta">
          <div class="row-title">${story.title}</div>
          <div class="story-sub">${subtitle}</div>
          <div class="story-sub">${statsLine}</div>
        </div>
        <div class="story-actions">
          <button class="btn" data-action="play">▶️ Abspielen</button>
          <button class="btn secondary" data-action="assign">Chip zuweisen</button>
          ${story.uid ? '<button class="btn secondary" data-action="unassign">Chip entfernen</button>' : ""}
          <button class="btn secondary" data-action="change-cover">🖼️ Cover ändern</button>
          ${story.cover_url ? '<button class="btn secondary" data-action="remove-cover">Cover entfernen</button>' : ""}
          ${
            story.stream_url
              ? ""
              : `<button class="btn secondary" data-action="add-tracks">+ Weitere Tracks</button>
          <button class="btn secondary" data-action="shuffle">${story.shuffle ? "🔀 an" : "🔀 aus"}</button>
          <div class="segmented" data-action="repeat-group" title="Wiederholung">
            <button type="button" class="segmented-btn${story.repeat === "off" ? " active" : ""}" data-mode="off">Aus</button>
            <button type="button" class="segmented-btn${story.repeat === "folder" ? " active" : ""}" data-mode="folder">🔁 Ordner</button>
            <button type="button" class="segmented-btn${story.repeat === "track" ? " active" : ""}" data-mode="track">🔂 Track</button>
          </div>`
          }
          <button class="btn danger" data-action="delete">Löschen</button>
        </div>
        <p class="field-help">
          „Abspielen“ startet diese Geschichte sofort, genau wie das Auflegen ihres Chips - auch
          ohne dass ihr überhaupt ein Chip zugewiesen ist. „Chip zuweisen“ verknüpft den nächsten
          aufgelegten Chip mit dieser Geschichte, „Chip entfernen“ löst die Verknüpfung wieder
          (löscht die Geschichte nicht). „Cover ändern“ ersetzt das Vorschaubild jederzeit, egal
          wie die Geschichte ursprünglich angelegt wurde - praktisch besonders bei Livestream- und
          Ganzer-Ordner-Einträgen, wo oft erst nachträglich ein passendes Bild zur Hand ist.
          „+ Weitere Tracks“ hängt zusätzliche Audiodateien hinten an
          diese Geschichte an, statt eine neue anzulegen - praktisch für ein Hörbuch auf mehreren
          CDs: jede CD einzeln über diesen Button nachladen, alle landen in derselben Geschichte, in
          der Reihenfolge des Hinzufügens. Shuffle mischt die Tracks zufällig. „Ordner“ wiederholt
          die ganze Geschichte endlos, „Track“ nur den gerade laufenden Titel, „Aus“ beendet die
          Wiedergabe nach dem letzten Track - wirkt sofort, falls diese Geschichte gerade läuft.
          „Löschen“ entfernt die Geschichte inklusive aller Audiodateien unwiderruflich.
        </p>
      `;
      const addTracksBtn = header.querySelector('[data-action="add-tracks"]');
      if (addTracksBtn) {
        addTracksBtn.addEventListener("click", () => {
          addTracksTargetId = story.id;
          addTracksInput.value = ""; // otherwise re-selecting the exact same file(s) wouldn't fire "change"
          addTracksInput.click();
        });
      }
      header.querySelector('[data-action="play"]').addEventListener("click", async () => {
        try {
          await api(`/api/stories/${story.id}/play`, { method: "POST" });
          showToast(`„${story.title}“ wird abgespielt.`);
        } catch (err) {
          showToast(err.message, true);
        }
      });
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
      header.querySelector('[data-action="change-cover"]').addEventListener("click", () => {
        changeCoverTargetId = story.id;
        changeCoverInput.value = ""; // otherwise re-selecting the exact same file wouldn't fire "change"
        changeCoverInput.click();
      });
      const removeCoverBtn = header.querySelector('[data-action="remove-cover"]');
      if (removeCoverBtn) {
        removeCoverBtn.addEventListener("click", async () => {
          try {
            await api(`/api/stories/${story.id}/cover`, { method: "DELETE" });
            showToast("Cover entfernt.");
            loadStories();
          } catch (err) {
            showToast(err.message, true);
          }
        });
      }
      const shuffleBtn = header.querySelector('[data-action="shuffle"]');
      if (shuffleBtn) {
        shuffleBtn.addEventListener("click", async () => {
          await api(`/api/stories/${story.id}/flags`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ shuffle: !story.shuffle }),
          });
          loadStories();
        });
      }
      const repeatGroup = header.querySelector('[data-action="repeat-group"]');
      if (repeatGroup) {
        repeatGroup.querySelectorAll(".segmented-btn").forEach((btn) => {
          btn.addEventListener("click", async () => {
            try {
              await api(`/api/stories/${story.id}/flags`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ repeat: btn.dataset.mode }),
              });
              loadStories();
            } catch (err) {
              showToast(err.message, true);
            }
          });
        });
      }
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
      if (story.tracks.length > 0) {
        const trackHelp = document.createElement("p");
        trackHelp.className = "field-help";
        trackHelp.textContent =
          "Checkbox markiert einen Titel für eine neue Playlist (unten erscheint dann eine Leiste " +
          "zum Erstellen) - auch über mehrere Geschichten hinweg kombinierbar. ▲/▼ verschieben einen " +
          "Track in der Abspielreihenfolge, das Papierkorb-Symbol entfernt ihn aus der Geschichte " +
          "(die Datei wird dabei ebenfalls gelöscht, auch aus Playlists, die ihn enthalten).";
        row.appendChild(trackHelp);
      }
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

  addTracksInput.addEventListener("change", async () => {
    const files = Array.from(addTracksInput.files || []);
    const storyId = addTracksTargetId;
    if (!storyId || files.length === 0) return;
    const formData = new FormData();
    files.forEach((f) => formData.append("audio_files", f));
    try {
      await api(`/api/stories/${storyId}/tracks`, { method: "POST", body: formData });
      showToast(`${files.length} Track(s) hinzugefügt.`);
      loadStories();
    } catch (err) {
      showToast(err.message, true);
    }
  });

  changeCoverInput.addEventListener("change", async () => {
    const file = (changeCoverInput.files || [])[0];
    const storyId = changeCoverTargetId;
    if (!storyId || !file) return;
    const formData = new FormData();
    formData.append("cover", file);
    try {
      await api(`/api/stories/${storyId}/cover`, { method: "POST", body: formData });
      showToast("Cover geändert.");
      loadStories();
    } catch (err) {
      showToast(err.message, true);
    }
  });

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
  loadStats();
})();
