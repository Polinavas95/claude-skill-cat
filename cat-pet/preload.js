const { contextBridge, ipcRenderer } = require("electron");
contextBridge.exposeInMainWorld("pet", {
  onCursor: cb => ipcRenderer.on("cursor", (_e, p) => cb(p)),
  onEnter: cb => ipcRenderer.on("enter", (_e, s) => cb(s)),
  onBowl: cb => ipcRenderer.on("bowl", (_e, k) => cb(k)),
  onToy: cb => ipcRenderer.on("toy", () => cb()),
  onResize: cb => ipcRenderer.on("resize", () => cb()),
  onToggleSex: cb => ipcRenderer.on("toggle-sex", () => cb()),
  setOverCat: v => ipcRenderer.send("over-cat", v),
  setState: t => ipcRenderer.send("state", t),
  menu: () => ipcRenderer.send("menu")
});
