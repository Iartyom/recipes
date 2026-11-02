#!/usr/bin/env python3
"""Render recipes.json into a self-contained index.html (inline CSS/JS). Stdlib only.

Do not hand-edit index.html — rerun this script (add_recipe.py / serve.py call it automatically).
"""
import json
import os
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent
# On GitHub Pages, add/edit/delete open a prefilled issue in this repo; the add-recipe workflow commits it.
REPO = os.environ.get("GITHUB_REPOSITORY", "Iartyom/recipes")

PAGE = r"""<!doctype html>
<html lang="he" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light">
<title>המטבח שלנו</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Frank+Ruhl+Libre:wght@500;700;900&family=Heebo:wght@400;500;700&display=swap" rel="stylesheet">
<style>
/* Light, warm kitchen palette: cream paper, tomato, basil, saffron. Light mode only by request. */
:root{--bg:#fbf5ec;--paper:#fffdf8;--ink:#3a2a20;--muted:#8b7564;--line:#efe2d0;--chip:#f7ead8;
  --tomato:#d6492a;--tomato-d:#b23a20;--basil:#4f8a35;--saffron:#f0a92e;--shadow:0 6px 22px rgba(120,72,30,.10)}
*{box-sizing:border-box}
html{color-scheme:light}
body{margin:0;color:var(--ink);font:16px/1.6 Heebo,system-ui,Arial,sans-serif;
  background:var(--bg) radial-gradient(circle at 1px 1px,rgba(214,73,42,.07) 1px,transparent 0) 0 0/22px 22px}
h1,h2,h3{font-family:"Frank Ruhl Libre",Georgia,serif;line-height:1.2}
a{color:var(--tomato)}
input,textarea,button{font:inherit;color:inherit}
input,textarea{width:100%;padding:11px 14px;border:1.5px solid var(--line);border-radius:12px;background:#fff;outline:none;transition:border .15s}
input:focus,textarea:focus{border-color:var(--saffron)}
textarea{min-height:110px;resize:vertical}
button{border:0;border-radius:999px;padding:10px 20px;background:var(--tomato);color:#fff;cursor:pointer;font-weight:500;transition:transform .1s,background .15s}
button:hover{background:var(--tomato-d)}
button:active{transform:scale(.97)}
button.soft{background:var(--chip);color:var(--ink)}
button.soft:hover{background:#f0dcc2}
button.green{background:var(--basil)}
button.danger{background:#fff;color:var(--tomato);border:1.5px solid var(--tomato)}
.wrap{max-width:1120px;margin:auto;padding:0 16px}

/* Header */
.hero{background:linear-gradient(135deg,#e35a33 0%,#f0a92e 100%);color:#fff;position:relative;overflow:hidden}
.hero .wrap{padding:34px 16px 70px;position:relative;z-index:1}
.hero h1{margin:0;font-size:clamp(34px,6vw,54px);font-weight:900;letter-spacing:-.5px}
.hero p{margin:6px 0 0;opacity:.92;font-size:17px}
.hero .float{position:absolute;inset:0;pointer-events:none;font-size:34px;opacity:.22}
.hero .float span{position:absolute}
.hero svg.wave{position:absolute;bottom:-1px;left:0;width:100%;height:40px}
.toolbar{margin-top:-38px;position:relative;z-index:2;display:flex;gap:10px;align-items:center}
.search{flex:1;position:relative}
.search input{padding-inline-start:44px;height:52px;border-radius:999px;box-shadow:var(--shadow);border-color:#fff;font-size:17px}
.search::before{content:"🔍";position:absolute;inset-inline-start:16px;top:13px;font-size:18px}
.toolbar button{height:52px;box-shadow:var(--shadow);white-space:nowrap}
.chips{display:flex;gap:8px;flex-wrap:wrap;margin:18px 0 6px}
.chip{background:var(--paper);border:1.5px solid var(--line);border-radius:999px;padding:5px 14px;font-size:14px;cursor:pointer;user-select:none}
.chip.on{background:var(--basil);border-color:var(--basil);color:#fff}
.count{color:var(--muted);font-size:14px;margin:6px 0 14px}

/* Cards */
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:20px;padding-bottom:50px}
.card{background:var(--paper);border-radius:20px;overflow:hidden;cursor:pointer;box-shadow:var(--shadow);
  transition:transform .18s,box-shadow .18s;display:flex;flex-direction:column}
.card:hover{transform:translateY(-4px);box-shadow:0 12px 30px rgba(120,72,30,.18)}
.pic{position:relative;aspect-ratio:4/3;overflow:hidden}
.pic img{width:100%;height:100%;object-fit:cover;display:block;transition:transform .4s}
.card:hover .pic img{transform:scale(1.05)}
.ph{width:100%;height:100%;display:flex;align-items:center;justify-content:center;font-size:64px}
.badge{position:absolute;bottom:10px;inset-inline-start:10px;background:rgba(255,253,248,.94);border-radius:999px;padding:3px 10px;font-size:13px;font-weight:500}
.fav{position:absolute;top:10px;inset-inline-end:10px;font-size:20px;filter:drop-shadow(0 1px 2px rgba(0,0,0,.3))}
.card .b{padding:14px 16px 16px}
.card h3{margin:0 0 6px;font-size:20px}
.card .tags{color:var(--muted);font-size:13px}
.empty{grid-column:1/-1;text-align:center;padding:60px 20px;color:var(--muted)}
.empty .big{font-size:70px}

/* Recipe view */
#view{display:none;padding-bottom:60px}
#view.open{display:block}
.vhead{position:relative;border-radius:24px;overflow:hidden;margin:22px 0;box-shadow:var(--shadow);min-height:220px;
  background:linear-gradient(135deg,#e35a33,#f0a92e)}
.vhead img{width:100%;max-height:420px;object-fit:cover;display:block}
.vhead .ph{height:240px;font-size:110px}
.vhead .over{position:absolute;inset:auto 0 0 0;padding:60px 26px 22px;color:#fff;
  background:linear-gradient(transparent,rgba(40,20,10,.75))}
.vhead h2{margin:0;font-size:clamp(28px,5vw,44px)}
.vmeta{display:flex;gap:8px;flex-wrap:wrap;margin-top:10px}
.vmeta span{background:rgba(255,255,255,.2);backdrop-filter:blur(4px);border-radius:999px;padding:3px 12px;font-size:14px}
.actions{display:flex;gap:8px;flex-wrap:wrap;margin:18px 0 0}
.desc{font-size:18px;color:#5b4637;margin:0 0 18px}
.cols{display:grid;grid-template-columns:minmax(260px,1fr) 2fr;gap:26px;align-items:start}
@media (max-width:780px){.cols{grid-template-columns:1fr}.toolbar{flex-wrap:wrap}.toolbar button{flex:1}}
.box{background:var(--paper);border-radius:20px;padding:20px 22px;box-shadow:var(--shadow)}
.box h3{margin:0 0 12px;font-size:24px;display:flex;align-items:center;gap:8px}
/* Ingredients look like a lined notepad. */
.ing{background:repeating-linear-gradient(var(--paper) 0 39px,var(--line) 39px 40px)}
.ing label{display:flex;gap:10px;align-items:center;min-height:40px;cursor:pointer}
.ing input{width:20px;height:20px;accent-color:var(--basil);flex:none}
.ing input:checked+span{text-decoration:line-through;color:var(--muted)}
ol.steps{list-style:none;padding:0;margin:0;counter-reset:s}
ol.steps li{counter-increment:s;position:relative;padding:4px 50px 16px 0;min-height:44px}
ol.steps li::before{content:counter(s);position:absolute;right:0;top:0;width:36px;height:36px;border-radius:50%;
  background:var(--tomato);color:#fff;display:flex;align-items:center;justify-content:center;font-weight:700}
ol.steps li.sec{counter-increment:none;padding:10px 0 8px;font-family:"Frank Ruhl Libre",serif;font-weight:700;font-size:19px;color:var(--basil)}
ol.steps li.sec::before{display:none}
ol.steps li.done{color:var(--muted)}
.src{color:var(--muted);font-size:14px;margin-top:20px}

/* Sheet (add / edit) */
.sheet-bg{position:fixed;inset:0;background:rgba(58,42,32,.45);display:none;z-index:10;align-items:flex-start;justify-content:center;overflow:auto;padding:30px 16px}
.sheet-bg.open{display:flex}
.sheet{background:var(--paper);border-radius:24px;padding:24px;max-width:640px;width:100%;box-shadow:0 20px 60px rgba(0,0,0,.25)}
.sheet h2{margin:0 0 4px}
.sheet .hint{color:var(--muted);font-size:14px;margin:0 0 14px}
.sheet label.f{display:block;font-weight:500;font-size:14px;margin:12px 0 4px}
.sheet .two{display:grid;grid-template-columns:1fr 1fr;gap:10px}
.sheet .row{display:flex;gap:8px;justify-content:flex-start;margin-top:18px;flex-wrap:wrap}
.toast{position:fixed;bottom:22px;left:50%;transform:translateX(-50%) translateY(120px);background:var(--ink);color:#fff;
  padding:12px 20px;border-radius:999px;z-index:20;transition:transform .25s;max-width:92vw}
.toast.show{transform:translateX(-50%) translateY(0)}
</style>
</head>
<body>
<header class="hero">
  <div class="float" aria-hidden="true">
    <span style="top:12%;left:6%">🍅</span><span style="top:55%;left:16%;font-size:26px">🌿</span>
    <span style="top:18%;left:30%;font-size:28px">🧄</span><span style="top:60%;left:42%">🍋</span>
    <span style="top:10%;left:55%;font-size:24px">🌶️</span><span style="top:48%;left:68%">🥖</span>
    <span style="top:14%;left:82%;font-size:30px">🧀</span><span style="top:58%;left:90%;font-size:26px">🫒</span>
  </div>
  <div class="wrap">
    <h1>המטבח שלנו</h1>
    <p id="count">מתכונים שאוהבים, במקום אחד</p>
  </div>
  <svg class="wave" viewBox="0 0 1440 40" preserveAspectRatio="none"><path fill="#fbf5ec" d="M0 40V18c180 18 360 22 540 10S900 0 1080 6s270 24 360 20v14z"/></svg>
</header>

<main class="wrap">
  <section id="list">
    <div class="toolbar">
      <div class="search"><input id="q" type="search" placeholder="מה מבשלים היום? שם, מצרך או תגית…" dir="auto"></div>
      <button id="open-add">➕ מתכון חדש</button>
    </div>
    <div class="chips" id="tags"></div>
    <div class="count" id="found"></div>
    <div class="grid" id="grid"></div>
  </section>
  <section id="view"></section>
</main>

<div class="sheet-bg" id="sheet-bg"><div class="sheet" id="sheet"></div></div>
<div class="toast" id="toast"></div>

<script>
const DATA = __DATA__;
const REPO = __REPO__;
const R = DATA.recipes.slice().reverse();  // newest first
// Served by serve.py on this machine → changes save instantly; on GitHub Pages they go through an issue.
const LOCAL = /^(127\.0\.0\.1|localhost)$/.test(location.hostname);
const $ = id => document.getElementById(id);
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));

// Placeholder art when a recipe has no photo: emoji by keyword, warm gradient picked from the id.
const EMOJI = [[/עוף|חזה|כרעיים|שניצל|chicken/i,"🍗"],[/בשר|קציצ|סטייק|בקר|beef|meat/i,"🥩"],[/דג|סלמון|טונה|fish/i,"🐟"],
  [/עוג|קינוח|שוקולד|עוגי|cake|dessert|cookie/i,"🍰"],[/לחם|חלה|מאפה|בצק|bread/i,"🥖"],[/פסטה|ספגטי|pasta/i,"🍝"],
  [/מרק|soup/i,"🍲"],[/סלט|salad/i,"🥗"],[/ביצ|שקשוק|חביתה|egg/i,"🍳"],[/אורז|rice/i,"🍚"],[/פיצה|pizza/i,"🍕"],
  [/ירק|טבעוני|צמחוני|vegan/i,"🥦"],[/בוקר|breakfast/i,"🥞"]];
const GRADS = ["#f6c9a8,#f0a92e","#f4b3a0,#d6492a","#cfe3b8,#7fae5a","#f7dd9c,#f0a92e","#f3c4c4,#e0736a","#e9d5b5,#c99a5b"];
function emojiFor(r) {
  const hay = [r.title, ...(r.tags || [])].join(" ");
  return (EMOJI.find(([re]) => re.test(hay)) || [0, "🍽️"])[1];
}
function placeholder(r) {
  let h = 0; for (const c of r.id || r.title || "") h = (h * 31 + c.charCodeAt(0)) >>> 0;
  return `<div class="ph" style="background:linear-gradient(135deg,${GRADS[h % GRADS.length]})">${emojiFor(r)}</div>`;
}
function pic(r) {
  return r.image ? `<img loading="lazy" src="${esc(r.image)}" alt="" onerror="this.replaceWith(Object.assign(document.createElement('div'),{innerHTML:${esc(JSON.stringify(placeholder(r)))}}).firstChild)">`
                 : placeholder(r);
}
const time = r => r.total_minutes ? `⏱ ${r.total_minutes} דק׳` : "";

// Favorites are a per-browser convenience only; the recipes themselves live in git.
let fav = new Set();
try { fav = new Set(JSON.parse(localStorage.getItem("recipes:fav") || "[]")); } catch (e) {}
const saveFav = () => { try { localStorage.setItem("recipes:fav", JSON.stringify([...fav])); } catch (e) {} };
let activeTag = "";

function toast(msg, ms = 3500) {
  const t = $("toast"); t.textContent = msg; t.classList.add("show");
  clearTimeout(toast.h); toast.h = setTimeout(() => t.classList.remove("show"), ms);
}

// ---------- list ----------
function tagsAll() {
  const n = {};
  R.forEach(r => (r.tags || []).forEach(t => n[t] = (n[t] || 0) + 1));
  return Object.keys(n).sort((a, b) => n[b] - n[a]).slice(0, 24);
}
function renderList() {
  const q = $("q").value.trim().toLowerCase();
  const hit = R.filter(r => {
    if (activeTag === "★" ? !fav.has(r.id) : activeTag && !(r.tags || []).includes(activeTag)) return false;
    return !q || [r.title, r.description, ...(r.ingredients || []), ...(r.tags || [])].join(" ").toLowerCase().includes(q);
  });
  $("count").textContent = R.length ? `${R.length} מתכונים שאוהבים, במקום אחד` : "מתכונים שאוהבים, במקום אחד";
  $("tags").innerHTML = R.length ? ["★", ...tagsAll()].map(t =>
    `<span class="chip ${t === activeTag ? "on" : ""}" data-t="${esc(t)}">${t === "★" ? "❤️ מועדפים" : esc(t)}</span>`).join("") : "";
  $("found").textContent = (q || activeTag) ? `${hit.length} תוצאות` : "";
  $("grid").innerHTML = hit.length ? hit.map(r => `
    <article class="card" data-id="${esc(r.id)}">
      <div class="pic">${pic(r)}${time(r) ? `<span class="badge">${time(r)}</span>` : ""}${fav.has(r.id) ? '<span class="fav">❤️</span>' : ""}</div>
      <div class="b"><h3 dir="auto">${esc(r.title)}</h3>
        <div class="tags">${[r.servings && "🍽 " + esc(r.servings), (r.tags || []).slice(0, 3).map(esc).join(" · ")].filter(Boolean).join(" · ")}</div></div>
    </article>`).join("")
    : `<div class="empty"><div class="big">${R.length ? "🔎" : "🍳"}</div>
        ${R.length ? "לא נמצא מתכון שמתאים לחיפוש" : "הספר עוד ריק — לחצו על <b>➕ מתכון חדש</b> והדביקו קישור או טקסט"}</div>`;
}

// ---------- recipe view ----------
function renderView(id) {
  const r = R.find(x => x.id === id);
  const view = $("view"), list = $("list");
  if (!r) { view.className = ""; list.style.display = ""; renderList(); return; }
  list.style.display = "none"; view.className = "open";
  let n = 0;
  const steps = (r.steps || []).map(s => /:$/.test(s) && s.length < 60
    ? `<li class="sec">${esc(s)}</li>` : `<li data-n="${n++}">${esc(s)}</li>`).join("");
  const host = (() => { try { return new URL(r.source_url).hostname.replace(/^www\./, ""); } catch (e) { return ""; } })();
  view.innerHTML = `
    <div class="actions">
      <button class="soft" onclick="location.hash=''">→ לכל המתכונים</button>
      <button class="soft" id="v-fav">${fav.has(r.id) ? "❤️ במועדפים" : "🤍 למועדפים"}</button>
      <button class="soft" id="v-edit">✏️ עריכה</button>
      <button class="danger" id="v-del">🗑️ מחיקה</button>
    </div>
    <div class="vhead">${r.image ? `<img src="${esc(r.image)}" alt="" onerror="this.remove()">` : placeholder(r)}
      <div class="over"><h2 dir="auto">${esc(r.title)}</h2>
        <div class="vmeta">${[time(r), r.servings && "🍽 " + esc(r.servings), ...(r.tags || []).map(esc)].filter(Boolean).map(x => `<span>${x}</span>`).join("")}</div></div></div>
    ${r.description ? `<p class="desc" dir="auto">${esc(r.description)}</p>` : ""}
    <div class="cols">
      <div class="box ing"><h3>🧺 מצרכים</h3><div dir="auto">${(r.ingredients || []).map(i =>
        `<label><input type="checkbox"><span>${esc(i)}</span></label>`).join("") || '<div class="src">אין רשימת מצרכים</div>'}</div></div>
      <div class="box"><h3>👩‍🍳 אופן ההכנה</h3><ol class="steps" dir="auto">${steps || '<li class="sec">אין שלבים</li>'}</ol></div>
    </div>
    ${(r.notes || []).length ? `<div class="box" style="margin-top:22px"><h3>💡 טיפים והערות</h3><div dir="auto">${r.notes.map(s =>
      /:$/.test(s) && s.length < 45 ? `<h4 style="margin:12px 0 4px;color:var(--basil)">${esc(s)}</h4>` : `<p style="margin:4px 0">${esc(s)}</p>`).join("")}</div></div>` : ""}
    <div class="src">${r.image_auto ? "📷 תמונה להמחשה (Pexels) · " : ""}${host ? `מקור: <a href="${esc(r.source_url)}" target="_blank" rel="noopener">${esc(host)} ↗</a> · ` : ""}נוסף ${esc(r.added || "")}</div>`;
  $("v-fav").onclick = () => { fav.has(r.id) ? fav.delete(r.id) : fav.add(r.id); saveFav(); renderView(id); };
  $("v-edit").onclick = () => openEdit(r);
  // Two-tap delete instead of confirm(): no blocking browser dialog.
  $("v-del").onclick = e => {
    const b = e.currentTarget;
    if (!b.dataset.armed) { b.dataset.armed = 1; b.textContent = "בטוח? לחצו שוב למחיקה"; setTimeout(() => { delete b.dataset.armed; b.textContent = "🗑️ מחיקה"; }, 4000); return; }
    change("delete", {id: r.id}, `מחיקת מתכון: ${r.title}`, r.id);
  };
  // Tap a step to mark it done while cooking.
  view.querySelectorAll("ol.steps li[data-n]").forEach(li => li.onclick = () => li.classList.toggle("done"));
  window.scrollTo(0, 0);
}

// ---------- add / edit sheet ----------
function openSheet(html) { $("sheet").innerHTML = html; $("sheet-bg").classList.add("open"); }
function closeSheet() { $("sheet-bg").classList.remove("open"); }
$("sheet-bg").onclick = e => { if (e.target.id === "sheet-bg") closeSheet(); };
document.addEventListener("keydown", e => { if (e.key === "Escape") closeSheet(); });

function openAdd() {
  openSheet(`
    <h2>➕ מתכון חדש</h2>
    <p class="hint">רק להדביק — קישור או את כל טקסט המתכון. מצרכים, שלבים, זמן, מנות, תגיות ותמונה נשלפים לבד.</p>
    <textarea id="a-text" dir="auto" style="min-height:180px" placeholder="https://… או טקסט המתכון"></textarea>
    <p class="hint" style="margin-top:10px">${LOCAL ? "נשמר מיד ונכנס ל-git. אפשר לתקן אחר כך ב-✏️." : "ייפתח issue מוכן ב-GitHub — לוחצים Submit, והמתכון מופיע כאן תוך כדקה."}</p>
    <div class="row"><button id="a-go">${LOCAL ? "הוספה" : "שליחה ל-GitHub"}</button><button class="soft" onclick="closeSheet()">ביטול</button></div>`);
  $("a-text").focus();
  $("a-go").onclick = () => {
    const text = $("a-text").value.trim(); if (!text) return;
    change("add", text, "מתכון: " + text.split("\n")[0].slice(0, 60), null);
  };
}
function openEdit(r) {
  const v = x => esc(x ?? "");
  openSheet(`
    <h2>✏️ עריכת מתכון</h2>
    <label class="f">שם</label><input id="e-title" dir="auto" value="${v(r.title)}">
    <label class="f">תיאור</label><textarea id="e-desc" dir="auto" style="min-height:60px">${v(r.description)}</textarea>
    <div class="two">
      <div><label class="f">מנות</label><input id="e-serv" dir="auto" value="${v(r.servings)}"></div>
      <div><label class="f">זמן (דקות)</label><input id="e-min" type="number" min="0" value="${v(r.total_minutes)}"></div>
    </div>
    <label class="f">תגיות (מופרדות בפסיק)</label><input id="e-tags" dir="auto" value="${v((r.tags || []).join(", "))}">
    <label class="f">קישור לתמונה</label><input id="e-img" dir="ltr" value="${v(r.image)}">
    <label class="f">מצרכים — שורה לכל מצרך</label><textarea id="e-ing" dir="auto" style="min-height:150px">${v((r.ingredients || []).join("\n"))}</textarea>
    <label class="f">שלבים — שורה לכל שלב (שורה שמסתיימת ב-":" = כותרת)</label><textarea id="e-steps" dir="auto" style="min-height:180px">${v((r.steps || []).join("\n"))}</textarea>
    <label class="f">טיפים והערות — שורה לכל הערה</label><textarea id="e-notes" dir="auto" style="min-height:90px">${v((r.notes || []).join("\n"))}</textarea>
    <label class="f">מקור</label><input id="e-src" dir="ltr" value="${v(r.source_url)}">
    <div class="row"><button class="green" id="e-go">${LOCAL ? "שמירה" : "שליחה ל-GitHub"}</button><button class="soft" onclick="closeSheet()">ביטול</button></div>`);
  $("e-go").onclick = () => {
    const lines = id => $(id).value.split("\n").map(s => s.trim()).filter(Boolean);
    const rec = {id: r.id, title: $("e-title").value.trim(), description: $("e-desc").value.trim(),
      servings: $("e-serv").value.trim(), total_minutes: $("e-min").value.trim(), image: $("e-img").value.trim(),
      tags: $("e-tags").value.split(",").map(s => s.trim()).filter(Boolean),
      ingredients: lines("e-ing"), steps: lines("e-steps"), notes: lines("e-notes"), source_url: $("e-src").value.trim()};
    // A photo the user typed in is theirs, not an auto-picked illustration.
    rec.image_auto = !!r.image_auto && rec.image === r.image;
    if (!rec.title) return toast("חסר שם מתכון");
    change("save", rec, "עריכת מתכון: " + rec.title, r.id);
  };
}

// One path for every change: local server → instant; GitHub Pages → prefilled issue for the workflow.
async function change(kind, payload, issueTitle, goTo) {
  if (LOCAL) {
    toast(kind === "add" ? "⏳ קורא את המתכון…" : "⏳ שומר…", 60000);
    try {
      const res = await fetch("/api/" + kind, {method: "POST", body: typeof payload === "string" ? payload : JSON.stringify(payload)});
      const r = await res.json();
      if (!r.ok) return toast("❌ " + r.error, 6000);
      location.hash = r.id ? encodeURIComponent(r.id) : "";
      location.reload();  // serve.py rebuilt index.html with the change
    } catch (e) { toast("❌ השרת המקומי לא עונה — הפעילו python serve.py", 6000); }
    return;
  }
  const body = kind === "add" ? payload
    : kind === "delete" ? payload.id
    : "```json\n" + JSON.stringify(payload, null, 1) + "\n```";
  const url = `https://github.com/${REPO}/issues/new?title=${encodeURIComponent(issueTitle)}&body=${encodeURIComponent(body)}`;
  if (url.length > 8000) return toast("❌ המתכון ארוך מדי לשליחה מהאתר — ערכו מהמחשב (python serve.py)", 7000);
  window.open(url, "_blank");
  closeSheet();
  toast("נפתח GitHub — לחצו Submit. השינוי יופיע כאן תוך כדקה.", 6000);
}

$("open-add").onclick = openAdd;
$("q").oninput = renderList;
$("tags").onclick = e => { const t = e.target.dataset.t; if (t === undefined) return; activeTag = activeTag === t ? "" : t; renderList(); };
$("grid").onclick = e => { const c = e.target.closest(".card"); if (c) location.hash = encodeURIComponent(c.dataset.id); };
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
