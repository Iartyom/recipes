#!/usr/bin/env python3
"""Add a recipe to recipes.json from a URL or pasted text, then rebuild index.html.

Usage:  python add_recipe.py <url | text>      python add_recipe.py -   (reads stdin; used by the issue workflow)
A line "תגיות: a, b" (or "tags: a, b") anywhere in the input sets tags. Stdlib only.
"""
import datetime
import html
import json
import pathlib
import re
import sys
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent
DATA = ROOT / "recipes.json"
# Many recipe sites reject the default urllib agent; a browser UA gets the normal SSR page.
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

URL_RE = re.compile(r"https?://\S+")
TAGS_RE = re.compile(r"^\s*(?:תגיות|tags)\s*:\s*(.*)$", re.I | re.M)
ING_HDR = re.compile(r"^(?:מצרכים|המצרכים|רכיבים|חומרים|ingredients)\b[^\n]{0,30}$", re.I)
STEP_HDR = re.compile(r"^(?:אופן ההכנה|אופן הכנה|הוראות הכנה|הכנה|שלבי הכנה|instructions|directions|method|steps|preparation)"
                      r"\b[^\n]{0,30}$", re.I)
BULLET = re.compile(r"^\s*(?:[-•*·▪●]+|\d{1,2}\s*[.)]|\(\d{1,2}\))\s*")


def clean(x):
    """Strip tags/entities and collapse whitespace."""
    x = re.sub(r"<[^>]+>", " ", str(x or ""))
    return re.sub(r"\s+", " ", html.unescape(x)).strip()


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "he,en;q=0.8"})
    with urllib.request.urlopen(req, timeout=25) as r:
        charset = r.headers.get_content_charset() or "utf-8"
        return r.read().decode(charset, errors="replace")


def _ld_objects(page):
    """Yield every JSON-LD dict on the page, flattening lists and @graph."""
    for raw in re.findall(r'<script[^>]+application/ld\+json[^>]*>(.*?)</script>', page, re.S | re.I):
        try:
            data = json.loads(raw.strip())
        except ValueError:
            continue
        stack = [data]
        while stack:
            o = stack.pop()
            if isinstance(o, list):
                stack.extend(o)
            elif isinstance(o, dict):
                if "@graph" in o:
                    stack.extend(o["@graph"] if isinstance(o["@graph"], list) else [o["@graph"]])
                yield o


def _is_recipe(o):
    t = o.get("@type")
    return "Recipe" in (t if isinstance(t, list) else [t])


def _steps(v):
    """Flatten recipeInstructions: str | [str] | HowToStep | HowToSection (sections become a header step)."""
    if isinstance(v, str):
        return [s for s in (clean(p) for p in re.split(r"\n+|(?<=\.)\s+(?=\d+\.)", v)) if s]
    if isinstance(v, dict):
        if "itemListElement" in v:
            head = [clean(v["name"]) + ":"] if v.get("name") else []
            return head + _steps(v["itemListElement"])
        return [clean(v.get("text") or v.get("name"))] if (v.get("text") or v.get("name")) else []
    if isinstance(v, list):
        return [s for item in v for s in _steps(item)]
    return []


def _image(v):
    if isinstance(v, list):
        v = v[0] if v else ""
    if isinstance(v, dict):
        v = v.get("url", "")
    return v if isinstance(v, str) else ""


def minutes(iso):
    """ISO-8601 duration (PT1H30M, P0DT45M) → minutes, or None."""
    m = re.match(r"P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?", str(iso or ""))
    if not m or not any(m.groups()):
        return None
    d, h, mi = (int(g or 0) for g in m.groups())
    return d * 1440 + h * 60 + mi or None


def _meta(page, prop):
    m = re.search(r'<meta[^>]+(?:property|name)=["\']%s["\'][^>]+content=["\']([^"\']*)' % re.escape(prop), page, re.I)
    return clean(m.group(1)) if m else ""


def from_html(page, url):
    """Parse a recipe page. Prefers schema.org Recipe JSON-LD (most recipe sites ship it for Google)."""
    rec = next((o for o in _ld_objects(page) if _is_recipe(o)), None)
    if rec is None:
        raise ValueError("לא נמצא מתכון מובנה בדף (אין schema.org Recipe). הדביקו את הטקסט במקום הקישור.")
    yld = rec.get("recipeYield")
    yld = yld[0] if isinstance(yld, list) and yld else yld
    cats = rec.get("recipeCategory") or []
    kws = rec.get("keywords") or []
    tags = [clean(t) for t in (cats if isinstance(cats, list) else [cats])]
    # Sites ship keywords as a list, a comma string, or a list holding one comma string — flatten all three.
    kws = [k for item in (kws if isinstance(kws, list) else [kws]) for k in re.split(r"[,،]", str(item))]
    tags += [clean(k) for k in kws if 0 < len(clean(k)) <= 20][:4]
    desc = clean(rec.get("description"))
    # Some sites stuff the whole recipe into description; keep a teaser, the full text is in ingredients/steps.
    if len(desc) > 280:
        desc = desc[:280].rsplit(" ", 1)[0] + "…"
    return {
        "title": clean(rec.get("name")) or _meta(page, "og:title") or url,
        "description": desc,
        "image": _image(rec.get("image")) or _meta(page, "og:image"),
        "servings": clean(yld) if yld else "",
        "total_minutes": minutes(rec.get("totalTime")) or (
            (minutes(rec.get("prepTime")) or 0) + (minutes(rec.get("cookTime")) or 0)) or None,
        "ingredients": [clean(i) for i in rec.get("recipeIngredient") or [] if clean(i)],
        "steps": _steps(rec.get("recipeInstructions")),
        "notes": [],
        "tags": [t for t in dict.fromkeys(tags) if t],
        "source_url": url,
    }


# A short line opening tips/storage/serving notes — everything after it is not a cooking step.
NOTES_HDR = re.compile(r"^(?:טיפים|טיפ|הערות|הערה|תחליפים|אחסון|הקפאה|הגשה|וריאציות|מרקם|שדרוגים|"
                       r"tips|notes|storage|variations)", re.I)
# Ingredient-looking line (used only when the paste has no section headers): starts with a quantity/unit.
# No \b after the digit class: "500" and "½" would fail a word boundary.
QTY = re.compile(r"^(?:[\d½¼¾⅓⅔⅛]|(?:חצי|רבע|שליש|כוס|כוסות|כף|כפות|כפית|כפיות|קורט|חופן|מעט|גרם|ק\"ג|ליטר|מ\"ל|"
                 r"שן|שיני|חבילה|חבילת|קופסה|קופסת|צרור)(?=\s|$))")


def _is_notes_header(line):
    return len(line) <= 40 and not line.rstrip().endswith((".", ",")) and bool(NOTES_HDR.match(line))


def split_notes(steps):
    """Move everything from the first tips/storage header onward out of the steps (headers keep a ':')."""
    for i, s in enumerate(steps):
        if i and _is_notes_header(s.rstrip(":")):
            notes = [n.rstrip(":") + ":" if _is_notes_header(n.rstrip(":")) else n for n in steps[i:]]
            return steps[:i], notes
    return steps, []


def from_text(text):
    """Parse pasted text: first line = title; sections start at ingredient/step headers.
    Without headers, quantity-led lines become ingredients and the rest steps."""
    lines = [ln.strip() for ln in text.splitlines()]
    lines = [ln for ln in lines if ln and not URL_RE.fullmatch(ln)]
    if not lines:
        raise ValueError("טקסט ריק")
    title, rest = lines[0], lines[1:]
    desc, ings, steps, cur = [], [], [], None
    for ln in rest:
        bare = ln.rstrip(":").strip()
        if ING_HDR.match(bare):
            cur = ings
            continue
        if STEP_HDR.match(bare):
            cur = steps
            continue
        item = BULLET.sub("", ln).strip()
        if not item:
            continue
        (cur if cur is not None else desc).append(item)
    if not ings and not steps:
        # No headers: the first prose line(s) before any quantity line are the description.
        body, desc = desc, []
        for item in body:
            if QTY.match(item) and len(item) <= 80:
                ings.append(item)
            elif not ings and not steps and len(body) > 2 and len(item) > 60:
                desc.append(item)
            else:
                steps.append(item)
    steps, notes = split_notes(steps)
    src = URL_RE.search(text)
    return {"title": BULLET.sub("", title), "description": " ".join(desc), "image": "", "servings": "",
            "total_minutes": None, "ingredients": ings, "steps": steps, "notes": notes, "tags": [],
            "source_url": src.group(0) if src else ""}


# ---------- auto-fill: time, servings, tags, photo ----------
_NUM = r"(\d+(?:\.\d+)?)"
TIME_RE = re.compile(rf"(?:{_NUM}\s*[-–]\s*)?{_NUM}\s*(?:דקות|דק['׳]|דקה|minutes?|mins?)\b"
                     rf"|(שעה וחצי)|(חצי שעה)|(?:{_NUM}\s*)?(שעות|שעה|hours?)\b", re.I)
SERV_RE = re.compile(r"(?:ל[-־]?\s*)?(\d+)\s*(מנות|סועדים|יחידות|קציצות|עוגיות|לביבות|servings|serves)", re.I)


def guess_minutes(steps):
    """Sum the largest time mentioned in each step ("אופים 18–22 דקות" → 22). None when no step mentions time."""
    total = 0
    for s in steps:
        best = 0
        for m in TIME_RE.finditer(s):
            lo, mins, h15, h05, hn, hw = m.groups()
            if mins:
                best = max(best, float(mins))
            elif h15:
                best = max(best, 90)
            elif h05:
                best = max(best, 30)
            elif hw:
                best = max(best, float(hn or 1) * 60)
        total += best
    return int(total) or None


# Hebrew stem → (tag, English photo keyword). Order matters: specific dishes before generic ingredients.
FOOD = [("שקשוק", "ארוחת בוקר", "shakshuka"), ("קציצ", "", "meatballs"), ("שניצל", "עוף", "schnitzel"),
        ("פרגי", "עוף", "grilled chicken"), ("עוף", "עוף", "chicken"), ("סלמון", "דגים", "salmon"),
        ("דג", "דגים", "fish"), ("סטייק", "בשרי", "steak"), ("אנטריקוט", "בשרי", "steak"),
        ("עוגת גבינה", "קינוח", "cheesecake"), ("עוגיות", "קינוח", "cookies"), ("עוג", "קינוח", "cake"),
        ("מאפינס", "קינוח", "muffins"), ("גלידה", "קינוח", "ice cream"), ("שוקולד", "קינוח", "chocolate"),
        ("חלה", "מאפים", "challah bread"), ("לחם", "מאפים", "bread"), ("פיצה", "מאפים", "pizza"),
        ("בורקס", "מאפים", "pastry"), ("פשטיד", "", "quiche"), ("פסטה", "פסטה", "pasta"),
        ("ספגטי", "פסטה", "spaghetti"), ("לזניה", "פסטה", "lasagna"), ("מרק", "מרקים", "soup"),
        ("סלט", "סלטים", "salad"), ("חומוס", "", "hummus"), ("פלאפל", "", "falafel"), ("קוסקוס", "", "couscous"),
        ("מג'דר", "", "lentils rice"), ("עדשים", "", "lentils"), ("אורז", "", "rice"), ("לביבות", "", "fritters"),
        ("פנקייק", "ארוחת בוקר", "pancakes"), ("חביתה", "ארוחת בוקר", "omelette"), ("ביצ", "", "eggs"),
        ("בטטה", "", "sweet potato"), ("דלעת", "", "pumpkin"), ("חציל", "", "eggplant"), ("קישוא", "", "zucchini"),
        ("פטריות", "", "mushrooms"), ("תפוח אדמה", "", "potatoes"), ("תפוז", "", "orange"), ("לימון", "", "lemon"),
        ("בקר", "בשרי", "beef"), ("בשר", "בשרי", "meat")]
RULES = [(r"ילדים|לקטנטנים|תינוק|פעוט", "לילדים"), (r"טבעוני", "טבעוני"),
         (r"להקפיא|הקפאה|במקפיא", "מתאים להקפאה"), (r"\bבתנור|תנור ל|לתנור", "בתנור")]


def auto_tags(r):
    title = r.get("title", "")
    every = " ".join([title, *r.get("ingredients", []), *r.get("steps", []), *r.get("notes", [])])
    tags = [tag for stem, tag, _ in FOOD if tag and stem in title]
    # Meat/chicken/fish count when they're an ingredient too, not just in the title.
    tags += [tag for stem, tag, _ in FOOD if tag in ("בשרי", "עוף", "דגים") and
             any(stem in i for i in r.get("ingredients", []))]
    tags += [tag for pat, tag in RULES if re.search(pat, every)]
    if r.get("total_minutes") and r["total_minutes"] <= 30:
        tags.append("מהיר")
    return list(dict.fromkeys(tags))


PEXELS_KEY = "U8gPRmt7N06ttWpRPmyrzqV5iCXAWFqTIQDcenAyBrAZfHMMXuTKKy2w"  # free key, also public in dira-nuriot


def find_image(title):
    """Illustrative photo from Pexels by English keywords mapped from the Hebrew title. '' on no match/failure."""
    words = [en for stem, _, en in FOOD if stem in title][:2]
    if not words:
        return ""
    url = "https://api.pexels.com/v1/search?per_page=1&orientation=landscape&query=" + \
        urllib.request.quote(" ".join(words) + " food")
    try:
        req = urllib.request.Request(url, headers={"Authorization": PEXELS_KEY, "User-Agent": UA})
        with urllib.request.urlopen(req, timeout=15) as r:
            photos = json.loads(r.read().decode("utf-8")).get("photos") or []
        return photos[0]["src"]["large"] if photos else ""
    except Exception:  # a photo is a nice-to-have; never fail the add over it
        return ""


def enrich(r):
    """Fill what the paste/page didn't say: notes split, time, servings, tags, photo. Never overwrites a value."""
    r.setdefault("notes", [])
    if not r["notes"]:
        r["steps"], r["notes"] = split_notes(r.get("steps", []))
    if not r.get("total_minutes"):
        r["total_minutes"] = guess_minutes(r.get("steps", []))
    if not r.get("servings"):
        m = SERV_RE.search(" ".join([r.get("title", ""), r.get("description", ""), *r.get("steps", [])]))
        r["servings"] = f"{m.group(1)} {m.group(2)}" if m else ""
    r["tags"] = list(dict.fromkeys(r.get("tags", []) + auto_tags(r)))
    if not r.get("image"):
        r["image"] = find_image(r.get("title", ""))
        r["image_auto"] = bool(r["image"])
    return r


def parse_input(raw):
    """Decide URL vs text, then auto-fill the rest. A paste that is basically a link (little other text) is fetched."""
    tags = []
    m = TAGS_RE.search(raw)
    if m:
        tags = [t.strip() for t in re.split(r"[,،]", m.group(1)) if t.strip()]
        raw = TAGS_RE.sub("", raw)
    body = raw.strip()
    url = URL_RE.search(body)
    if url and len(URL_RE.sub("", body).strip()) < 80:
        recipe = from_html(fetch(url.group(0)), url.group(0))
    else:
        recipe = from_text(body)
    recipe["tags"] = list(dict.fromkeys(tags + recipe["tags"]))
    return enrich(recipe)


def slug(title, taken):
    """Readable id that keeps Hebrew letters; suffixes -2, -3 on collision."""
    base = re.sub(r"[^\w]+", "-", title.lower(), flags=re.U).strip("-")[:50] or "recipe"
    sid, n = base, 2
    while sid in taken:
        sid, n = f"{base}-{n}", n + 1
    return sid


def load():
    return json.loads(DATA.read_text(encoding="utf-8")) if DATA.exists() else {"recipes": []}


def add(recipe, data):
    """Append (or replace a recipe with the same source URL) and return the stored record."""
    items = data["recipes"]
    if recipe.get("source_url"):
        old = next((r for r in items if r.get("source_url") == recipe["source_url"]), None)
        if old:
            recipe["id"], recipe["added"] = old["id"], old["added"]
            items[items.index(old)] = recipe
            return recipe
    recipe["id"] = slug(recipe["title"], {r["id"] for r in items})
    recipe["added"] = datetime.date.today().isoformat()
    items.append(recipe)
    return recipe


def _lines(v):
    if isinstance(v, str):
        v = v.splitlines()
    return [str(x).strip() for x in (v or []) if str(x).strip()]


def normalize(r):
    """Coerce a recipe edited in the page into the stored shape (lists of non-empty strings, int minutes)."""
    try:
        mins = int(r.get("total_minutes")) if str(r.get("total_minutes") or "").strip() else None
    except ValueError:
        mins = None
    title = str(r.get("title") or "").strip()
    if not title:
        raise ValueError("חסר שם מתכון")
    return {"title": title, "description": str(r.get("description") or "").strip(),
            "image": str(r.get("image") or "").strip(), "servings": str(r.get("servings") or "").strip(),
            "total_minutes": mins, "ingredients": _lines(r.get("ingredients")), "steps": _lines(r.get("steps")),
            "notes": _lines(r.get("notes")), "image_auto": bool(r.get("image_auto")) and bool(r.get("image")),
            "tags": _lines(r["tags"].split(",") if isinstance(r.get("tags"), str) else r.get("tags")),
            "source_url": str(r.get("source_url") or "").strip()}


def update(recipe, data):
    """Replace the recipe with the same id (edit from the page). Keeps id and 'added'."""
    items = data["recipes"]
    i = next((k for k, r in enumerate(items) if r["id"] == recipe.get("id")), None)
    if i is None:
        raise ValueError(f"מתכון לא נמצא: {recipe.get('id')}")
    items[i] = {**normalize(recipe), "id": items[i]["id"], "added": items[i].get("added")}
    return items[i]


def delete(rid, data):
    before = len(data["recipes"])
    data["recipes"] = [r for r in data["recipes"] if r["id"] != rid]
    if len(data["recipes"]) == before:
        raise ValueError(f"מתכון לא נמצא: {rid}")


def save(data):
    DATA.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    import build_html
    build_html.build()


def apply_issue(title, body, data):
    """Issue → change. Titles: "מתכון: …" add (URL/text), "עריכת מתכון: …" body = recipe JSON,
    "מחיקת מתכון: …" body = recipe id. Returns a Hebrew summary for the issue comment."""
    t = title.strip()
    if t.startswith("מחיקת מתכון"):
        rid = body.strip().splitlines()[0].strip()
        delete(rid, data)
        return f"🗑️ נמחק: {rid}"
    if t.startswith("עריכת מתכון"):
        # The page wraps the JSON in a ```json fence so GitHub shows it readably.
        raw = re.sub(r"^\s*```(?:json)?|```\s*$", "", body.strip())
        rec = update(json.loads(raw), data)
        return f"✏️ עודכן: {rec['title']}"
    rec = add(parse_input(body), data)
    return f"✅ נוסף: {rec['title']} — {len(rec['ingredients'])} מצרכים, {len(rec['steps'])} שלבים (#{rec['id']})"


def main(argv):
    """CLI: <url|text> or '-' adds; '--issue' applies an issue (title in $ISSUE_TITLE, body on stdin)."""
    import os
    for s in (sys.stdout, sys.stderr):
        s.reconfigure(encoding="utf-8")
    if not argv:
        print(__doc__)
        return 2
    if argv == ["--issue"]:
        title, raw = os.environ.get("ISSUE_TITLE", "מתכון"), sys.stdin.read()
    else:
        title, raw = "מתכון", sys.stdin.read() if argv == ["-"] else " ".join(argv)
    data = load()
    try:
        msg = apply_issue(title, raw, data)
    except Exception as e:  # network/parse failures become a readable message for the issue comment
        print(f"❌ לא הצלחתי: {e}")
        return 1
    save(data)
    print(msg)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
