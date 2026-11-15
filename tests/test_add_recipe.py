"""Offline tests: JSON-LD and pasted-text parsing, ids, and the HTML build."""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import add_recipe as ar  # noqa: E402
import build_html  # noqa: E402

FIX = ROOT / "tests" / "fixtures"


def test_jsonld_graph_recipe():
    page = (FIX / "recipe_page.html").read_text(encoding="utf-8")
    r = ar.from_html(page, "https://example.com/shakshuka")
    assert r["title"] == "שקשוקה"
    assert r["ingredients"][0] == "6 ביצים"
    assert r["steps"][0] == "בסיס:"           # HowToSection name becomes a header step
    assert "מטגנים בצל" in r["steps"][1]
    assert r["total_minutes"] == 40
    assert r["servings"] == "4"
    assert r["image"] == "https://example.com/s.jpg"
    assert "ארוחת בוקר" in r["tags"]


def test_page_without_recipe_raises():
    try:
        ar.from_html("<html><title>x</title><article><p>just a story.</p></article></html>", "https://example.com")
    except ValueError:
        return
    raise AssertionError("expected ValueError")


def test_text_sections_and_bullets():
    r = ar.from_text("עוגת שוקולד\nעוגה מהירה\nמצרכים:\n- 2 ביצים\n• כוס סוכר\nאופן ההכנה:\n1. מערבבים\n2) אופים 30 דק׳")
    assert r["title"] == "עוגת שוקולד"
    assert r["description"] == "עוגה מהירה"
    assert r["ingredients"] == ["2 ביצים", "כוס סוכר"]
    assert r["steps"] == ["מערבבים", "אופים 30 דק׳"]


def test_text_without_headers_keeps_body_as_steps():
    r = ar.from_text("סלט\nחותכים ירקות\nמתבלים")
    assert r["steps"] == ["חותכים ירקות", "מתבלים"] and r["ingredients"] == []


def test_tags_line_and_url_detection(monkeypatch):
    monkeypatch.setattr(ar, "fetch", lambda url: (FIX / "recipe_page.html").read_text(encoding="utf-8"))
    r = ar.parse_input("https://example.com/shakshuka\n\nתגיות: מהיר, צמחוני")
    assert r["tags"][:2] == ["מהיר", "צמחוני"]
    assert r["source_url"] == "https://example.com/shakshuka"


def test_minutes():
    assert ar.minutes("PT1H30M") == 90
    assert ar.minutes("P0DT45M") == 45
    assert ar.minutes("") is None


def test_add_dedupes_by_url_and_unique_ids():
    data = {"recipes": []}
    a = ar.add({"title": "פסטה", "source_url": "u1", "ingredients": [], "steps": []}, data)
    b = ar.add({"title": "פסטה", "source_url": "", "ingredients": [], "steps": []}, data)
    assert a["id"] == "פסטה" and b["id"] == "פסטה-2"
    ar.add({"title": "פסטה חדשה", "source_url": "u1", "ingredients": ["x"], "steps": []}, data)
    assert len(data["recipes"]) == 2 and data["recipes"][0]["ingredients"] == ["x"]


def test_build_escapes_script_close(tmp_path, monkeypatch):
    (tmp_path / "recipes.json").write_text(json.dumps({"recipes": [{"id": "x", "title": "</script>"}]}),
                                           encoding="utf-8")
    monkeypatch.setattr(build_html, "ROOT", tmp_path)
    out = build_html.build().read_text(encoding="utf-8")
    assert out.count("</script>") == 1


def test_update_keeps_id_and_added_and_normalizes():
    data = {"recipes": [{"id": "a", "title": "x", "added": "2026-11-01", "ingredients": [], "steps": []}]}
    rec = ar.update({"id": "a", "title": " חדש ", "ingredients": "1\n\n2", "tags": "x, y", "total_minutes": "15"}, data)
    assert rec["id"] == "a" and rec["added"] == "2026-11-01" and rec["title"] == "חדש"
    assert rec["ingredients"] == ["1", "2"] and rec["tags"] == ["x", "y"] and rec["total_minutes"] == 15


def test_apply_issue_routes_by_title():
    data = {"recipes": []}
    ar.apply_issue("מתכון: סלט", "סלט\nמצרכים:\nעגבנייה\nאופן ההכנה:\nחותכים", data)
    rid = data["recipes"][0]["id"]
    body = '```json\n{"id": "%s", "title": "סלט ירקות", "steps": ["חותכים"]}\n```' % rid
    assert "עודכן" in ar.apply_issue("עריכת מתכון: סלט", body, data)
    assert data["recipes"][0]["title"] == "סלט ירקות"
    ar.apply_issue("מחיקת מתכון: סלט", rid + "\n", data)
    assert data["recipes"] == []


def test_delete_missing_raises():
    try:
        ar.delete("nope", {"recipes": []})
    except ValueError:
        return
    raise AssertionError("expected ValueError")


import pytest  # noqa: E402


@pytest.fixture(autouse=True)
def _no_photo_lookup(monkeypatch):
    # Keep tests offline: the Pexels lookup is the only network call in enrich().
    monkeypatch.setattr(ar, "find_image", lambda title: "")


KIDS = """קציצות בקר ובטטה לקטנטנים
קציצות רכות ועסיסיות, מושלמות לשלב ההזנה המשלימה ולכל המשפחה, עם ברזל ואבץ מהבקר ומתיקות מהבטטה.
500 גרם בשר בקר טחון
½ כוס מחית בטטה
1 כפית אבקת שום
מחממים תנור ל־180 מעלות.
אופים כ־18–22 דקות, עד שהקציצות עשויות.
מצננים לפני ההגשה.
אחסון והקפאה
במקפיא: עד 3 חודשים."""


def test_headerless_paste_is_classified_and_enriched():
    r = ar.parse_input(KIDS)
    assert r["ingredients"] == ["500 גרם בשר בקר טחון", "½ כוס מחית בטטה", "1 כפית אבקת שום"]
    assert r["steps"][0].startswith("מחממים") and r["steps"][-1] == "מצננים לפני ההגשה."
    assert r["notes"] == ["אחסון והקפאה:", "במקפיא: עד 3 חודשים."]
    assert r["description"].startswith("קציצות רכות")
    assert r["total_minutes"] == 22
    assert {"בשרי", "לילדים", "בתנור", "מתאים להקפאה", "מהיר"} <= set(r["tags"])


def test_guess_minutes_hours_and_ranges():
    assert ar.guess_minutes(["מתפיחים שעה וחצי", "אופים 30-35 דקות", "מצננים"]) == 125
    assert ar.guess_minutes(["מערבבים"]) is None


def test_link_with_a_few_words_is_fetched(monkeypatch):
    monkeypatch.setattr(ar, "fetch", lambda url: (FIX / "recipe_page.html").read_text(encoding="utf-8"))
    r = ar.parse_input("תראי את זה https://example.com/shakshuka")
    assert r["title"] == "שקשוקה" and r["source_url"] == "https://example.com/shakshuka"


def test_blog_post_without_jsonld_takes_first_recipe():
    # Shape of michalwaxman.com: story, title, intro, sub-headed ingredients, steps, then a second recipe.
    story = "<p>" + "סיפור ארוך על החג. " * 20 + "</p>"
    page = ("<html><meta property=\"og:image\" content=\"http://x/a.jpg\"><div class=\"entry-content\">" + story +
            "<p>סירניקי של סבתא</p><p>" + "לביבות גבינה מבושמות. " * 5 + "</p>"
            "<p>ללביבות:<br>500 גרם גבינה<br>3 כפות סוכר<br>1 ביצה</p>"
            "<p>להגשה:<br>שמנת חמוצה</p><p>מערבבים הכל בקערה.</p><p>מטגנים עד הזהבה.</p>"
            "<p>סלט פירות</p>" + story + "<p>1 בננה<br>2 תפוחים</p><p>חותכים.</p></div></html>")
    r = ar.from_html(page, "https://blog.example/p")
    assert r["title"] == "סירניקי של סבתא"
    assert r["ingredients"] == ["ללביבות:", "500 גרם גבינה", "3 כפות סוכר", "1 ביצה", "להגשה:", "שמנת חמוצה"]
    assert r["steps"] == ["מערבבים הכל בקערה.", "מטגנים עד הזהבה."]
    assert r["image"] == "http://x/a.jpg" and r["description"].startswith("לביבות")
