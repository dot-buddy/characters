// Dumpling (Dot Buddy's main character) strolling along the bottom of the page.
// Frames are the app's own drawing (DotBuddy --export-pack <dir> mandu): mandu-<motion>.png next to this file, 20×16 dots a frame.
// Click it and it says hi. With "reduce motion" on it just stands there.
(() => {
  if (window.__dotBuddyWalker) return; window.__dotBuddyWalker = true;
  const base = document.currentScript.src.replace(/[^/]*$/, '');
  const ko = (document.documentElement.lang || '').startsWith('ko');
  const still = matchMedia('(prefers-reduced-motion: reduce)').matches;
  const FPS = { walk: 6, idle: 2, blink: 1, wave: 5, happy: 1, cheer: 4, sit: 1, sleep: 1.5 };
  const LINES = ko ? ['안녕!', '나는 만두야', '에이전트 일이 끝나면 알려 줄게', '맥에 데려가 줘!', '간지러워~']
                   : ['Hi!', "I'm Dumpling", "I'll tell you when your agent is done", 'Take me to your Mac!', 'That tickles~'];
  const FW = 20, FH = 16, img = {};
  for (const m in FPS) { img[m] = new Image(); img[m].src = base + 'mandu-' + m + '.png'; }

  const css = document.createElement('style');
  css.textContent = `
.db-walker { position: fixed; left: 0; bottom: env(safe-area-inset-bottom, 0); z-index: 50; cursor: pointer; -webkit-tap-highlight-color: transparent; }
.db-walker-sprite { image-rendering: pixelated; background-repeat: no-repeat; }
.db-walker-bubble { position: absolute; bottom: 100%; left: 50%; transform: translateX(-50%); margin-bottom: 4px; padding: 3px 8px; white-space: nowrap;
  font: 600 13px/1.4 system-ui, sans-serif; color: #3a2a24; background: #fffaf0; border: 2px solid #5a4334; border-radius: 6px; opacity: 0; transition: opacity .2s; pointer-events: none; }
.db-walker-bubble.on { opacity: 1; }
body { padding-bottom: 72px; }                                     /* room so it never sits on the footer text */
@media print { .db-walker { display: none; } }`;
  document.head.append(css);
  const el = document.createElement('div'), spr = document.createElement('div'), bub = document.createElement('div');
  el.className = 'db-walker'; spr.className = 'db-walker-sprite'; bub.className = 'db-walker-bubble';
  el.setAttribute('role', 'img'); el.setAttribute('aria-label', ko ? '화면 아래를 걸어 다니는 만두' : 'Dumpling walking along the bottom of the page');
  el.append(bub, spr);

  const scale = () => (innerWidth < 600 ? 3 : 4);
  let x = 24, dir = 1, motion = 'idle', t0 = 0, until = 0, target = 0, hop = 0, bubbleUntil = 0;
  const now = () => performance.now() / 1000;
  const maxX = () => Math.max(8, innerWidth - FW * scale() - 8);
  function act(m, secs) { motion = m; t0 = now(); until = t0 + secs; }
  function decide() {
    if (still) return act(Math.random() < 0.15 ? 'blink' : 'idle', 0.4 + Math.random() * 3);
    const r = Math.random();
    if (r < 0.5) { target = 8 + Math.random() * (maxX() - 8); dir = target > x ? 1 : -1; act('walk', 30); }
    else if (r < 0.75) act('idle', 1.5 + Math.random() * 3);
    else if (r < 0.85) act('wave', 2);
    else if (r < 0.93) act('sit', 3 + Math.random() * 3);
    else act('sleep', 6 + Math.random() * 5);
  }
  el.addEventListener('click', () => {
    act('cheer', 1.6); hop = now();
    bub.textContent = LINES[Math.floor(Math.random() * LINES.length)]; bub.classList.add('on'); bubbleUntil = now() + 2.4;
  });

  let last = now();
  function tick() {
    const t = now(), dt = Math.min(0.1, t - last); last = t;
    const s = scale();
    if (motion === 'walk') {
      x += dir * 34 * dt;
      if ((dir > 0 && x >= target) || (dir < 0 && x <= target)) { x = target; decide(); }
    } else if (t > until) {
      if (motion === 'idle' && !still && Math.random() < 0.3) act('blink', 0.25); else decide();
    }
    x = Math.min(Math.max(x, 8), maxX());
    if (bubbleUntil && t > bubbleUntil) { bub.classList.remove('on'); bubbleUntil = 0; }
    const im = img[motion], n = Math.max(1, Math.round((im.naturalWidth || FW) / FW)), f = Math.floor((t - t0) * FPS[motion]) % n;
    spr.style.width = FW * s + 'px'; spr.style.height = FH * s + 'px';
    spr.style.backgroundImage = `url("${im.src}")`;
    spr.style.backgroundSize = `${n * FW * s}px ${FH * s}px`;
    spr.style.backgroundPosition = `${-f * FW * s}px 0`;
    spr.style.transform = dir < 0 ? 'scaleX(-1)' : '';
    const bob = motion === 'walk' && f % 2 ? s : 0;                                 // the dumpling has no feet to swap, so it bobs a dot each step
    const up = (hop && t - hop < 0.35 ? Math.sin((t - hop) / 0.35 * Math.PI) * 3 * s : 0) + bob;
    el.style.transform = `translate(${Math.round(x)}px, ${-Math.round(up)}px)`;
    requestAnimationFrame(tick);
  }
  function start() { document.body.append(el); decide(); requestAnimationFrame(tick); }
  if (document.body) start(); else addEventListener('DOMContentLoaded', start);
})();
