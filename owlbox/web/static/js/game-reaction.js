// Reaktionsspiel mini-game (Whack-a-Mole-artig: tap the owl before it
// disappears) - one of several mini-games under the Spiele-Menü (see
// game.js, which owns menu/switching and calls window.OwlBoxGameReaction.
// start()/stop() at the right moments). No uploaded content needed.
(function () {
  const containerEl = document.getElementById("game-reaction");
  const difficultyEl = document.getElementById("game-reaction-difficulty");
  const difficultyBtns = document.querySelectorAll(".game-reaction-difficulty-btn");
  const boardWrapEl = document.getElementById("game-reaction-board-wrap");
  const gridEl = document.getElementById("game-reaction-grid");
  const scoreEl = document.getElementById("game-reaction-score");
  const totalEl = document.getElementById("game-reaction-total");
  const winBannerEl = document.getElementById("game-reaction-win-banner");
  const finalScoreEl = document.getElementById("game-reaction-final-score");
  const againBtn = document.getElementById("game-reaction-again-btn");
  const changeDifficultyBtn = document.getElementById("game-reaction-change-difficulty-btn");

  const HOLE_COUNT = 9; // fixed 3x3 grid regardless of difficulty
  const TOTAL_ROUNDS = 15;
  // Difficulty only changes pacing, not the grid - how long the owl stays
  // up (dwellMs) and the pause before the next one appears (gapMs).
  const SETTINGS_BY_DIFFICULTY = {
    leicht: { dwellMs: 1400, gapMs: 900 },
    mittel: { dwellMs: 1000, gapMs: 650 },
    schwer: { dwellMs: 700, gapMs: 450 },
  };

  let holes = [];
  let currentSettings = SETTINGS_BY_DIFFICULTY.mittel;
  let activeHole = null;
  let hitThisRound = false;
  let round = 0;
  let score = 0;
  let pendingTimeout = null;

  totalEl.textContent = String(TOTAL_ROUNDS);

  function ensureHoles() {
    if (holes.length === HOLE_COUNT) return;
    gridEl.innerHTML = "";
    holes = [];
    for (let i = 0; i < HOLE_COUNT; i++) {
      const hole = document.createElement("button");
      hole.type = "button";
      hole.className = "game-reaction-hole";
      hole.setAttribute("aria-label", "Loch");
      hole.innerHTML = '<span class="game-reaction-owl">🦉</span>';
      hole.addEventListener("click", () => handleHoleTap(i));
      gridEl.appendChild(hole);
      holes.push(hole);
    }
  }

  function scheduleNext() {
    if (round >= TOTAL_ROUNDS) {
      finish();
      return;
    }
    round += 1;
    activeHole = Math.floor(Math.random() * HOLE_COUNT);
    hitThisRound = false;
    holes[activeHole].classList.add("active");
    pendingTimeout = setTimeout(onDwellExpired, currentSettings.dwellMs);
  }

  function onDwellExpired() {
    if (activeHole !== null) holes[activeHole].classList.remove("active");
    activeHole = null;
    pendingTimeout = setTimeout(scheduleNext, currentSettings.gapMs);
  }

  function handleHoleTap(index) {
    if (index !== activeHole || hitThisRound) return;
    hitThisRound = true;
    score += 1;
    scoreEl.textContent = String(score);
    holes[index].classList.remove("active");
    holes[index].classList.add("hit");
    setTimeout(() => holes[index].classList.remove("hit"), 200);
    clearTimeout(pendingTimeout);
    activeHole = null;
    pendingTimeout = setTimeout(scheduleNext, currentSettings.gapMs);
  }

  function finish() {
    finalScoreEl.textContent = `${score} von ${TOTAL_ROUNDS} getroffen`;
    winBannerEl.hidden = false;
  }

  function beginRound(difficultyKey) {
    currentSettings = SETTINGS_BY_DIFFICULTY[difficultyKey] || SETTINGS_BY_DIFFICULTY.mittel;
    difficultyEl.hidden = true;
    winBannerEl.hidden = true;
    boardWrapEl.hidden = false;
    ensureHoles();
    holes.forEach((hole) => hole.classList.remove("active", "hit"));
    activeHole = null;
    hitThisRound = false;
    round = 0;
    score = 0;
    scoreEl.textContent = "0";
    pendingTimeout = setTimeout(scheduleNext, 500);
  }

  function showDifficultyScreen() {
    boardWrapEl.hidden = true;
    winBannerEl.hidden = true;
    difficultyEl.hidden = false;
  }

  let lastDifficulty = "mittel";
  difficultyBtns.forEach((btn) => {
    btn.addEventListener("click", () => {
      lastDifficulty = btn.dataset.difficulty;
      beginRound(lastDifficulty);
    });
  });

  againBtn.addEventListener("click", () => beginRound(lastDifficulty));
  changeDifficultyBtn.addEventListener("click", showDifficultyScreen);

  function start() {
    containerEl.hidden = false;
    difficultyEl.hidden = true;
    boardWrapEl.hidden = true;
    winBannerEl.hidden = true;
    showDifficultyScreen();
  }

  function stop() {
    if (pendingTimeout) {
      clearTimeout(pendingTimeout);
      pendingTimeout = null;
    }
    activeHole = null;
    containerEl.hidden = true;
  }

  window.OwlBoxGameReaction = { start, stop };
})();
