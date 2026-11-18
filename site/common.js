"use strict";

const $ = (id) => document.getElementById(id);

function el(tag, text, className) {
  const node = document.createElement(tag);
  if (text !== undefined) node.textContent = text;
  if (className) node.className = className;
  return node;
}

function makeTable(title, columns, rows, numeric) {
  const numbers = new Set(numeric || []);
  const wrap = el("div", undefined, "scroll");
  wrap.tabIndex = 0;
  wrap.setAttribute("role", "region");
  wrap.setAttribute("aria-label", title);
  const table = el("table");
  table.appendChild(el("caption", title));
  const head = el("tr");
  columns.forEach((label, i) => {
    const th = el("th", label, numbers.has(i) ? "num" : undefined);
    th.scope = "col";
    head.appendChild(th);
  });
  const thead = el("thead");
  thead.appendChild(head);
  table.appendChild(thead);
  const body = el("tbody");
  for (const row of rows) {
    const tr = el("tr");
    row.forEach((text, i) => tr.appendChild(el("td", String(text), numbers.has(i) ? "num" : undefined)));
    body.appendChild(tr);
  }
  table.appendChild(body);
  wrap.appendChild(table);
  return wrap;
}
