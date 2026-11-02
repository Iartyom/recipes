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
    tags += [clean(t) for t in (kws if isinstance(kws, list) else str(kws).split(","))][:5]
    return {
        "title": clean(rec.get("name")) or _meta(page, "og:title") or url,
        "description": clean(rec.get("description")),
        "image": _image(rec.get("image")) or _meta(page, "og:image"),
        "servings": clean(yld) if yld else "",
        "total_minutes": minutes(rec.get("totalTime")) or (
            (minutes(rec.get("prepTime")) or 0) + (minutes(rec.get("cookTime")) or 0)) or None,
        "ingredients": [clean(i) for i in rec.get("recipeIngredient") or [] if clean(i)],
        "steps": _steps(rec.get("recipeInstructions")),
        "tags": [t for t in dict.fromkeys(tags) if t],
        "source_url": url,
    }


def from_text(text):
    """Parse pasted text: first line = title; sections start at ingredient/step headers."""
    lines = [ln.strip() for ln in text.splitlines()]
    lines = [ln for ln in lines if ln]
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
    # No headers at all: treat the body as steps rather than losing it in the description.
    if not ings and not steps:
        steps, desc = desc, []
    src = URL_RE.search(text)
    return {"title": BULLET.sub("", title), "description": " ".join(desc), "image": "", "servings": "",
            "total_minutes": None, "ingredients": ings, "steps": steps, "tags": [],
            "source_url": src.group(0) if src else ""}


def parse_input(raw):
    """Decide URL vs text. Input that is just a URL (plus optional tags line) is fetched."""
    tags = []
    m = TAGS_RE.search(raw)
    if m:
        tags = [t.strip() for t in re.split(r"[,،]", m.group(1)) if t.strip()]
        raw = TAGS_RE.sub("", raw)
    body = raw.strip()
    if URL_RE.fullmatch(body):
        recipe = from_html(fetch(body), body)
    else:
        recipe = from_text(body)
    recipe["tags"] = list(dict.fromkeys(tags + recipe["tags"]))
    return recipe


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


def main(argv):
    for s in (sys.stdout, sys.stderr):
        s.reconfigure(encoding="utf-8")
    if not argv:
        print(__doc__)
        return 2
    raw = sys.stdin.read() if argv == ["-"] else " ".join(argv)
    try:
        recipe = parse_input(raw)
    except Exception as e:  # network/parse failures become a readable message for the issue comment
        print(f"❌ לא הצלחתי להוסיף: {e}")
        return 1
    data = load()
    rec = add(recipe, data)
    DATA.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    import build_html
    build_html.build()
    print(f"✅ נוסף: {rec['title']} — {len(rec['ingredients'])} מצרכים, {len(rec['steps'])} שלבים (#{rec['id']})")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
