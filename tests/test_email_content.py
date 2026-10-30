from datetime import datetime

from bs4 import BeautifulSoup

from ai_news_radar.models import Development, RawItem, Source
from ai_news_radar.notifications.email_template import render_html, render_text


def story(title, *, source="publisher", kind="company", url="https://example.com/news", summary="Kısa açıklama.", tags=()):
    return Development(title_tr=title, summary_tr=summary, verified=True,
                       classification_rationale="", sector_tags=list(tags),
                       raw_item=RawItem(title=title, summary=summary, url=url,
                                        published_at=datetime(2026, 10, 28, 10),
                                        source=Source(name=source, source_type=kind)))


def test_topics_keep_each_story_once_in_html_and_text_and_hide_empty_topics():
    items = [story("Açık ağırlıklı LLM yerel çalışıyor", tags=["nlp"]),
             story("Protein çalışması", source="arxiv", kind="academic"),
             story("Yeni kod editörü yayınlandı"), story("Şirket yatırım aldı")]
    for rendered in (BeautifulSoup(render_html(items, "28.10.2026"), "html.parser").get_text(" "),
                     render_text(items, "28.10.2026")):
        for title in ("LLM & Yerel Modeller", "Araştırma", "Araçlar & Uygulamalar", "Diğer gelişmeler"):
            assert title in rendered
        for item in items:
            assert rendered.count(item.title_tr) == 1
    html = render_html([items[1]], "28.10.2026")
    assert "LLM &amp; Yerel Modeller" not in html
    assert "Araçlar &amp; Uygulamalar" not in html
    assert "Diğer gelişmeler" not in html


def test_research_source_has_priority_over_incidental_llm_keywords():
    html = render_html([story("LLM reasoning research", kind="academic", tags=["nlp"])], "28.10.2026")
    soup = BeautifulSoup(html, "html.parser")
    assert [h.get_text() for h in soup.find_all("h2")] == ["Araştırma"]


def test_funding_news_is_not_a_tool_just_because_it_has_a_software_tag():
    item = story("Acme 3 milyar dolar yatırım aldı", tags=["general_software"])
    soup = BeautifulSoup(render_html([item], "28.10.2026"), "html.parser")
    assert [h.get_text() for h in soup.find_all("h2")] == ["Diğer gelişmeler"]


def test_available_project_gets_try_today_highlight_without_duplicating_article():
    item = story("LocalKit yayınlandı", url="https://github.com/team/localkit")
    for rendered in (BeautifulSoup(render_html([item], "28.10.2026"), "html.parser").get_text(" "),
                     render_text([item], "28.10.2026")):
        assert "Bugün denenebilecekler" in rendered
        assert rendered.count("LocalKit yayınlandı") == 1
    assert 'href="https://github.com/team/localkit"' in render_html([item], "28.10.2026")


def test_unavailable_and_non_project_pages_are_not_recommended():
    for url, title, summary in [
        ("https://github.com/team/tool", "Yeni araç yakında geliyor", "Henüz kullanıma açılmadı."),
        ("https://github.com/team/tool/issues/1", "Tool hatası", "Güvenlik açığı bulundu."),
        ("https://huggingface.co/blog/model", "Yeni model", "Araştırma duyurusu."),
        ("javascript:alert(1)", "Araç yayınlandı", "İndirilebilir."),
        ("https://example.com/launch", "Yeni araç yayınlandı", "Yakında kullanıma açılacak."),
    ]:
        item = story(title, url=url, summary=summary)
        assert "Bugün denenebilecekler" not in render_html([item], "28.10.2026")
        assert "Bugün denenebilecekler" not in render_text([item], "28.10.2026")


def test_official_tool_release_can_be_recommended_but_not_waitlisted():
    item = story("n8n 3.0 Tanıtılıyor", source="n8n-blog", url="https://blog.n8n.io/introducing-n8n-v3/",
                 summary="Yeni sürüm artık kullanılabilir. İş akışı otomasyonu için yeni özellikler.")
    assert "Bugün denenebilecekler" in render_text([item], "28.10.2026")
    item.summary_tr = "Yeni sürüm için bekleme listesine katılın."
    assert "Bugün denenebilecekler" not in render_text([item], "28.10.2026")


def test_official_release_with_correct_turkish_spelling_is_recommended():
    item = story("n8n 3.0 beta sürümü yayımlandı", source="n8n-blog",
                 url="https://blog.n8n.io/introducing-n8n-v3/",
                 summary="Kararlılık ve güvenlik odaklı değişiklikler açıklandı.")
    assert "Bugün denenebilecekler" in render_text([item], "28.10.2026")


def test_reading_time_grows_with_visible_content_in_both_alternatives():
    short = [story("Kısa haber")]
    long = [story(f"Araştırma {i}", kind="academic", summary="kelime " * 150) for i in range(8)]
    assert "Yaklaşık 1 dakika" in render_text(short, "28.10.2026")
    assert "Yaklaşık 7 dakika" in render_text(long, "28.10.2026")
    assert "Yaklaşık 7 dakika" in render_html(long, "28.10.2026")
    for rendered in (render_html([], "28.10.2026"), render_text([], "28.10.2026")):
        assert "Yaklaşık" not in rendered
        assert "Bugün denenebilecekler" not in rendered
        assert "bulunamadı" in rendered


def test_only_one_project_is_highlighted_and_model_link_stays_in_llm_section():
    items = [story("TinyLM açık model", url="https://huggingface.co/team/tinylm", tags=["nlp"]),
             story("LocalKit yayınlandı", url="https://github.com/team/localkit")]
    html = render_html(items, "28.10.2026")
    soup = BeautifulSoup(html, "html.parser")
    assert soup.get_text().count("Bugün denenebilecekler") == 1
    assert "LLM & Yerel Modeller" in soup.get_text()
    assert soup.get_text().count("TinyLM açık model") == 1
