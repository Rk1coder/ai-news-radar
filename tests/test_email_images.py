from datetime import UTC, datetime
from types import SimpleNamespace as N
from unittest.mock import Mock, patch
import pytest
from bs4 import BeautifulSoup

from ai_news_radar.notifications import email_images as images
from ai_news_radar.notifications.email import build_message, preview_html
from ai_news_radar.notifications.email_template import render_html


def story(url='https://blogs.nvidia.com/blog/article/'):
    return N(title_tr='Yeni model yayımlandı', summary_tr='Model erişime açılmıştır.',
             classification_rationale='', sector_tags=['nlp'],
             raw_item=N(title='New model', summary='', url=url, published_at=datetime(2026,10,30),
                        fetched_at=None, source=N(name='nvidia-blog', source_type='company')))


def test_metadata_prefers_og_image_and_resolves_relative_urls():
    html = b'<meta name="twitter:image" content="/fallback.jpg"><meta property="og:image" content="/cover.png"><img src="/advert.jpg">'
    assert images.image_candidates(html, 'https://blogs.nvidia.com/blog/article/') == [
        'https://blogs.nvidia.com/cover.png', 'https://blogs.nvidia.com/fallback.jpg']


@pytest.mark.parametrize('url', ['http://blogs.nvidia.com/a', 'https://127.0.0.1/a',
    'https://blogs.nvidia.com.evil.test/a', 'https://user:password@blogs.nvidia.com/a',
    'https://blogs.nvidia.com:444/a', 'file:///etc/passwd'])
def test_untrusted_urls_never_reach_network(url):
    session=Mock()
    with pytest.raises(ValueError):
        images.fetch_public(session,url,limit=100,deadline=images.monotonic()+10)
    session.get.assert_not_called()


def response(status=200, headers=None, content=b''):
    r=Mock(status_code=status,headers=headers or {})
    r.__enter__=Mock(return_value=r)
    r.__exit__=Mock(return_value=False)
    r.iter_content.return_value=iter([content])
    return r


def test_redirect_to_private_target_is_rejected():
    session=Mock()
    session.get.return_value=response(302,{'Location':'https://127.0.0.1/secret'})
    with patch.object(images,'public_dns',return_value=True),pytest.raises(ValueError):
        images.fetch_public(session,'https://blogs.nvidia.com/a',limit=100,deadline=images.monotonic()+10)
    assert session.get.call_count==1
    assert session.get.call_args.kwargs['allow_redirects'] is False


def test_oversized_response_is_not_downloaded():
    session=Mock()
    r=response(headers={'Content-Length':'101'})
    session.get.return_value=r
    with patch.object(images,'public_dns',return_value=True),pytest.raises(ValueError):
        images.fetch_public(session,'https://blogs.nvidia.com/a',limit=100,deadline=images.monotonic()+10)
    r.iter_content.assert_not_called()


def test_collection_skips_unavailable_and_unsupported_images():
    item=story()
    page=b'<meta property="og:image" content="/cover.svg">'
    def fetch(session, url, **kwargs):
        if url == item.raw_item.url: return page,url,'text/html'
        if url.endswith('cover.svg'): return b'<svg/>',url,'image/svg+xml'
        raise images.requests.HTTPError()
    with patch.object(images,'fetch_public',side_effect=fetch):
        assert images.collect_story_images([item])=={}
    with patch.object(images,'fetch_public',side_effect=images.requests.Timeout):
        assert images.collect_story_images([item])=={}


def test_real_image_is_embedded_once_and_preview_resolves_cid():
    from importlib.resources import files
    png=files('ai_news_radar').joinpath('assets/radar-logo-transparent.png').read_bytes()
    item=story()
    page=b'<meta property="og:image" content="/cover.png">'
    with patch.object(images,'fetch_public',side_effect=[(page,item.raw_item.url,'text/html'),(png,'https://blogs.nvidia.com/cover.png','image/png')]):
        covers=images.collect_story_images([item])
    assert len(covers)==1
    msg=build_message([item],datetime(2026,10,30,tzinfo=UTC),images=covers)
    parts=[p for p in msg.walk() if p.get('Content-ID') and p.get_filename()!='radar-logo.png']
    assert len(parts)==1 and parts[0].get_payload(decode=True)==covers[item.raw_item.url].data
    assert all('@' in p['Content-ID'] for p in msg.walk() if p.get('Content-ID'))
    html=next(p.get_payload(decode=True).decode() for p in msg.walk() if p.get_content_type()=='text/html')
    soup=BeautifulSoup(html,'html.parser')
    assert len(soup.select('img.story-image'))==1
    assert soup.select_one('img.story-image')['src']=='cid:'+parts[0]['Content-ID'][1:-1]
    assert soup.get_text().count(item.title_tr)==1
    assert 'cid:' not in preview_html(msg)
    assert 'data:image/png;base64,' in preview_html(msg)
    without=BeautifulSoup(render_html([item],'30.10.2026'),'html.parser')
    assert not without.select('img.story-image')
    assert item.title_tr in without.get_text()


def raster_bytes(fmt='PNG', size=(64, 64), mode='RGB'):
    from io import BytesIO
    from PIL import Image
    output = BytesIO()
    Image.new(mode, size, (20, 150, 140, 255) if mode == 'RGBA' else (20, 150, 140)).save(output, format=fmt)
    return output.getvalue()


def test_webp_and_ico_are_converted_to_email_safe_rasters():
    from io import BytesIO
    from PIL import Image
    for fmt, kind in [('WEBP','image/webp'), ('ICO','image/x-icon')]:
        data, subtype = images.raster_image(raster_bytes(fmt), kind)
        assert subtype in ('png', 'jpeg')
        assert Image.open(BytesIO(data)).format in ('PNG', 'JPEG')
    with pytest.raises(ValueError):
        images.raster_image(b'<svg/>', 'image/svg+xml')
    with pytest.raises(ValueError):
        images.raster_image(b'not an image', 'image/webp')


def test_oversized_pixel_dimensions_are_rejected_before_loading():
    with patch.object(images, 'MAX_PIXELS', 100), pytest.raises(ValueError):
        images.raster_image(raster_bytes(size=(11, 10)), 'image/png')


def test_large_webp_is_resized_and_alpha_is_preserved():
    from io import BytesIO
    from PIL import Image
    raw = BytesIO()
    Image.new('RGBA', (1800, 900), (0, 100, 100, 100)).save(raw, format='WEBP', lossless=True)
    data, subtype = images.raster_image(raw.getvalue(), 'image/webp')
    with Image.open(BytesIO(data)) as converted:
        assert subtype == 'png'
        assert converted.size == (1200, 600)
        assert converted.getextrema()[3][0] == 100
    assert len(data) <= images.IMAGE_LIMIT


def test_total_embedded_image_budget_is_respected():
    items = [story('https://arxiv.org/abs/1'), story('https://arxiv.org/abs/2')]
    cover = images.StoryImage(b'123456789012', 'png', 'cover')
    with patch.object(images, 'TOTAL_LIMIT', 20), patch.object(images, '_cover', return_value=(cover,b'',items[0].raw_item.url)):
        found = images.collect_story_images(items)
    assert len(found) == 1
    assert sum(len(image.data) for image in found.values()) <= 20


@pytest.mark.parametrize('url', ['https://www.youtube.com/watch?v=abcdefghijk',
    'https://youtu.be/abcdefghijk', 'https://www.youtube.com/shorts/abcdefghijk'])
def test_youtube_thumbnail_is_fetched_without_video_html(url):
    calls = []
    def fetch(session, target, **kwargs):
        calls.append(target)
        return raster_bytes('JPEG'),target,'image/jpeg'
    with patch.object(images,'fetch_public',side_effect=fetch):
        covers = images.collect_story_images([story(url)])
    assert calls == ['https://i.ytimg.com/vi/abcdefghijk/hqdefault.jpg']
    assert covers[url].kind == 'cover'


def test_youtube_lookalike_and_invalid_video_id_are_rejected():
    assert images.youtube_thumbnail('https://youtube.com.evil.test/watch?v=abcdefghijk') is None
    assert images.youtube_thumbnail('https://www.youtube.com/watch?v=../../private') is None


def test_missing_cover_uses_one_shared_source_logo_and_labels_it():
    items = [story('https://arxiv.org/abs/2610.00001'), story('https://arxiv.org/abs/2610.00002')]
    for item in items: item.raw_item.source.name = 'arxiv'
    calls = []
    def fetch(session, url, **kwargs):
        calls.append(url)
        if '/abs/' in url:
            return b'<link rel="apple-touch-icon" href="/icon.png">',url,'text/html'
        if url == 'https://arxiv.org/icon.png': return raster_bytes(),url,'image/png'
        raise images.requests.HTTPError()
    with patch.object(images,'fetch_public',side_effect=fetch):
        covers = images.collect_story_images(items)
    assert len(covers) == 2
    assert calls.count('https://arxiv.org/icon.png') == 1
    assert all(cover.kind == 'source_logo' for cover in covers.values())
    html = render_html(items,'30.10.2026',images=covers)
    assert 'Kaynak logosu: arXiv' in html
    assert 'arXiv haberinin kapak görseli' not in html


def test_no_network_after_budget_and_untrusted_logo_is_ignored():
    with patch.object(images,'fetch_public') as fetch:
        assert images.collect_story_images([story()],budget_seconds=0) == {}
        fetch.assert_not_called()
    assert images.logo_candidates(b'<link rel="icon" href="https://127.0.0.1/private">',
                                 'https://arxiv.org/abs/1') == ['https://arxiv.org/favicon.ico']


def test_publisher_logo_in_og_image_is_not_presented_as_news_photo():
    item = story('http://arxiv.org/abs/2610.00001')
    def fetch(session, url, **kwargs):
        if url == 'https://arxiv.org/abs/2610.00001':
            return b'<meta property="og:image" content="/images/arxiv-logo-fb.png">',url,'text/html'
        return raster_bytes(),url,'image/png'
    with patch.object(images,'fetch_public',side_effect=fetch):
        found = images.collect_story_images([item])
    assert found[item.raw_item.url].kind == 'source_logo'
