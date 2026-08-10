// Schiebe-Puzzle mini-game (reassemble one sliced-up picture by tapping two
// tiles to swap them) - one of several mini-games under the Spiele-Menü (see
// game.js, which owns menu/switching and calls window.OwlBoxGamePuzzle.start()/
// stop() at the right moments). Reuses the same picture pool as Memory
// (/api/game/images, uploaded under Einstellungen -> Spiel) rather than
// asking for a second, separate set of images.
(function () {
  const containerEl = document.getElementById("game-puzzle");
  const difficultyEl = document.getElementById("game-puzzle-difficulty");
  const difficultyBtns = document.querySelectorAll(".game-puzzle-difficulty-btn");
  const boardWrapEl = document.getElementById("game-puzzle-board-wrap");
  const referenceEl = document.getElementById("game-puzzle-reference");
  const gridEl = document.getElementById("game-puzzle-grid");
  const emptyHintEl = document.getElementById("game-puzzle-empty-hint");
  const winBannerEl = document.getElementById("game-puzzle-win-banner");
  const winMovesEl = document.getElementById("game-puzzle-win-moves");
  const againBtn = document.getElementById("game-puzzle-again-btn");
  const changeDifficultyBtn = document.getElementById("game-puzzle-change-difficulty-btn");

  // Tap-to-swap-any-two-tiles (not a classic single-blank sliding puzzle),
  // so every shuffled arrangement is solvable - no parity check needed, a
  // player can always fix any two tiles with one swap.
  const GRID_SIZE_BY_DIFFICULTY = { leicht: 3, mittel: 4, schwer: 5 };

  let lastImages = null;
  let lastGridSize = GRID_SIZE_BY_DIFFICULTY.mittel;
  let tiles = []; // DOM elements, index = fixed slot position in the grid
  let selectedTile = null;
  let moves = 0;

  function shuffled(array) {
    const copy = array.slice();
    for (let i = copy.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [copy[i], copy[j]] = [copy[j], copy[i]];
    }
    return copy;
  }

  function styleTileForHome(tile, home, gridSize, imageUrl) {
    const row = Math.floor(home / gridSize);
    const col = home % gridSize;
    tile.dataset.home = String(home);
    tile.style.backgroundImage = `url(${imageUrl})`;
    tile.style.backgroundSize = `${gridSize * 100}% ${gridSize * 100}%`;
    const posX = gridSize === 1 ? 0 : (col / (gridSize - 1)) * 100;
    const posY = gridSize === 1 ? 0 : (row / (gridSize - 1)) * 100;
    tile.style.backgroundPosition = `${posX}% ${posY}%`;
  }

  function checkWin() {
    return tiles.every((tile, slot) => Number(tile.dataset.home) === slot);
  }

  function showWin() {
    winMovesEl.textContent = `${moves} Zug${moves === 1 ? "" : "e"}`;
    winBannerEl.hidden = false;
  }

  function handleTileTap(tile) {
    if (!winBannerEl.hidden) return;
    if (selectedTile === tile) {
      tile.classList.remove("selected");
      selectedTile = null;
      return;
    }
    if (!selectedTile) {
      selectedTile = tile;
      tile.classList.add("selected");
      return;
    }
    // Swap the two tiles' pictured piece (their "home") - the DOM elements
    // and grid slots themselves never move, only which piece each shows.
    const a = selectedTile;
    const b = tile;
    const gridSize = lastGridSize;
    const imageUrl = a.dataset.imageUrl;
    const homeA = a.dataset.home;
    const homeB = b.dataset.home;
    styleTileForHome(a, Number(homeB), gridSize, imageUrl);
    styleTileForHome(b, Number(homeA), gridSize, imageUrl);
    a.classList.remove("selected");
    selectedTile = null;
    moves += 1;

    if (checkWin()) showWin();
  }

  function buildBoard(imageUrl, gridSize) {
    lastGridSize = gridSize;
    difficultyEl.hidden = true;
    winBannerEl.hidden = true;
    boardWrapEl.hidden = false;
    selectedTile = null;
    moves = 0;
    gridEl.innerHTML = "";
    tiles = [];

    referenceEl.src = imageUrl;
    gridEl.style.gridTemplateColumns = `repeat(${gridSize}, 1fr)`;

    const cellCount = gridSize * gridSize;
    let homes = shuffled(Array.from({ length: cellCount }, (_, i) => i));
    // A fully-solved starting board would be no puzzle at all - vanishingly
    // rare with a real shuffle, but reshuffle just in case.
    while (homes.every((home, slot) => home === slot)) {
      homes = shuffled(homes);
    }

    for (let slot = 0; slot < cellCount; slot++) {
      const tile = document.createElement("button");
      tile.type = "button";
      tile.className = "game-puzzle-tile";
      tile.dataset.imageUrl = imageUrl;
      tile.setAttribute("aria-label", "Puzzle-Teil");
      styleTileForHome(tile, homes[slot], gridSize, imageUrl);
      tile.addEventListener("click", () => handleTileTap(tile));
      gridEl.appendChild(tile);
      tiles.push(tile);
    }
  }

  function showDifficultyScreen() {
    boardWrapEl.hidden = true;
    winBannerEl.hidden = true;
    difficultyEl.hidden = false;
  }

  function newRoundWithRandomImage(gridSize) {
    if (!lastImages || lastImages.length === 0) return;
    const image = lastImages[Math.floor(Math.random() * lastImages.length)];
    buildBoard(image.url, gridSize);
  }

  difficultyBtns.forEach((btn) => {
    btn.addEventListener("click", () => {
      const gridSize = GRID_SIZE_BY_DIFFICULTY[btn.dataset.difficulty] || GRID_SIZE_BY_DIFFICULTY.mittel;
      newRoundWithRandomImage(gridSize);
    });
  });

  againBtn.addEventListener("click", () => newRoundWithRandomImage(lastGridSize));
  changeDifficultyBtn.addEventListener("click", showDifficultyScreen);

  async function start() {
    containerEl.hidden = false;
    difficultyEl.hidden = true;
    boardWrapEl.hidden = true;
    winBannerEl.hidden = true;
    try {
      const res = await fetch("/api/game/images");
      const images = await res.json();
      lastImages = images;
      if (!Array.isArray(images) || images.length < 1) {
        emptyHintEl.hidden = false;
        return;
      }
      emptyHintEl.hidden = true;
      showDifficultyScreen();
    } catch (err) {
      emptyHintEl.hidden = false;
    }
  }

  function stop() {
    containerEl.hidden = true;
    difficultyEl.hidden = true;
    winBannerEl.hidden = true;
    selectedTile = null;
  }

  window.OwlBoxGamePuzzle = { start, stop };
})();
