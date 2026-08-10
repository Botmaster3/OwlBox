// Tier-Sound-Quiz mini-game (a sound plays, tap the matching picture) - one
// of several mini-games under the Spiele-Menü (see game.js, which owns
// menu/switching and calls window.OwlBoxGameQuiz.start()/stop() at the right
// moments). Content is picture+sound pairs uploaded under Einstellungen ->
// Spiel (/api/quiz/items) - a separate pool from Memory's plain pictures,
// since each entry here needs both an image and a matching sound.
(function () {
  const containerEl = document.getElementById("game-quiz");
  const boardWrapEl = document.getElementById("game-quiz-board-wrap");
  const emptyHintEl = document.getElementById("game-quiz-empty-hint");
  const gridEl = document.getElementById("game-quiz-grid");
  const scoreEl = document.getElementById("game-quiz-score");
  const roundEl = document.getElementById("game-quiz-round");
  const totalEl = document.getElementById("game-quiz-total");
  const replayBtn = document.getElementById("game-quiz-replay-btn");
  const winBannerEl = document.getElementById("game-quiz-win-banner");
  const finalScoreEl = document.getElementById("game-quiz-final-score");
  const againBtn = document.getElementById("game-quiz-again-btn");

  const TOTAL_ROUNDS = 8;
  const MAX_OPTIONS = 4;
  // Needs at least one distractor to be a real quiz - see start()'s pool
  // length check below.
  const MIN_ITEMS = 2;
  const REVEAL_DELAY_MS = 1300;

  let items = [];
  let round = 0;
  let score = 0;
  let boardLocked = false;
  let currentSoundUrl = null;
  let pendingTimeout = null;

  totalEl.textContent = String(TOTAL_ROUNDS);

  function shuffled(array) {
    const copy = array.slice();
    for (let i = copy.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [copy[i], copy[j]] = [copy[j], copy[i]];
    }
    return copy;
  }

  function playCurrentSound() {
    if (!currentSoundUrl) return;
    try {
      new Audio(currentSoundUrl).play().catch(() => {
        // Autoplay blocked or similar - the replay button lets the player
        // trigger it again with their own tap, which always counts as a
        // fresh user gesture.
      });
    } catch (err) {
      // Audio unsupported - the picture options still let the round proceed.
    }
  }

  function buildRoundOptions() {
    const optionCount = Math.min(MAX_OPTIONS, items.length);
    const correct = items[Math.floor(Math.random() * items.length)];
    const distractorPool = items.filter((item) => item.id !== correct.id);
    const distractors = shuffled(distractorPool).slice(0, optionCount - 1);
    return { correct, options: shuffled([correct, ...distractors]) };
  }

  function handleOptionTap(item, optionEl) {
    if (boardLocked) return;
    boardLocked = true;
    const options = Array.from(gridEl.children);

    if (item.correct) {
      score += 1;
      scoreEl.textContent = String(score);
      optionEl.classList.add("correct");
    } else {
      optionEl.classList.add("wrong");
      const correctEl = options.find((el) => el.dataset.correct === "true");
      if (correctEl) correctEl.classList.add("correct");
    }

    pendingTimeout = setTimeout(() => {
      if (round >= TOTAL_ROUNDS) {
        finish();
      } else {
        newRound();
      }
    }, REVEAL_DELAY_MS);
  }

  function newRound() {
    round += 1;
    roundEl.textContent = String(round);
    boardLocked = false;
    gridEl.innerHTML = "";

    const { correct, options } = buildRoundOptions();
    currentSoundUrl = correct.sound_url;

    const columns = options.length <= 2 ? options.length : Math.ceil(Math.sqrt(options.length));
    gridEl.style.gridTemplateColumns = `repeat(${columns}, 1fr)`;

    options.forEach((item) => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "game-quiz-option";
      btn.dataset.correct = String(item.id === correct.id);
      btn.setAttribute("aria-label", item.label || "Antwortmöglichkeit");
      btn.innerHTML = `<img src="${item.image_url}" alt="">`;
      btn.addEventListener("click", () => handleOptionTap({ correct: item.id === correct.id }, btn));
      gridEl.appendChild(btn);
    });

    playCurrentSound();
  }

  function finish() {
    finalScoreEl.textContent = `${score} von ${TOTAL_ROUNDS} richtig`;
    boardWrapEl.hidden = true;
    winBannerEl.hidden = false;
  }

  function beginGame() {
    winBannerEl.hidden = true;
    boardWrapEl.hidden = false;
    round = 0;
    score = 0;
    scoreEl.textContent = "0";
    newRound();
  }

  replayBtn.addEventListener("click", playCurrentSound);
  againBtn.addEventListener("click", beginGame);

  async function start() {
    containerEl.hidden = false;
    boardWrapEl.hidden = true;
    winBannerEl.hidden = true;
    try {
      const res = await fetch("/api/quiz/items");
      const fetched = await res.json();
      items = Array.isArray(fetched) ? fetched : [];
      if (items.length < MIN_ITEMS) {
        emptyHintEl.hidden = false;
        return;
      }
      emptyHintEl.hidden = true;
      beginGame();
    } catch (err) {
      emptyHintEl.hidden = false;
    }
  }

  function stop() {
    if (pendingTimeout) {
      clearTimeout(pendingTimeout);
      pendingTimeout = null;
    }
    boardLocked = false;
    containerEl.hidden = true;
  }

  window.OwlBoxGameQuiz = { start, stop };
})();
