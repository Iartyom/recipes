#!/usr/bin/env python3
"""Render recipes.json into a self-contained index.html (inline CSS/JS). Stdlib only.

Do not hand-edit index.html — rerun this script (add_recipe.py calls it automatically).
"""
import json
import os
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent
# The "add" form opens a prefilled GitHub issue in this repo; the add-recipe workflow turns it into a commit.
REPO = os.environ.get("GITHUB_REPOSITORY", "Iartyom/recipes")

PAGE = r"""<!doctype html>
<html lang="he" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>המתכונים שלנו</title>
<style>
:root{--bg:#faf7f2;--card:#fff;--ink:#2b2622;--muted:#7a7068;--line:#e8e1d8;--accent:#c2562d;--chip:#f1e9df}
@media (prefers-color-scheme:dark){:root{--bg:#1b1917;--card:#262321;--ink:#eee8e1;--muted:#a59b91;--line:#3a3532;--accent:#e57a4f;--chip:#332e2a}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.55 system-ui,"Segoe UI",Arial,sans-serif}
header{padding:20px 16px 8px;max-width:1100px;margin:auto}
h1{margin:0 0 4px;font-size:26px}
.sub{color:var(--muted);font-size:14px}
main{max-width:1100px;margin:auto;padding:0 16px 40px}
input,textarea,button{font:inherit;color:inherit}
input,textarea{width:100%;padding:10px 12px;border:1px solid var(--line);border-radius:10px;background:var(--card)}
button{border:0;border-radius:10px;padding:10px 16px;background:var(--accent);color:#fff;cursor:pointer}
button.ghost{background:var(--chip);color:var(--ink)}
details.add{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:12px 14px;margin:12px 0}
details.add summary{cursor:pointer;font-weight:600}
details.add textarea{min-height:110px;margin:10px 0 8px}
.row{display:flex;gap:8px;flex-wrap:wrap;align-items:center}
.chips{display:flex;gap:6px;flex-wrap:wrap;margin:12px 0}
.chip{background:var(--chip);border:1px solid transparent;border-radius:999px;padding:4px 12px;font-size:14px;cursor:pointer}
.chip.on{border-color:var(--accent);color:var(--accent)}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:14px}
.card{background:var(--card);border:1px solid var(--line);border-radius:14px;overflow:hidden;cursor:pointer;display:flex;flex-direction:column}
.card img,.card .noimg{width:100%;aspect-ratio:4/3;object-fit:cover;background:var(--chip);display:flex;align-items:center;justify-content:center;font-size:40px}
.card .b{padding:10px 12px}
.card h3{margin:0 0 4px;font-size:17px}
.meta{color:var(--muted);font-size:13px}
.empty{color:var(--muted);text-align:center;padding:40px 0}
#view{display:none}
#view.open{display:block}
.back{margin:8px 0 14px}
.hero{width:100%;max-height:380px;object-fit:cover;border-radius:14px}
.cols{display:grid;grid-template-columns:1fr 2fr;gap:24px}
@media (max-width:760px){.cols{grid-template-columns:1fr}}
.ing label{display:flex;gap:8px;padding:6px 0;border-bottom:1px solid var(--line);cursor:pointer}
.ing input{width:auto}
.ing input:checked+span{text-decoration:line-through;color:var(--muted)}
ol.steps{padding-inline-start:22px}
ol.steps li{margin:0 0 12px}
ol.steps li.sec{list-style:none;font-weight:700;margin-inline-start:-22px}
.star{background:none;color:var(--accent);font-size:22px;padding:0 6px}
a{color:var(--accent)}
</style>
</head>
<body>
<header>
  <h1>🍲 המתכונים שלנו</h1>
  <div class="sub" id="count"></div>
</header>
<main>
  <section id="list">
    <details class="add">
      <summary>➕ הוספת מתכון</summary>
      <textarea id="add-text" placeholder="הדביקו קישור למתכון, או את כל הטקסט (שורה ראשונה = שם, ואז &quot;מצרכים&quot; ו&quot;אופן ההכנה&quot;)" dir="auto"></textarea>
      <input id="add-tags" placeholder="תגיות (לא חובה): עוף, ערב שבת" dir="auto">
      <div class="row" style="margin-top:8px">
        <button id="add-go">שליחה ל-GitHub</button>
        <span class="sub" id="add-hint">נפתח issue מוכן — לוחצים Submit, והמתכון מופיע כאן תוך כדקה.</span>
      </div>
    </details>
    <input id="q" type="search" placeholder="חיפוש לפי שם, מצרך או תגית…" dir="auto">
    <div class="chips" id="tags"></div>
    <div class="grid" id="grid"></div>
  </section>
  <section id="view"></section>
</main>
<script>
const DATA = __DATA__;
const REPO = __REPO__;
const R = DATA.recipes.slice().reverse();  // newest first
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
// Favorites are a per-browser convenience only; the recipes themselves live in git.
const FKEY = "recipes:fav";
let fav = new Set();
try { fav = new Set(JSON.parse(localStorage.getItem(FKEY) || "[]")); } catch (e) {}
const saveFav = () => { try { localStorage.setItem(FKEY, JSON.stringify([...fav])); } catch (e) {} };
let activeTag = "";

function tagsAll() {
  const n = {};
  R.forEach(r => (r.tags || []).forEach(t => n[t] = (n[t] || 0) + 1));
  return Object.keys(n).sort((a, b) => n[b] - n[a]).slice(0, 30);
}
function time(r) { return r.total_minutes ? `⏱ ${r.total_minutes} דק׳` : ""; }

function renderList() {
  const q = document.getElementById("q").value.trim().toLowerCase();
  const hit = R.filter(r => {
    if (activeTag === "★" ? !fav.has(r.id) : activeTag && !(r.tags || []).includes(activeTag)) return false;
    if (!q) return true;
    return [r.title, r.description, ...(r.ingredients || []), ...(r.tags || [])].join(" ").toLowerCase().includes(q);
  });
  document.getElementById("count").textContent = `${R.length} מתכונים`;
  const chips = ["★", ...tagsAll()];
  document.getElementById("tags").innerHTML = chips.map(t =>
    `<span class="chip ${t === activeTag ? "on" : ""}" data-t="${esc(t)}">${t === "★" ? "★ מועדפים" : esc(t)}</span>`).join("");
  document.getElementById("grid").innerHTML = hit.length ? hit.map(r => `
    <div class="card" data-id="${esc(r.id)}">
      ${r.image ? `<img loading="lazy" src="${esc(r.image)}" alt="" onerror="this.outerHTML='<div class=noimg>🍽️</div>'">` : `<div class="noimg">🍽️</div>`}
      <div class="b"><h3 dir="auto">${fav.has(r.id) ? "★ " : ""}${esc(r.title)}</h3>
      <div class="meta">${[time(r), r.servings && "🍽 " + esc(r.servings), (r.tags || []).slice(0, 3).map(esc).join(" · ")].filter(Boolean).join(" · ")}</div></div>
    </div>`).join("") : `<div class="empty">אין מתכונים${q || activeTag ? " שמתאימים לחיפוש" : " עדיין — הוסיפו את הראשון למעלה"}</div>`;
}

function renderView(id) {
  const r = R.find(x => x.id === id);
  const view = document.getElementById("view"), list = document.getElementById("list");
  if (!r) { view.className = ""; list.style.display = ""; renderList(); return; }
  list.style.display = "none"; view.className = "open";
  const steps = (r.steps || []).map(s => /:$/.test(s) && s.length < 60
    ? `<li class="sec">${esc(s)}</li>` : `<li>${esc(s)}</li>`).join("");
  view.innerHTML = `
    <div class="row back"><button class="ghost" onclick="location.hash=''">→ חזרה</button>
      <button class="star" id="star" title="מועדף">${fav.has(r.id) ? "★" : "☆"}</button></div>
    ${r.image ? `<img class="hero" src="${esc(r.image)}" alt="" onerror="this.remove()">` : ""}
    <h2 dir="auto">${esc(r.title)}</h2>
    <div class="meta">${[time(r), r.servings && "🍽 " + esc(r.servings), (r.tags || []).map(esc).join(" · "), "נוסף " + esc(r.added)].filter(Boolean).join(" · ")}</div>
    ${r.description ? `<p dir="auto">${esc(r.description)}</p>` : ""}
    <div class="cols">
      <div><h3>מצרכים</h3><div class="ing" dir="auto">${(r.ingredients || []).map(i =>
        `<label><input type="checkbox"><span>${esc(i)}</span></label>`).join("") || '<div class="sub">—</div>'}</div></div>
      <div><h3>אופן ההכנה</h3><ol class="steps" dir="auto">${steps || '<li class="sec">—</li>'}</ol></div>
    </div>
    ${r.source_url ? `<p class="sub">מקור: <a href="${esc(r.source_url)}" target="_blank" rel="noopener">${esc(new URL(r.source_url).hostname)} ↗</a></p>` : ""}`;
  document.getElementById("star").onclick = () => {
    fav.has(r.id) ? fav.delete(r.id) : fav.add(r.id); saveFav(); renderView(id);
  };
  window.scrollTo(0, 0);
}

document.getElementById("q").oninput = renderList;
document.getElementById("tags").onclick = e => {
  const t = e.target.dataset.t; if (t === undefined) return;
  activeTag = activeTag === t ? "" : t; renderList();
};
document.getElementById("grid").onclick = e => {
  const c = e.target.closest(".card"); if (c) location.hash = encodeURIComponent(c.dataset.id);
};
// Served by serve.py on this machine → save directly; otherwise (GitHub Pages / file) → prefilled issue.
const LOCAL = /^(127\.0\.0\.1|localhost)$/.test(location.hostname);
if (LOCAL) {
  document.getElementById("add-go").textContent = "הוספה";
  document.getElementById("add-hint").textContent = "שמירה ישירה (שרת מקומי) — קישור נקרא אוטומטית.";
}
document.getElementById("add-go").onclick = async () => {
  const text = document.getElementById("add-text").value.trim();
  if (!text) return;
  const tags = document.getElementById("add-tags").value.trim();
  const body = text + (tags ? `\n\nתגיות: ${tags}` : "");
  const hint = document.getElementById("add-hint");
  if (LOCAL) {
    hint.textContent = "⏳ קורא את המתכון…";
    try {
      const r = await (await fetch("/api/add", {method: "POST", body})).json();
      if (!r.ok) { hint.textContent = "❌ " + r.error; return; }
      location.href = "/#" + encodeURIComponent(r.id);
      location.reload();  // the server rebuilt index.html with the new recipe
    } catch (e) { hint.textContent = "❌ השרת המקומי לא עונה — הפעילו python serve.py"; }
    return;
  }
  const first = text.split("\n")[0].slice(0, 60);
  // Title prefix "מתכון:" is what the add-recipe workflow listens for.
  window.open(`https://github.com/${REPO}/issues/new?title=${encodeURIComponent("מתכון: " + first)}&body=${encodeURIComponent(body)}`, "_blank");
};
const route = () => renderView(decodeURIComponent(location.hash.slice(1)));
window.addEventListener("hashchange", route);
route();
</script>
</body>
</html>
"""


def build():
    data = json.loads((ROOT / "recipes.json").read_text(encoding="utf-8"))
    # "</" inside embedded JSON would close the <script> tag early.
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    out = PAGE.replace("__DATA__", payload).replace("__REPO__", json.dumps(REPO))
    (ROOT / "index.html").write_text(out, encoding="utf-8")
    return ROOT / "index.html"


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    print(f"✅ נוצר {build()}")
