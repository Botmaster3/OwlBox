// Spiele-Menü orchestrator, shown while game mode is active (see player.js,
// which owns the top-level view switching and calls window.OwlBoxGame.start()/
// stop() at the right moments). This is the one screen in the whole kiosk
// where touch input actually does anything - everywhere else is look-only,
// see docs/hardware.md.
//
// This file only owns the menu screen and switching between mini-games; each
// mini-game's own screen/logic lives in its own game-<name>.js, loaded before
// this file (see player.html), each exposing window.OwlBoxGame<Name> =
// {start, stop} the same way this file exposes window.OwlBoxGame to player.js.
(function () {
  const gameModeEl = document.getElementById("game-mode");
  const menuEl = document.getElementById("game-menu");
  const backBtn = document.getElementById("game-back-btn");
  const tiles = document.querySelectorAll(".game-menu-tile");

  // Looked up lazily (not cached at load time) - by the time a tile is
  // actually tapped, every game-*.js has long since finished loading and set
  // its window.OwlBoxGameXxx regardless of <script> order among themselves.
  function moduleFor(id) {
    return {
      memory: window.OwlBoxGameMemory,
      simon: window.OwlBoxGameSimon,
      puzzle: window.OwlBoxGamePuzzle,
      reaction: window.OwlBoxGameReaction,
      quiz: window.OwlBoxGameQuiz,
      soundmemory: window.OwlBoxGameSoundMemory,
    }[id];
  }

  let activeGame = null; // the currently open mini-game's {start, stop} module, or null on the menu

  function showMenu() {
    if (activeGame) {
      activeGame.stop();
      activeGame = null;
    }
    menuEl.hidden = false;
    backBtn.hidden = true;
  }

  function showGame(id) {
    const module = moduleFor(id);
    if (!module) return;
    menuEl.hidden = true;
    backBtn.hidden = false;
    activeGame = module;
    module.start();
  }

  tiles.forEach((tile) => {
    tile.addEventListener("click", () => showGame(tile.dataset.game));
  });

  backBtn.addEventListener("click", showMenu);

  function start() {
    gameModeEl.hidden = false;
    // Fresh activation - always land back on the menu rather than resuming
    // whichever mini-game was open last time, same "starts clean every
    // time" principle the mini-games themselves use for their own rounds.
    showMenu();
  }

  function stop() {
    if (activeGame) {
      activeGame.stop();
      activeGame = null;
    }
    gameModeEl.hidden = true;
  }

  window.OwlBoxGame = { start, stop };
})();
