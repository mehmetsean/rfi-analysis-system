"use strict";

const SETS = [
  ["A", "Family A, report seeds"],
  ["B", "Family B, report seeds"],
  ["written", "Written set"],
];
const METHODS = [
  ["rfikit", "rfikit"],
  ["naive", "naive baseline"],
  ["prototype", "prototype regexes"],
];
const LEVELS = [
  ["strict", "strict span"],
  ["overlap", "overlap span"],
  ["full", "full key"],
  ["base", "base key"],
  ["clause", "clause"],
];
const GROUP_LEVELS = ["strict", "overlap", "key"];

const rate = (v) => (typeof v === "number" ? v.toFixed(3) : "n/a");
const whole = new Intl.NumberFormat("en-US");

function levelRows(methods) {
  const rows = [];
  for (const [mkey, mname] of METHODS) {
    const levels = (methods[mkey] || {}).levels || {};
    for (const [lkey, lname] of LEVELS) {
      const got = levels[lkey] || {};
      rows.push([mname, lname, rate(got.precision), rate(got.recall), rate(got.f1)]);
    }
  }
  return rows;
}

function groupRows(groups) {
  const rows = [];
  for (const name of Object.keys(groups).sort()) {
    const g = groups[name];
    const key = g.key || {};
    rows.push([name, whole.format(key.gold || 0), rate((g.strict || {}).recall), rate((g.overlap || {}).recall), rate(key.recall), rate(key.precision)]);
  }
  return rows;
}

function renderSet(box, doc, key, name) {
  const set = doc.full.sets[key];
  const methods = set.methods;
  const rfikit = methods.rfikit;
  const section = el("section");
  section.appendChild(el("h2", name + ", measured on synthetic data"));
  const seeds = set.seeds > 0 ? set.seeds + " seeds, " : "";
  section.appendChild(el("p", seeds + whole.format(rfikit.rfis) + " RFIs.", "hint"));
  const levels = ["Method", "Level", "Precision", "Recall", "F1"];
  section.appendChild(makeTable(name + ": scores per method and level", levels, levelRows(methods), [2, 3, 4]));
  const cols = ["Group", "Gold citations", "Strict recall", "Overlap recall", "Key recall", "Key precision"];
  const num = [1, 2, 3, 4, 5];
  const groups = rfikit.groups || {};
  section.appendChild(makeTable(name + ": rfikit per body", cols, groupRows(groups.body || {}), num));
  section.appendChild(makeTable(name + ": rfikit per noise class", cols, groupRows(groups.noise || {}), num));
  box.appendChild(section);
}

async function start() {
  try {
    const response = await fetch("measured.json");
    if (!response.ok) throw new Error("measured.json is missing from this site");
    const doc = await response.json();
    const box = $("sets");
    box.appendChild(el("p", doc.data + " Version " + doc.rfikit_version + "."));
    for (const [key, name] of SETS) renderSet(box, doc, key, name);
    $("status").textContent = "Loaded measured.json.";
  } catch (e) {
    $("status").textContent = "Could not load the results: " + e.message;
  }
}

start();
