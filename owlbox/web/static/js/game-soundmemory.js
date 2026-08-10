// Sound-Memory mini-game (match pairs by ear instead of by sight - tap a
// card, hear its clip, find the other card with the same clip) - one of
// several mini-games under the Spiele-Menü (see game.js, which owns menu/
// switching and calls window.OwlBoxGameSoundMemory.start()/stop() at the
// right moments). Content is short sound clips uploaded under Einstellungen
// -> Spiel (/api/sound/clips), a separate pool from Memory's pictures.
// Reuses the exact same .game-card/.game-grid/.game-difficulty/.game-win-banner
// CSS as the picture Memory game - only the card front is different (a fixed
// icon instead of an <img>, since there's nothing to reveal visually).
(function () {
  const containerEl = document.getElementById("game-soundmemory");
  const difficultyEl = document.getElementById("game-soundmemory-difficulty");
  const difficultyBtns = document.querySelectorAll(".game-soundmemory-difficulty-btn");
  const gridEl = document.getElementById("game-soundmemory-grid");
  const emptyHintEl = document.getElementById("game-soundmemory-empty-hint");
  const winBannerEl = document.getElementById("game-soundmemory-win-banner");
  const winMovesEl = document.getElementById("game-soundmemory-win-moves");
  const againBtn = document.getElementById("game-soundmemory-again-btn");
  const changeDifficultyBtn = document.getElementById("game-soundmemory-change-difficulty-btn");

  const PAIRS_BY_DIFFICULTY = { leicht: 4, mittel: 8, schwer: 12 };
  // How long a card stays "listening" before the board unlocks again - long
  // enough for a short clip to actually finish, same reasoning as Memory's
  // MISMATCH_DELAY_MS but applied to every single tap here (not just
  // mismatches), since overlapping audio would be confusing rather than fun.
  const LISTEN_MS = 1200;

  let flippedCards = [];
  let matchedPairs = 0;
  let totalPairs = 0;
  let moves = 0;
  let boardLocked = false;
  let lastClips = null;
  let lastPairCount = PAIRS_BY_DIFFICULTY.mittel;
  let pendingTimeout = null;

  function shuffled(array) {
    const copy = array.slice();
    for (let i = copy.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [copy[i], copy[j]] = [copy[j], copy[i]];
    }
    return copy;
  }

  function playClip(url) {
    try {
      new Audio(url).play().catch(() => {});
    } catch (err) {
      // Audio unsupported - the fixed LISTEN_MS delay still paces the round.
    }
  }

  function buildCard(clipUrl, pairId) {
    const card = document.createElement("button");
    card.type = "button";
    card.className = "game-card";
    card.dataset.pairId = String(pairId);
    card.dataset.clipUrl = clipUrl;
    card.setAttribute("aria-label", "Sound-Memory-Karte");
    card.innerHTML =
      '<span class="game-card-inner">' +
      '<span class="game-card-face game-card-back">🦉</span>' +
      '<span class="game-card-face game-card-front">🔊</span>' +
      "</span>";
    card.addEventListener("click", () => handleCardTap(card));
    return card;
  }

  function handleCardTap(card) {
    if (boardLocked) return;
    if (card.classList.contains("flipped") || card.classList.contains("matched")) return;

    card.classList.add("flipped");
    playClip(card.dataset.clipUrl);
    flippedCards.push(card);

    if (flippedCards.length < 2) {
      boardLocked = true;
      pendingTimeout = setTimeout(() => {
        boardLocked = false;
      }, LISTEN_MS);
      return;
    }

    moves += 1;
    boardLocked = true;
    const [first, second] = flippedCards;
    pendingTimeout = setTimeout(() => {
      if (first.dataset.pairId === second.dataset.pairId) {
        first.classList.add("matched");
        second.classList.add("matched");
        flippedCards = [];
        matchedPairs += 1;
        boardLocked = false;
        if (matchedPairs === totalPairs) {
          boardLocked = true;
          pendingTimeout = setTimeout(showWin, 300);
        }
      } else {
        first.classList.remove("flipped");
        second.classList.remove("flipped");
        flippedCards = [];
        boardLocked = false;
      }
    }, LISTEN_MS);
  }

  function showWin() {
    winMovesEl.textContent = `${moves} Zug${moves === 1 ? "" : "e"}`;
    winBannerEl.hidden = false;
  }

  function layoutGrid(cardCount) {
    const columns = Math.ceil(Math.sqrt(cardCount));
    gridEl.style.gridTemplateColumns = `repeat(${columns}, 1fr)`;
  }

  function newRound(clips, pairCount) {
    lastPairCount = pairCount;
    difficultyEl.hidden = true;
    gridEl.hidden = false;
    winBannerEl.hidden = true;
    boardLocked = false;
    flippedCards = [];
    matchedPairs = 0;
    moves = 0;
    gridEl.innerHTML = "";

    const pool = shuffled(clips).slice(0, pairCount);
    totalPairs = pool.length;
    layoutGrid(totalPairs * 2);

    const cards = shuffled(pool.flatMap((clip, i) => [buildCard(clip.url, i), buildCard(clip.url, i)]));
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
      if (lastClips) newRound(lastClips, pairCount);
    });
  });

  againBtn.addEventListener("click", () => {
    if (lastClips) newRound(lastClips, lastPairCount);
  });

  changeDifficultyBtn.addEventListener("click", showDifficultyScreen);

  async function start() {
    containerEl.hidden = false;
    difficultyEl.hidden = true;
    gridEl.hidden = true;
    winBannerEl.hidden = true;
    try {
      const res = await fetch("/api/sound/clips");
      const clips = await res.json();
      lastClips = clips;
      if (!Array.isArray(clips) || clips.length < 2) {
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
    if (pendingTimeout) {
      clearTimeout(pendingTimeout);
      pendingTimeout = null;
    }
    containerEl.hidden = true;
    difficultyEl.hidden = true;
    winBannerEl.hidden = true;
  }

  window.OwlBoxGameSoundMemory = { start, stop };
})();
