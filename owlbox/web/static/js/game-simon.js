// Simon-Sagt mini-game (repeat the growing color/sound sequence) - one of
// several mini-games under the Spiele-Menü (see game.js, which owns menu/
// switching and calls window.OwlBoxGameSimon.start()/stop() at the right
// moments). No uploaded content needed - fully self-contained.
(function () {
  const containerEl = document.getElementById("game-simon");
  const levelEl = document.getElementById("game-simon-level");
  const pads = document.querySelectorAll(".game-simon-pad");
  const startBtn = document.getElementById("game-simon-start-btn");
  const gameoverEl = document.getElementById("game-simon-gameover");
  const finalLevelEl = document.getElementById("game-simon-final-level");
  const againBtn = document.getElementById("game-simon-again-btn");

  // One tone per pad (roughly a C major arpeggio) - just needs to be
  // distinct per pad, not musically meaningful.
  const PAD_FREQUENCIES = [329.63, 261.63, 220.0, 164.81];
  const FLASH_MS = 400;
  const GAP_MS = 250;

  let sequence = [];
  let level = 0; // rounds completed so far
  let playerIndex = 0;
  let accepting = false;
  let pendingTimeouts = [];
  let audioCtx = null;

  function schedule(fn, delay) {
    const id = setTimeout(fn, delay);
    pendingTimeouts.push(id);
    return id;
  }

  function clearAllTimeouts() {
    pendingTimeouts.forEach((id) => clearTimeout(id));
    pendingTimeouts = [];
  }

  // Created lazily on the first actual play - browsers require a user
  // gesture before audio can start, and "Los geht's"/"Nochmal spielen" are
  // exactly that gesture. A missing/blocked AudioContext just means silent
  // pads - the visual flash still carries the game.
  function beep(padIndex) {
    try {
      if (!audioCtx) audioCtx = new (window.AudioContext || window.webkitAudioContext)();
      const osc = audioCtx.createOscillator();
      const gain = audioCtx.createGain();
      osc.type = "sine";
      osc.frequency.value = PAD_FREQUENCIES[padIndex];
      gain.gain.setValueAtTime(0.2, audioCtx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + FLASH_MS / 1000);
      osc.connect(gain).connect(audioCtx.destination);
      osc.start();
      osc.stop(audioCtx.currentTime + FLASH_MS / 1000);
    } catch (err) {
      // Web Audio unavailable/blocked - the flash animation alone is enough
      // to still play the game.
    }
  }

  function flashPad(padIndex) {
    const pad = pads[padIndex];
    pad.classList.add("flash");
    beep(padIndex);
    schedule(() => pad.classList.remove("flash"), FLASH_MS);
  }

  function playSequence() {
    accepting = false;
    sequence.forEach((padIndex, i) => {
      schedule(() => flashPad(padIndex), i * (FLASH_MS + GAP_MS));
    });
    schedule(() => {
      playerIndex = 0;
      accepting = true;
    }, sequence.length * (FLASH_MS + GAP_MS));
  }

  function nextRound() {
    sequence.push(Math.floor(Math.random() * 4));
    levelEl.textContent = String(sequence.length);
    playSequence();
  }

  function handlePadTap(padIndex) {
    if (!accepting) return;
    flashPad(padIndex);
    if (padIndex !== sequence[playerIndex]) {
      accepting = false;
      showGameOver();
      return;
    }
    playerIndex += 1;
    if (playerIndex === sequence.length) {
      level = sequence.length;
      accepting = false;
      schedule(nextRound, FLASH_MS + 500);
    }
  }

  pads.forEach((pad) => {
    pad.addEventListener("click", () => handlePadTap(Number(pad.dataset.pad)));
  });

  function showGameOver() {
    finalLevelEl.textContent = String(level);
    gameoverEl.hidden = false;
  }

  function beginGame() {
    gameoverEl.hidden = true;
    startBtn.hidden = true;
    sequence = [];
    level = 0;
    playerIndex = 0;
    levelEl.textContent = "1";
    schedule(nextRound, 400);
  }

  startBtn.addEventListener("click", beginGame);
  againBtn.addEventListener("click", beginGame);

  function start() {
    containerEl.hidden = false;
    gameoverEl.hidden = true;
    startBtn.hidden = false;
    accepting = false;
    sequence = [];
    level = 0;
    levelEl.textContent = "1";
  }

  function stop() {
    clearAllTimeouts();
    accepting = false;
    containerEl.hidden = true;
  }

  window.OwlBoxGameSimon = { start, stop };
})();
