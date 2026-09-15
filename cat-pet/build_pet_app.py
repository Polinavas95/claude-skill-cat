#!/usr/bin/env python3
"""Собирает pet.template.html для Electron-питомца: берёт движок cat-skill и переключает его
с нарисованного рабочего стола на прозрачное окно поверх экрана. Конкретного кота (cat.json)
приложение подставляет само при запуске.
    python3 build_pet_app.py
"""
import json, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
# движок берём из соседней папки cat-skill или из плагина в репозитории
SKILL_DIR = next(d for d in (HERE / "cat-skill", HERE.parent / "plugins" / "cat-skill" / "skills" / "cat-skill") if d.exists())
sys.path.insert(0, str(SKILL_DIR / "scripts"))
import build_pet  # noqa: E402

html = build_pet.TEMPLATE.read_text(encoding="utf-8")
# породы и готовые окрасы отдаём приложению: оно применяет их к cat.json само, при запуске
Path("breeds.json").write_text(json.dumps({
    "breeds": build_pet.BREEDS, "aliases": build_pet.BREED_ALIASES,
    "patterns": build_pet.PATTERN_PRESETS, "pattern_aliases": build_pet.PATTERN_ALIASES,
}, ensure_ascii=False, indent=1), encoding="utf-8")

def rep(old, new, count=1):
    global html
    n = html.count(old)
    assert n == count, f"ожидал {count}, нашёл {n}: {old[:70]!r}"
    html = html.replace(old, new)

# --- прозрачная страница: виден только canvas на весь экран ---
rep("""  :root { color-scheme: light dark; }
""", "")   # с color-scheme Chromium красит фон окна
# переопределения идут ПОСЛЕ исходных правил, иначе проигрывают им по порядку в каскаде
rep("""</style>""", """  html, body { background: transparent !important; overflow: hidden !important; margin: 0 !important; padding: 0 !important; }
  .wrap { max-width: none !important; margin: 0 !important; }
  .wrap > *:not(.stage) { display: none !important; }
  .stage { position: fixed !important; inset: 0 !important; border-radius: 0 !important;
    box-shadow: none !important; background: transparent !important; overflow: visible !important; }
  canvas { width: 100vw !important; height: 100vh !important; display: block; }
</style>""")
rep("""  @media (prefers-color-scheme: dark) {
    body { background: #1a1a1c; color: #eceae4; }""", """  @media (prefers-color-scheme: dark) {
    body { color: #eceae4; }""")

# --- размер сцены = окно, чёткость на Retina через setTransform ---
rep("""const cv = document.getElementById("stage"), ctx = cv.getContext("2d");
const W = cv.width, H = cv.height, FLOOR = H - 70;""",
"""const cv = document.getElementById("stage"), ctx = cv.getContext("2d");
const DPR = window.devicePixelRatio || 1;
cv.width = Math.round(innerWidth * DPR); cv.height = Math.round(innerHeight * DPR);
const W = innerWidth, H = innerHeight, FLOOR = H - 6;   // окно уже без Dock — пол у самого низа""")
# на настоящем экране кот из скилла великоват: уменьшаем в 2.5 раза (scale в cat.json остаётся множителем)
rep("""  scale: clamp(SPEC.scale||1, .5, 2) * 2.6,""", """  scale: clamp(SPEC.scale||1, .5, 2) * 2.6 / 2.5,""")
# меньший кот — шаг короче, иначе он несётся по экрану как заводной
rep("""const speed = () => (1.15 + P.energy*2.5) * CAT.speed * 1.5 * (cat.speedMul || 1);""",
    """const speed = () => (1.15 + P.energy*2.5) * CAT.speed * 1.5 * (cat.speedMul || 1) / 1.6;""")
# пузырь речи и его отступы тоже под размер кота
rep("""    ctx.font = "600 30px -apple-system, Segoe UI, sans-serif"; ctx.textAlign = "center";
    const w = ctx.measureText(cat.bubble).width + 34;""", """    ctx.font = "600 14px -apple-system, Segoe UI, sans-serif"; ctx.textAlign = "center";
    const w = ctx.measureText(cat.bubble).width + 18;""")
rep("""    roundRect(bx-w/2, by-26, w, 46, 14); ctx.fill(); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(bx-12, by+18); ctx.lineTo(bx-6, by+34); ctx.lineTo(bx+4, by+18);
    ctx.closePath(); ctx.fillStyle = "#fdfcf8"; ctx.fill();
    ctx.fillStyle = "#26242a"; ctx.fillText(cat.bubble, bx, by+6);""",
"""    roundRect(bx-w/2, by-12, w, 22, 8); ctx.fill(); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(bx-6, by+9); ctx.lineTo(bx-3, by+16); ctx.lineTo(bx+2, by+9);
    ctx.closePath(); ctx.fillStyle = "#fdfcf8"; ctx.fill();
    ctx.fillStyle = "#26242a"; ctx.fillText(cat.bubble, bx, by+4);""")

# --- курсор приходит из главного процесса (глобальный), а не из событий canvas ---
rep("""cv.addEventListener("mousemove", e => {
  const r = cv.getBoundingClientRect();
  const nx = (e.clientX-r.left)*(W/r.width), ny = (e.clientY-r.top)*(H/r.height);
  if (mousePrev) mouseSpeed = mouseSpeed*.6 + Math.hypot(nx-mousePrev.x, ny-mousePrev.y)*.4;
  mousePrev = {x:nx,y:ny}; mouse = {x:nx,y:ny,inside:true};
});
cv.addEventListener("mouseleave", () => { mouse.inside = false; mouseSpeed = 0; });""",
"""window.pet.onCursor(p => {
  if (!p.inside) { mouse.inside = false; mouseSpeed = 0; mousePrev = null; return; }
  if (mousePrev) mouseSpeed = mouseSpeed*.6 + Math.hypot(p.x-mousePrev.x, p.y-mousePrev.y)*.4;
  mousePrev = {x:p.x, y:p.y}; mouse = {x:p.x, y:p.y, inside:true};
});
window.pet.onEnter(s => enter(s));
cv.addEventListener("contextmenu", e => { e.preventDefault(); window.pet.menu(); });
window.pet.onBowl(k => { if (!bowlOf(k)) spawnBowl(k); });
window.pet.onToy(() => toy ? removeToy() : spawnToy());
window.pet.onResize(() => location.reload());
const catHit = () => mouse.inside &&
  Math.hypot(mouse.x - cat.x, mouse.y - (cat.y - 40*CAT.scale)) < 110*CAT.scale;
let overCatPrev = false;""")

# --- на настоящем экране нет нарисованных иконок и окна: к ним не ходим, прячемся за край ---
rep("""    approach_icon: .05 + P.curiosity*.85,
    berserk: .08 + P.energy*.32""", """    berserk: .08 + P.energy*.32""")
rep("""      cat.hideBehind = Math.random() < .75;""", """      cat.hideBehind = false;""")
# ходим по полу, а не «в глубину» стола
rep("""      cat.target = {x: rnd(120, W-120), y: rnd(FLOOR-H*.26, FLOOR)};""",
    """      cat.target = {x: rnd(120, W-120), y: FLOOR};""")
rep("""          : {x: rnd(60, W-60), y: rnd(FLOOR - H*.3, FLOOR)};""",
    """          : {x: rnd(60, W-60), y: FLOOR - rnd(0, 40)};""")
rep("""      if (cat.offTimer <= 0) cat.dash = {x: rnd(W*.2, W*.8), y: rnd(FLOOR - H*.2, FLOOR)};""",
    """      if (cat.offTimer <= 0) cat.dash = {x: rnd(W*.2, W*.8), y: FLOOR - rnd(0, 40)};""")
rep("""      stepTo({x: mouse.x, y: clamp(mouse.y + 38, 120, FLOOR)}, speed()*1.25);""",
    """      stepTo({x: mouse.x, y: clamp(mouse.y + 38, 120, FLOOR)}, speed()*1.25);
      if (cat.y < FLOOR - 20 && Math.abs(mouse.x - cat.x) < 40 && mouse.y > cat.y) cat.y = FLOOR;""")

# --- кадр: без стола и окна, с передачей «курсор над котом» в главный процесс ---
rep("""  const q = pose();
  ctx.clearRect(0,0,W,H);
  drawDesktop();
  const behind = cat.state === "hidden" && cat.hideBehind;
  if (behind) { drawToy(); drawCat(q); drawWindow(); }
  else { drawWindow(); drawToy(); drawCat(q); }
  drawBowls();
  requestAnimationFrame(frame);""",
"""  const q = pose();
  ctx.setTransform(DPR, 0, 0, DPR, 0, 0);
  ctx.clearRect(0,0,W,H);
  drawToy();
  drawCat(q);
  drawBowls();
  const over = catHit();
  if (over !== overCatPrev) { overCatPrev = over; window.pet.setOverCat(over); }
  requestAnimationFrame(frame);""")
rep("""  document.getElementById("statebar").textContent =
    "сейчас: " + (STATE_RU[cat.state] || cat.state) + (bowls.length ? " · на полу миска" : "") + (toy ? " · на полу мышка" : "");""",
"""  const stText = (STATE_RU[cat.state] || cat.state);
  if (stText !== cat.lastSt) { cat.lastSt = stText; window.pet.setState(CAT.name + ": " + stText); }""")

# миски и позиция у миски — в масштабе кота (в движке они заданы под кота масштаба 2.6)
rep("""    ctx.save(); ctx.globalAlpha = clamp(b.life/3, 0, 1);
    const w = 96, h = 38, rimY = b.y - h;""", """    ctx.save(); ctx.globalAlpha = clamp(b.life/3, 0, 1);
    const BS = CAT.scale / 2.6;
    ctx.translate(b.x, b.y); ctx.scale(BS, BS); ctx.translate(-b.x, -b.y);
    const w = 96, h = 38, rimY = b.y - h;""")
rep("""      cat.target = {x: b.x - 94*(cat.x < b.x ? 1 : -1), y: FLOOR};""",
    """      cat.target = {x: b.x - 36*CAT.scale*(cat.x < b.x ? 1 : -1), y: FLOOR};""")
rep("""cv.addEventListener("contextmenu", e => { e.preventDefault(); window.pet.menu(); });""",
    """cv.addEventListener("contextmenu", e => { e.preventDefault(); window.pet.menu(); });
window.pet.onToggleSex(() => sexBtn.click());""")
Path("pet.template.html").write_text(html, encoding="utf-8")
print("готово: pet.template.html + breeds.json")
