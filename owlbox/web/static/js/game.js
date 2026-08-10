// Memory game shown on the kiosk display while game mode is active (see
// player.js, which owns view switching and calls window.OwlBoxGame.start()/
// stop() at the right moments). This is the one screen in the whole kiosk
// where touch input actually does anything - everywhere else is look-only,
// see docs/hardware.md.
(function () {
  const gameModeEl = document.getElementById("game-mode");
  const difficultyEl = document.getElementById("game-difficulty");
  const difficultyBtns = document.querySelectorAll(".game-difficulty-btn");
  const gridEl = document.getElementById("game-grid");
  const emptyHintEl = document.getElementById("game-empty-hint");
  const winBannerEl = document.getElementById("game-win-banner");
  const winMovesEl = document.getElementById("game-win-moves");
  const againBtn = document.getElementById("game-again-btn");
  const changeDifficultyBtn = document.getElementById("game-change-difficulty-btn");

  // Cards auto-size to fit however many pairs a round has (see layoutGrid()
  // below) - the actual cap on how many pairs one round pulls out of the
  // pool is picked by the player via the difficulty screen shown on every
  // game-mode activation. Extra uploaded images beyond a given difficulty's
  // count just widen the pool a new round can draw from instead. Fewer
  // uploaded images than the chosen difficulty asks for is fine too -
  // newRound() below just uses however many are actually available.
  const PAIRS_BY_DIFFICULTY = { leicht: 4, mittel: 8, schwer: 12 };
  // How long a non-matching pair stays face-up before flipping back, so
  // there's actually time to see what was wrong.
  const MISMATCH_DELAY_MS = 900;

  let flippedCards = [];
  let matchedPairs = 0;
  let totalPairs = 0;
  let moves = 0;
  let boardLocked = false;
  let lastImages = null;
  let lastPairCount = PAIRS_BY_DIFFICULTY.mittel;

  function shuffled(array) {
    const copy = array.slice();
    for (let i = copy.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [copy[i], copy[j]] = [copy[j], copy[i]];
    }
    return copy;
  }

  function buildCard(url, pairId) {
    const card = document.createElement("button");
    card.type = "button";
    card.className = "game-card";
    card.dataset.pairId = String(pairId);
    card.setAttribute("aria-label", "Memory-Karte");
    card.innerHTML =
      '<span class="game-card-inner">' +
      '<span class="game-card-face game-card-back">🦉</span>' +
      `<span class="game-card-face game-card-front"><img src="${url}" alt=""></span>` +
      "</span>";
    card.addEventListener("click", () => handleCardTap(card));
    return card;
  }

  function handleCardTap(card) {
    if (boardLocked) return;
    if (card.classList.contains("flipped") || card.classList.contains("matched")) return;

    card.classList.add("flipped");
    flippedCards.push(card);
    if (flippedCards.length < 2) return;

    moves += 1;
    const [first, second] = flippedCards;
    if (first.dataset.pairId === second.dataset.pairId) {
      first.classList.add("matched");
      second.classList.add("matched");
      flippedCards = [];
      matchedPairs += 1;
      if (matchedPairs === totalPairs) {
        boardLocked = true;
        setTimeout(showWin, 500);
      }
    } else {
      boardLocked = true;
      setTimeout(() => {
        first.classList.remove("flipped");
        second.classList.remove("flipped");
        flippedCards = [];
        boardLocked = false;
      }, MISMATCH_DELAY_MS);
    }
  }

  function showWin() {
    winMovesEl.textContent = `${moves} Zug${moves === 1 ? "" : "e"}`;
    winBannerEl.hidden = false;
  }

  // A roughly square grid for however many cards this round has, rather than
  // a fixed column count that would look sparse/cramped depending on how
  // many images ended up in the pool.
  function layoutGrid(cardCount) {
    const columns = Math.ceil(Math.sqrt(cardCount));
    gridEl.style.gridTemplateColumns = `repeat(${columns}, 1fr)`;
  }

  function newRound(images, pairCount) {
    lastPairCount = pairCount;
    difficultyEl.hidden = true;
    gridEl.hidden = false;
    winBannerEl.hidden = true;
    boardLocked = false;
    flippedCards = [];
    matchedPairs = 0;
    moves = 0;
    gridEl.innerHTML = "";

    // Fewer uploaded images than the chosen difficulty just means a smaller
    // round than requested, not an error - see PAIRS_BY_DIFFICULTY above.
    const pool = shuffled(images).slice(0, pairCount);
    totalPairs = pool.length;
    layoutGrid(totalPairs * 2);

    const cards = shuffled(pool.flatMap((img, i) => [buildCard(img.url, i), buildCard(img.url, i)]));
    cards.forEach((card) => gridEl.appendChild(card));
  }

  function showDifficultyScreen() {
    gridEl.hidden = true;
    winBannerEl.hidden = true;
    difficultyEl.hidden = false;
  }

  difficultyBtns.forEach((btn) => {
    btn.addEventListener("click", () => {
      const pairCount = PAIRS_BY_DIFFICULTY[btn.dataset.difficulty] || PAIRS_BY_DIFFICULTY.mittel;
      if (lastImages) newRound(lastImages, pairCount);
    });
  });

  againBtn.addEventListener("click", () => {
    if (lastImages) newRound(lastImages, lastPairCount);
  });

  changeDifficultyBtn.addEventListener("click", () => {
    showDifficultyScreen();
  });

  async function start() {
    gameModeEl.hidden = false;
    difficultyEl.hidden = true;
    gridEl.hidden = true;
    winBannerEl.hidden = true;
    try {
      const res = await fetch("/api/game/images");
      const images = await res.json();
      lastImages = images;
      if (!Array.isArray(images) || images.length < 2) {
        emptyHintEl.hidden = false;
        return;
      }
      emptyHintEl.hidden = true;
      // Fresh activation - always ask for a difficulty again rather than
      // silently reusing the last one, same "starts clean every time"
      // principle as the round shuffle itself (see player.js).
      showDifficultyScreen();
    } catch (err) {
      emptyHintEl.hidden = false;
    }
  }

  function stop() {
    gameModeEl.hidden = true;
    difficultyEl.hidden = true;
    winBannerEl.hidden = true;
  }

  window.OwlBoxGame = { start, stop };
})();
