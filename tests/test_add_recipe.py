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
        ar.from_html("<html><title>x</title></html>", "https://example.com")
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
