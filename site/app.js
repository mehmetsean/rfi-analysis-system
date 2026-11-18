"use strict";

const WHEEL_NAME = /^[A-Za-z0-9_.+-]+\.whl$/;
const KEY_COLUMNS = ["No.", "Cited text", "Key", "Base key", "Body", "Clause"];

let pyodide = null;
let demo = null;

function setStatus(text) {
  $("status").textContent = text;
}

function pyError(e) {
  const lines = String(e && e.message ? e.message : e).trim().split("\n");
  return lines[lines.length - 1];
}

function renderMarked(text, rows) {
  const box = $("marked");
  box.replaceChildren();
  let pos = 0;
  for (const row of rows) {
    if (row.start < pos) continue;
    if (row.start > pos) box.appendChild(document.createTextNode(text.slice(pos, row.start)));
    const mark = el("mark", undefined, "cite");
    mark.appendChild(document.createTextNode(text.slice(row.start, row.end)));
    mark.appendChild(el("span", row.body, "tag"));
    box.appendChild(mark);
    pos = row.end;
  }
  if (pos < text.length) box.appendChild(document.createTextNode(text.slice(pos)));
}

function renderKeys(rows) {
  const box = $("keys");
  box.replaceChildren();
  if (rows.length === 0) {
    box.appendChild(el("p", "No citations found."));
    return;
  }
  const body = rows.map((r, i) => [i + 1, r.text, r.key, r.base_key, r.body, r.clause]);
  box.appendChild(makeTable("Citation keys", KEY_COLUMNS, body, [0]));
}

function findCitations() {
  const text = $("text").value;
  let rows = [];
  try {
    const proxy = demo.find_citations(text);
    rows = proxy.toJs({ dict_converter: Object.fromEntries });
    proxy.destroy();
  } catch (e) {
    setStatus("Could not read the text: " + pyError(e));
    return;
  }
  renderMarked(text, rows);
  renderKeys(rows);
  $("count").textContent = rows.length + (rows.length === 1 ? " citation" : " citations") + " found in " + text.length + " characters.";
  $("results").hidden = false;
  setStatus("Done.");
}

function loadSample() {
  const seed = Number($("seed").value);
  if (!Number.isInteger(seed) || seed < 0 || seed > 999999) {
    setStatus("Seed must be a whole number from 0 to 999999.");
    return;
  }
  $("text").value = demo.sample_text(seed);
  findCitations();
  setStatus("Loaded the synthetic sample for seed " + seed + ".");
}

function clearAll() {
  $("text").value = "";
  $("results").hidden = true;
  $("marked").replaceChildren();
  $("keys").replaceChildren();
  setStatus("Cleared.");
  $("text").focus();
}

async function installWheels() {
  const response = await fetch("manifest.json");
  if (!response.ok) throw new Error("manifest.json is missing from this site");
  const manifest = await response.json();
  for (const name of manifest.wheels) {
    if (typeof name !== "string" || !WHEEL_NAME.test(name)) throw new Error("bad wheel name in manifest.json");
    const wheel = await fetch("wheels/" + name);
    if (!wheel.ok) throw new Error(name + " is missing from this site");
    pyodide.unpackArchive(await wheel.arrayBuffer(), "wheel");
  }
  pyodide.runPython("import importlib\nimportlib.invalidate_caches()");
}

async function start() {
  $("run").addEventListener("click", findCitations);
  $("sample").addEventListener("click", loadSample);
  $("clear").addEventListener("click", clearAll);
  try {
    pyodide = await loadPyodide({ indexURL: new URL("pyodide/", document.baseURI).href });
    await installWheels();
    demo = pyodide.pyimport("rfikit.demo");
    $("run").disabled = false;
    $("sample").disabled = false;
    setStatus("Ready. Paste text or load a sample.");
  } catch (e) {
    setStatus("The Python runtime could not start: " + pyError(e));
  }
}

start();
