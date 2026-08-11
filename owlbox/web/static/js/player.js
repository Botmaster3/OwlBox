(function () {
  const coverImg = document.getElementById("cover");
  const coverPlaceholder = document.getElementById("cover-placeholder");
  const storyTitleEl = document.getElementById("story-title");
  const storyTitleTextEl = document.getElementById("story-title-text");
  const trackTitleEl = document.getElementById("track-title");
  const playbackFlagsEl = document.getElementById("playback-flags");
  const flagShuffleEl = document.getElementById("flag-shuffle");
  const flagRepeatEl = document.getElementById("flag-repeat");
  const timePosEl = document.getElementById("time-pos");
  const timeRemainingEl = document.getElementById("time-remaining");
  const progressRow = document.getElementById("progress-row");
  const upcomingEl = document.getElementById("upcoming");
  const upcomingListEl = document.getElementById("upcoming-list");
  const progressFill = document.getElementById("progress-fill");
  const volumeFill = document.getElementById("volume-fill");
  const unknownBanner = document.getElementById("unknown-banner");
  const playerEl = document.querySelector(".player");
  const parentModeEl = document.getElementById("parent-mode");
  const sleepModeEl = document.getElementById("sleep-mode");
  const parentModeLabelEl = document.getElementById("parent-mode-label");
  const parentModeQrEl = document.getElementById("parent-mode-qr");
  const sleepTimerBadge = document.getElementById("sleep-timer-badge");
  const sleepTimerRemaining = document.getElementById("sleep-timer-remaining");
  const splashEl = document.getElementById("splash");
  const brightnessOsd = document.getElementById("brightness-osd");
  const brightnessOsdIcon = document.getElementById("brightness-osd-icon");
  const brightnessOsdValue = document.getElementById("brightness-osd-value");
  const brightnessOsdFill = document.getElementById("brightness-osd-fill");
  const nightModeBadge = document.getElementById("night-mode-badge");
  const airplayBadge = document.getElementById("airplay-badge");
  const wifiBars = document.querySelectorAll("#wifi-bars .wifi-bar");
  const wifiLabel = document.getElementById("wifi-label");
  const statusBarEl = document.getElementById("status-bar");
  const cpuTempBadge = document.getElementById("cpu-temp-badge");
  const cpuTempValueEl = document.getElementById("cpu-temp-value");
  const hotspotBanner = document.getElementById("hotspot-banner");
  const hotspotSsidEl = document.getElementById("hotspot-ssid");
  const hotspotPasswordEl = document.getElementById("hotspot-password");
  const hotspotUrlEl = document.getElementById("hotspot-url");
  const vuBars = document.querySelectorAll("#vu-meter .vu-bar");

  let lastCoverUrl = null;
  let lastStoryTitle = null;
  let parentModeActive = false;
  let gameModeActive = false;
  let hasScannedTag = false;
  let lastBrightness = null;
  let lastNightModeActive = null;
  let brightnessOsdTimer = null;
  let vuBarsSet = false;

  // Decorative "is audio playing" animation, not a real audio-level analysis -
  // mpv doesn't expose one over the IPC socket we already talk to it through.
  // NOT actually animated anymore - a previous session already throttled this
  // from repainting 5 bars ~7-8x/second down to ~2x/second (450ms), reasoning
  // that was still "alive"-looking without stealing too much CPU from mpv's
  // audio thread on this Pi's fully software-rendered Chromium (no GPU access
  // at all, see docs/hardware.md). Confirmed on real hardware that even that
  // throttled rate wasn't enough - continuous audible crackling during
  // playback persisted, traced specifically to this: every 450ms tick was
  // also driving a 0.12s CSS `transition: height` on 5 bars at once (see
  // style.css), which is several additional compositor frames per tick, not
  // just one - on top of everything else already competing for this Pi 3B+'s
  // limited cycles (kiosk vs. audio, see systemd/owlbox-kiosk.service's
  // Nice=). Now sets each bar's height exactly once when playback starts
  // (still reads as "something is playing" at a glance) instead of on a
  // recurring timer - zero ongoing repaint cost either way once set.
  function setVuPlaying(playing) {
    if (playing) {
      if (vuBarsSet) return;
      vuBarsSet = true;
      vuBars.forEach((bar) => {
        bar.style.height = `${12 + Math.random() * 85}%`;
      });
    } else if (vuBarsSet) {
      vuBarsSet = false;
      vuBars.forEach((bar) => {
        bar.style.height = "12%";
      });
    }
  }

  // Fill percentage of a value relative to a [min, max] range, e.g. how full
  // the brightness/volume bar should look given the configured limits rather
  // than the raw 0-100 value.
  function relativePercent(value, min, max) {
    if (max <= min) return 0;
    return Math.max(0, Math.min(100, ((value - min) / (max - min)) * 100));
  }

  function showBrightnessOsd(percent, min, max, nightModeActive) {
    brightnessOsdIcon.textContent = nightModeActive ? "🌙" : "☀️";
    brightnessOsdValue.textContent = percent;
    // Night mode deliberately goes below min (see Engine.toggle_night_mode) -
    // the relative-fill bar would otherwise clamp to 0% instead of showing
    // how dim it actually went, so widen the range just for that reading.
    brightnessOsdFill.style.width = `${relativePercent(percent, nightModeActive ? Math.min(min, percent) : min, max)}%`;
    brightnessOsd.hidden = false;
    clearTimeout(brightnessOsdTimer);
    brightnessOsdTimer = setTimeout(() => {
      brightnessOsd.hidden = true;
    }, 2000);
  }

  // Traffic-light coloring: green from a solid connection, yellow once it's
  // getting weak, red when it's barely usable or there's no connection at all.
  function wifiSignalClass(enabled, signal) {
    if (!enabled || typeof signal !== "number") return "critical";
    if (signal >= 60) return "good";
    if (signal >= 30) return "warn";
    return "critical";
  }

  function applyWifi(wifi) {
    wifi = wifi || {};
    const cls = wifiSignalClass(wifi.enabled, wifi.signal);
    const activeBars =
      wifi.enabled && typeof wifi.signal === "number"
        ? Math.min(4, Math.max(0, Math.ceil((wifi.signal / 100) * 4)))
        : 0;
    wifiBars.forEach((bar, index) => {
      bar.classList.remove("active", "good", "warn", "critical");
      if (index < activeBars) {
        bar.classList.add("active", cls);
      }
    });
    if (!wifi.enabled) {
      wifiLabel.textContent = "Aus";
    } else if (typeof wifi.signal !== "number") {
      wifiLabel.textContent = "Getrennt";
    } else {
      wifiLabel.textContent = `${wifi.signal}%`;
    }
  }

  // Same soft-throttle cutoff the Pi 3B+ itself uses (~80°C, confirmed via
  // vcgencmd get_throttled on real hardware) - "warn" a bit below that so
  // a climbing temperature is visible before it actually starts throttling.
  function applyCpuTemp(system) {
    system = system || {};
    const temp = system.cpu_temp_celsius;
    cpuTempBadge.classList.remove("warn", "critical");
    if (typeof temp !== "number") {
      cpuTempValueEl.textContent = "–";
      return;
    }
    cpuTempValueEl.textContent = Math.round(temp);
    if (temp >= 80) {
      cpuTempBadge.classList.add("critical");
    } else if (temp >= 70) {
      cpuTempBadge.classList.add("warn");
    }
  }

  function applyHotspotBanner(wifi) {
    wifi = wifi || {};
    if (!wifi.hotspot_active) {
      hotspotBanner.hidden = true;
      statusBarEl.hidden = false;
      return;
    }
    hotspotSsidEl.textContent = wifi.hotspot_ssid;
    hotspotPasswordEl.textContent = wifi.hotspot_password;
    const port = window.location.port ? `:${window.location.port}` : "";
    hotspotUrlEl.textContent = `http://${wifi.hotspot_ip}${port}/admin`;
    hotspotBanner.hidden = false;
    // The banner already covers WiFi state plus what to do about it - showing
    // both at once is redundant and there isn't room for both on a small screen.
    statusBarEl.hidden = true;
  }

  // NOT a scrolling marquee anymore - a long title now just truncates with
  // "..." (see .story-title's text-overflow in style.css) instead of
  // continuously animating. Confirmed on real hardware as a major
  // contributor to a "continuous crackling during playback" complaint that
  // survived every other fix tried (config.txt/kernel overlays, removing
  // unnecessary subprocess spawns from the app's hot paths, deprioritizing
  // the kiosk vs. owlbox.service): the marquee's CSS
  // animation-iteration-count: infinite kept the title's compositor layer
  // repainting at up to 60fps for as long as a long title was on screen -
  // on this Pi's fully software-rendered Chromium (no GPU access at all,
  // see docs/hardware.md), that's a far bigger, far more sustained repaint
  // load than the VU-meter dots ever were (see setVuPlaying above, already
  // fixed for the same reason) - it ran for the whole story, not just a
  // few ticks. Simply not doing continuous animation at all beats trying to
  // throttle it further, same reasoning the design themes already apply
  // (static images instead of running animations - see themes.py).
  function setStoryTitle(text) {
    if (text === lastStoryTitle) return;
    lastStoryTitle = text;
    storyTitleTextEl.textContent = text;
  }

  function formatTime(seconds) {
    seconds = Math.max(0, Math.floor(seconds || 0));
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return `${m}:${String(s).padStart(2, "0")}`;
  }

  // The "custom" theme's colors live as inline CSS custom properties on
  // <html> (see base.html/web/__init__.py) instead of a static per-theme
  // CSS block, since they're user-supplied. Re-applied on every poll rather
  // than only on a theme change - the colors themselves can change while
  // "custom" stays the active theme (editing Eigenes Design again) - cheap
  // enough (ten property writes) that there's no need to track and compare
  // the previous values just to skip redundant ones.
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

  function applyState(state) {
    // Shown regardless of splash/parent-mode/tag state, like a phone's own
    // status bar - the brightness OSD change-detection needs it up here too.
    const settings = state.settings || {};
    // Applied even before any tag is scanned (splash screen) and regardless
    // of parent-mode/sleep-mode - the kiosk page loads once and stays open
    // for days, so a theme changed from Einstellungen needs to reach it live
    // rather than only on the next full page reload.
    if (settings.theme && document.documentElement.dataset.theme !== settings.theme) {
      document.documentElement.dataset.theme = settings.theme;
    }
    if (settings.theme) {
      applyCustomThemeVars(settings.theme, settings.custom_theme_colors);
    }
    // Only visible on the Weihnachten theme, but a kiosk left open overnight
    // into a new Advent Sunday should still see the new candle lit live.
    const adventCandles = String(settings.advent_candles);
    if (typeof settings.advent_candles === "number" && document.documentElement.dataset.adventCandles !== adventCandles) {
      document.documentElement.dataset.adventCandles = adventCandles;
      // Nudge a reflow so the animated wreath (.advent-wreath::after) is
      // guaranteed to pick up the new candle count right away rather than
      // waiting for its next unrelated style change.
      void document.documentElement.offsetHeight;
    }
    // Same idea as advent_candles just above, for the one-day "Geschenke"
    // decoration (see .christmas-gifts in style.css) - a kiosk already open
    // when the 24th begins should still pick it up without a page reload.
    if (typeof settings.christmas_eve === "boolean") {
      document.documentElement.dataset.christmasEve = String(settings.christmas_eve);
    }
    if (typeof settings.brightness === "number") {
      const nightModeActive = !!settings.night_mode_active;
      const brightnessChanged = lastBrightness !== null && settings.brightness !== lastBrightness;
      // Also trigger on a night-mode flip with no brightness change - e.g.
      // night_brightness happens to equal the current day brightness, still
      // worth surfacing that the mode itself just switched.
      const nightModeChanged = lastNightModeActive !== null && nightModeActive !== lastNightModeActive;
      if (lastBrightness !== null && (brightnessChanged || nightModeChanged)) {
        showBrightnessOsd(settings.brightness, settings.min_brightness, settings.max_brightness, nightModeActive);
      }
      lastBrightness = settings.brightness;
      lastNightModeActive = nightModeActive;
      nightModeBadge.hidden = !nightModeActive;
    }
    airplayBadge.hidden = !state.airplay.active;
    applyWifi(state.wifi);
    applyHotspotBanner(state.wifi);
    applyCpuTemp(state.system);

    const story = state.story;
    const player = state.player || {};
    const parentMode = state.parent_mode || { active: false, label: null };

    // On boot, show the OwlBox splash (owl + name) instead of the "no chip"
    // now-playing view - it only goes away once any chip (story, function, or
    // parent tag) has actually been read, and stays gone for the rest of this
    // page load even after that chip is removed again.
    if (!hasScannedTag) {
      if (!state.uid) {
        return;
      }
      hasScannedTag = true;
      splashEl.hidden = true;
    }

    // Parent mode (a "Vater"/"Mutter" chip is on the reader) shows a QR code to
    // the login page instead of the normal now-playing view - never revealed to
    // kids scanning story or function tags.
    if (parentMode.active !== parentModeActive) {
      parentModeActive = parentMode.active;
      if (parentModeActive) {
        // Generate the QR code fresh at the moment the chip is scanned - the IP it
        // encodes may have changed since the last time a parent tag was placed, and
        // the kiosk page itself never reloads on its own to pick that up otherwise.
        parentModeQrEl.src = `/login-qr.svg?t=${Date.now()}`;
      }
    }
    parentModeEl.hidden = !parentModeActive;
    playerEl.hidden = parentModeActive;
    if (parentModeActive) {
      parentModeLabelEl.textContent = `Eltern-Modus: ${parentMode.label}`;
      return;
    }

    // Memory game (a dedicated function-chip toggles this - see Kapitel
    // "Spiel" in Einstellungen): takes over the whole display until toggled
    // off again, but doesn't touch playback - a story can keep playing in
    // the background. Takes priority over auto-sleep below on purpose: a
    // paused story shouldn't put the kiosk to sleep while a kid is actively
    // playing. window.OwlBoxGame comes from game.js, loaded before this file.
    const gameMode = state.game_mode || { active: false };
    if (gameMode.active !== gameModeActive) {
      gameModeActive = gameMode.active;
      if (window.OwlBoxGame) {
        if (gameModeActive) window.OwlBoxGame.start();
        else window.OwlBoxGame.stop();
      }
    }
    if (gameModeActive) {
      playerEl.hidden = true;
      sleepModeEl.hidden = true;
      return;
    }

    // Auto-sleep: the story has been paused long enough that the box shows a
    // sleeping owl instead of the now-playing view. Raising the volume,
    // pressing play/pause, or scanning a tag wakes it back up (engine-side) -
    // the state then simply stops reporting auto_sleep.active on the next poll.
    const autoSleep = state.auto_sleep || { active: false };
    sleepModeEl.hidden = !autoSleep.active;
    if (autoSleep.active) {
      playerEl.hidden = true;
      return;
    }

    if (story) {
      setStoryTitle(story.title);
    } else if (state.unknown_tag) {
      setStoryTitle("Unbekannter Chip");
    } else {
      setStoryTitle("Kein Chip aufgelegt");
    }

    if (story && story.is_stream) {
      trackTitleEl.textContent = "🔴 Live-Stream";
      trackTitleEl.hidden = false;
    } else if (story && story.track_title) {
      trackTitleEl.textContent = story.track_title;
      trackTitleEl.hidden = false;
    } else {
      trackTitleEl.hidden = true;
    }
    progressRow.hidden = !!(story && story.is_stream);

    // Shuffle/Wiederholung don't apply to a livestream (no fixed playlist to
    // shuffle or loop) - same exclusion the admin Home widget uses. Each pill
    // hides individually and the whole row collapses once neither is active,
    // so this stays invisible for the common case (both off).
    const shuffleRepeatUsable = !!(story && !story.is_stream);
    const shuffleActive = shuffleRepeatUsable && !!story.shuffle;
    const repeatMode = shuffleRepeatUsable ? story.repeat : "off";
    flagShuffleEl.hidden = !shuffleActive;
    if (repeatMode === "folder") {
      flagRepeatEl.textContent = "🔁 Ordner";
      flagRepeatEl.hidden = false;
    } else if (repeatMode === "track") {
      flagRepeatEl.textContent = "🔂 Track";
      flagRepeatEl.hidden = false;
    } else {
      flagRepeatEl.hidden = true;
    }
    playbackFlagsEl.hidden = !shuffleActive && repeatMode === "off";

    const coverUrl = story && story.cover_url ? story.cover_url : null;
    if (coverUrl !== lastCoverUrl) {
      lastCoverUrl = coverUrl;
      if (coverUrl) {
        coverImg.src = coverUrl;
        coverImg.hidden = false;
        coverPlaceholder.hidden = true;
      } else {
        coverImg.hidden = true;
        coverPlaceholder.hidden = false;
      }
    }

    const timePos = player.time_pos || 0;
    const duration = player.duration || 0;
    timePosEl.textContent = formatTime(timePos);
    timeRemainingEl.textContent = `-${formatTime(duration - timePos)}`;
    progressFill.style.width = duration > 0 ? `${Math.min(100, (timePos / duration) * 100)}%` : "0%";

    // The kiosk's "Tracks" list is meant as a look-ahead, not a full
    // tracklist - the currently playing track already has its own row
    // (#track-title) above, so tracks at or before current_track_index would
    // just be clutter/already-heard here. Filtered to strictly upcoming ones,
    // and capped to the next 3 - the point is a quick glance at what's next,
    // not the whole rest of the story (that's what the admin Home widget's
    // full, scrollable tracklist is for).
    const allTracks = (story && story.tracks) || [];
    const currentTrackIndex = story && typeof story.current_track_index === "number" ? story.current_track_index : -1;
    const upcomingTracks = allTracks.filter((_, index) => index > currentTrackIndex).slice(0, 3);
    if (upcomingTracks.length === 0) {
      upcomingEl.hidden = true;
    } else {
      upcomingEl.hidden = false;
      upcomingListEl.innerHTML = upcomingTracks.map((title) => `<li>${title}</li>`).join("");
    }

    volumeFill.style.width = `${relativePercent(player.volume || 0, 0, settings.max_volume || 100)}%`;
    setVuPlaying(!!player.playing);

    unknownBanner.hidden = !state.unknown_tag;

    const sleepTimer = state.sleep_timer || {};
    if (sleepTimer.active) {
      sleepTimerBadge.hidden = false;
      sleepTimerRemaining.textContent = formatTime(sleepTimer.remaining_seconds);
    } else {
      sleepTimerBadge.hidden = true;
    }
  }

  async function poll() {
    try {
      const res = await fetch("/api/state");
      if (res.ok) {
        applyState(await res.json());
      }
    } catch (err) {
      // network hiccup, just try again next tick
    } finally {
      setTimeout(poll, 1000);
    }
  }

  poll();
})();
