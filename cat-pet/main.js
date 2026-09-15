// Кот поверх рабочего стола: прозрачное окно на весь экран, клики проходят сквозь него
// везде, кроме самого кота. Курсор читаем глобально, чтобы кот видел его над любыми окнами.
// Внешность, характер и пол — в cat.json в папке приложения; правки подхватываются на лету.
const { app, BrowserWindow, screen, ipcMain, Tray, Menu, nativeImage, shell, dialog } = require("electron");
const path = require("path");
const fs = require("fs");

let win = null, tray = null, cursorTimer = null, overCat = false, visible = true, catName = "Кот";
const USER_DIR = app.getPath("userData");
const SPEC_PATH = path.join(USER_DIR, "cat.json");
const PAGE_PATH = path.join(USER_DIR, "pet.html");
const DEFAULT_SPEC = path.join(__dirname, "cats", "shinshilla.json");
const TABLES = JSON.parse(fs.readFileSync(path.join(__dirname, "breeds.json"), "utf-8"));

/* ---------- cat.json → страница ---------- */
function applyPresets(spec) {
  // то же, что делает build_pet.py в скилле: порода и готовый окрас заполняют
  // только те поля, которые в appearance не заданы явно
  const app_ = Object.assign({}, spec.appearance || {});
  if (spec.breed) {
    let key = String(spec.breed).trim().toLowerCase().replace(/_/g, " ");
    key = TABLES.aliases[key] || key.replace(/ /g, "_");
    const preset = TABLES.breeds[key];
    if (preset) for (const [k, v] of Object.entries(preset)) if (app_[k] == null) app_[k] = v;
  }
  const pat = String(app_.pattern || "").trim().toLowerCase();
  const pkey = TABLES.pattern_aliases[pat] || pat;
  const pp = TABLES.patterns[pkey];
  if (pp) {
    app_.pattern = pp.pattern;
    const ex = (app_.extras || []).map(s => String(s).toLowerCase());
    for (const e of pp.extras || []) if (!ex.includes(e)) ex.push(e);
    app_.extras = ex;
    for (const k of ["pattern_color", "belly_color"]) if (pp[k] && !app_[k]) app_[k] = pp[k];
  }
  if ((app_.extras || []).includes("heterochromia") && !app_.eye_color2) app_.eye_color2 = "#8fc7e8";
  if ((app_.extras || []).includes("collar") && !app_.collar_color) app_.collar_color = "#c0392b";
  return Object.assign({}, spec, { appearance: app_ });
}

function loadSpec() {
  if (!fs.existsSync(SPEC_PATH)) {
    fs.mkdirSync(USER_DIR, { recursive: true });
    fs.copyFileSync(DEFAULT_SPEC, SPEC_PATH);
  }
  let spec;
  try {
    spec = JSON.parse(fs.readFileSync(SPEC_PATH, "utf-8"));
    if (!spec || typeof spec !== "object") throw new Error("cat.json должен быть объектом {...}");
    if (!spec.appearance || !spec.appearance.base_color) throw new Error("нет appearance.base_color");
  } catch (e) {
    dialog.showErrorBox("cat.json не читается", e.message + "\n\nФайл: " + SPEC_PATH +
      "\nПока используется прошлое описание кота.");
    return null;
  }
  return applyPresets(spec);
}

function buildPage(spec) {
  const tpl = fs.readFileSync(path.join(__dirname, "pet.template.html"), "utf-8");
  const payload = JSON.stringify(spec, null, 2).replace(/<\//g, "<\\/");
  const html = tpl.replace("__CAT_SPEC__", payload).split("__CAT_NAME__").join(spec.name || "Кот");
  fs.writeFileSync(PAGE_PATH, html);
  catName = spec.name || "Кот";
}

function reloadCat() {
  const spec = loadSpec();
  if (!spec) return false;
  buildPage(spec);
  if (win && !win.isDestroyed()) win.loadFile(PAGE_PATH);
  if (tray) { tray.setTitle(" " + catName); tray.setContextMenu(buildMenu()); }
  return true;
}

/* ---------- значок в строке меню ---------- */
function trayIcon() {
  // след лапы с наклоном; файл *Template.png — macOS сам перекрашивает его под светлую и тёмную строку меню
  const img = nativeImage.createFromPath(path.join(__dirname, "tray", "trayTemplate.png"));
  img.setTemplateImage(true);
  return img;
}

/* ---------- окно ---------- */
function createWindow() {
  const a = screen.getPrimaryDisplay().workArea;   // без меню-бара и Dock
  win = new BrowserWindow({
    x: a.x, y: a.y, width: a.width, height: a.height,
    transparent: true, frame: false, hasShadow: false, resizable: false, movable: false,
    alwaysOnTop: true, skipTaskbar: true, focusable: false, backgroundColor: "#00000000",
    webPreferences: { preload: path.join(__dirname, "preload.js"), contextIsolation: true }
  });
  win.setAlwaysOnTop(true, "floating");
  win.setVisibleOnAllWorkspaces(true, { visibleOnFullScreen: true });
  win.setIgnoreMouseEvents(true, { forward: true });
  win.loadFile(PAGE_PATH);

  cursorTimer = setInterval(() => {
    if (!win || win.isDestroyed()) return;
    const p = screen.getCursorScreenPoint(), b = win.getBounds();
    const x = p.x - b.x, y = p.y - b.y;
    win.webContents.send("cursor", { x, y, inside: x >= 0 && y >= 0 && x < b.width && y < b.height });
  }, 16);
}

function send(ch, v) { if (win && !win.isDestroyed()) win.webContents.send(ch, v); }

ipcMain.on("over-cat", (_e, v) => {
  if (!win || v === overCat) return;
  overCat = v;
  win.setIgnoreMouseEvents(!v, { forward: true });   // над котом окно ловит мышь, иначе пропускает
});
ipcMain.on("state", (_e, text) => { if (tray) tray.setToolTip(text); });
ipcMain.on("menu", () => buildMenu().popup({ window: win }));

async function pickSpecFile() {
  // приложение без Dock и с нефокусируемым окном: без явного фокуса диалог уходит под другие окна
  if (app.dock) await app.dock.show();
  app.focus({ steal: true });
  try {
    const r = await dialog.showOpenDialog({
      title: "Выбрать cat.json", defaultPath: path.join(__dirname, "cats"),
      properties: ["openFile"], filters: [{ name: "cat.json", extensions: ["json"] }]
    });
    if (r.canceled || !r.filePaths[0]) return;
    try { JSON.parse(fs.readFileSync(r.filePaths[0], "utf-8")); }
    catch (e) { dialog.showErrorBox("Это не cat.json", e.message); return; }
    fs.copyFileSync(r.filePaths[0], SPEC_PATH);
    reloadCat();
  } finally {
    if (app.dock) app.dock.hide();
  }
}

function buildMenu() {
  const act = (label, state) => ({ label, click: () => send("enter", state) });
  return Menu.buildFromTemplate([
    { label: catName, enabled: false },
    act("Погладить", "petted"),
    act("Пройтись", "walk"),
    act("Буханка", "loaf"),
    act("Спать", "sleep"),
    act("Умываться", "groom"),
    act("Потянуться", "stretch"),
    act("К курсору", "chase_cursor"),
    act("Испугать", "startle"),
    act("Берсерк", "berserk"),
    { type: "separator" },
    { label: "Поставить / убрать корм", click: () => send("bowl", "food") },
    { label: "Поставить / убрать воду", click: () => send("bowl", "water") },
    { label: "Дать / убрать мышку", click: () => send("toy", null) },
    { type: "separator" },
    { label: "Изменить кота (cat.json)…", click: () => shell.openPath(SPEC_PATH) },
    { label: "Выбрать другой cat.json…", click: () => pickSpecFile() },
    { label: "Сменить пол", click: () => send("toggle-sex", null) },
    { label: "Перезагрузить кота", click: () => reloadCat() },
    { type: "separator" },
    { label: visible ? "Спрятать кота" : "Показать кота", click: () => {
        visible = !visible; visible ? win.show() : win.hide(); tray.setContextMenu(buildMenu()); } },
    { label: "Выход", click: () => app.quit() }
  ]);
}

app.whenReady().then(() => {
  if (app.dock) app.dock.hide();
  const spec = loadSpec() || JSON.parse(fs.readFileSync(DEFAULT_SPEC, "utf-8"));
  buildPage(applyPresets(spec));
  createWindow();
  tray = new Tray(trayIcon());
  tray.setTitle(" " + catName);
  tray.setToolTip("Правый клик по коту или этот значок — меню");
  tray.setContextMenu(buildMenu());
  // правки cat.json в редакторе подхватываются сами
  fs.watchFile(SPEC_PATH, { interval: 1000 }, () => reloadCat());
  screen.on("display-metrics-changed", () => {
    const a = screen.getPrimaryDisplay().workArea;
    win.setBounds({ x: a.x, y: a.y, width: a.width, height: a.height });
    send("resize", null);
  });
});
app.on("window-all-closed", () => app.quit());
app.on("before-quit", () => { clearInterval(cursorTimer); fs.unwatchFile(SPEC_PATH); });
