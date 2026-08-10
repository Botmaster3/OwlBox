// Memory game shown on the kiosk display while game mode is active (see
// player.js, which owns view switching and calls window.OwlBoxGame.start()/
// stop() at the right moments). This is the one screen in the whole kiosk
// where touch input actually does anything - everywhere else is look-only,
// see docs/hardware.md.
(function () {
  const gameModeEl = document.getElementById("game-mode");
  const gridEl = document.getElementById("game-grid");
  const emptyHintEl = document.getElementById("game-empty-hint");
  const winBannerEl = document.getElementById("game-win-banner");
  const winMovesEl = document.getElementById("game-win-moves");
  const againBtn = document.getElementById("game-again-btn");

  // Cards auto-size to fit however many pairs a round has (see layoutGrid()
  // below) - this just caps how many pairs one round pulls out of the pool,
  // so the board doesn't become impossible to scan on a 5" display. Extra
  // uploaded images beyond this just widen the pool a new round can draw
  // from instead.
  const MAX_PAIRS = 12;
  // How long a non-matching pair stays face-up before flipping back, so
  // there's actually time to see what was wrong.
  const MISMATCH_DELAY_MS = 900;

  let flippedCards = [];
  let matchedPairs = 0;
  let totalPairs = 0;
  let moves = 0;
  let boardLocked = false;
  let lastImages = null;

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

  function newRound(images) {
    winBannerEl.hidden = true;
    boardLocked = false;
    flippedCards = [];
    matchedPairs = 0;
    moves = 0;
    gridEl.innerHTML = "";

    const pool = shuffled(images).slice(0, MAX_PAIRS);
    totalPairs = pool.length;
    layoutGrid(totalPairs * 2);

    const cards = shuffled(pool.flatMap((img, i) => [buildCard(img.url, i), buildCard(img.url, i)]));
    cards.forEach((card) => gridEl.appendChild(card));
  }

  againBtn.addEventListener("click", () => {
    if (lastImages) newRound(lastImages);
  });

  async function start() {
    gameModeEl.hidden = false;
    winBannerEl.hidden = true;
    try {
      const res = await fetch("/api/game/images");
      const images = await res.json();
      lastImages = images;
      if (!Array.isArray(images) || images.length < 2) {
        gridEl.hidden = true;
        emptyHintEl.hidden = false;
        return;
      }
      gridEl.hidden = false;
      emptyHintEl.hidden = true;
      newRound(images);
    } catch (err) {
      gridEl.hidden = true;
      emptyHintEl.hidden = false;
    }
  }

  function stop() {
    gameModeEl.hidden = true;
  }

  window.OwlBoxGame = { start, stop };
})();
