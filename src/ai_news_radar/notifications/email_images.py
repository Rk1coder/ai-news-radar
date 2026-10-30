"""Best-effort publisher cover images, embedded in the email rather than hotlinked."""
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
from io import BytesIO
from ipaddress import ip_address
import logging
import re
import socket
from time import monotonic
from urllib.parse import parse_qs, urljoin, urlsplit, urlunsplit

from bs4 import BeautifulSoup
import requests
from PIL import Image, ImageOps, UnidentifiedImageError

log = logging.getLogger(__name__)
# Exact publisher/CDN hosts, never arbitrary hosts supplied in article metadata.
ARTICLE_HOSTS = frozenset('''blogs.nvidia.com deepmind.google arstechnica.com
www.masqot.co masqot.co techcrunch.com aws.amazon.com www.theverge.com the-decoder.com
blog.n8n.io openai.com huggingface.co blog.google www.technologyreview.com www.wired.com
ollama.com lmstudio.ai github.com www.youtube.com youtube.com m.youtube.com youtu.be
arxiv.org export.arxiv.org www.therundown.ai news.smol.ai aiweekly.co www.bensbites.com
importai.substack.com tldr.tech blog.langchain.com blog.langchain.dev
www.anthropic.com anthropic.com mistral.ai www.mistral.ai cohere.com
www.marktechpost.com venturebeat.com www.infoq.com'''.split())
IMAGE_HOSTS = ARTICLE_HOSTS | frozenset('''lh3.googleusercontent.com lh4.googleusercontent.com
lh5.googleusercontent.com lh6.googleusercontent.com new.masqot.co platform.theverge.com
cdn.vox-cdn.com d2908q01vomqb2.cloudfront.net storage.ghost.io images.nvidia.com
images.ctfassets.net images.openai.com cdn.openai.com opengraph.githubassets.com
i.ytimg.com media.wired.com cdn.arstechnica.net static.arxiv.org
github.githubassets.com avatars.githubusercontent.com raw.githubusercontent.com
cdn-uploads.huggingface.co cdn.sanity.io substackcdn.com substack-post-media.s3.amazonaws.com
cdn.prod.website-files.com framerusercontent.com images.unsplash.com'''.split())
PAGE_LIMIT = 1_500_000
IMAGE_LIMIT = 900_000
DOWNLOAD_LIMIT = 2_000_000
MAX_PIXELS = 16_000_000
TOTAL_LIMIT = 4_000_000


@dataclass(frozen=True)
class StoryImage:
    data: bytes
    subtype: str
    cid: str
    kind: str = 'cover'


def _allowed(url, hosts):
    try:
        p = urlsplit(url)
        return (p.scheme == 'https' and p.hostname in hosts and p.port in (None,443)
                and not p.username and not p.password)
    except ValueError:
        return False


def public_dns(host):
    addresses = socket.getaddrinfo(host,443,type=socket.SOCK_STREAM)
    return bool(addresses) and all(ip_address(row[4][0]).is_global for row in addresses)


def fetch_public(session, url, *, limit, deadline):
    """Bounded HTTPS fetch. Validate every redirect; no ambient proxy/credentials."""
    for _ in range(4):
        remaining = deadline - monotonic()
        if remaining <= 0 or not _allowed(url, IMAGE_HOSTS):
            raise ValueError('Unsupported image source or elapsed budget')
        if not public_dns(urlsplit(url).hostname):
            raise ValueError('Non-public address')
        with session.get(url,stream=True,allow_redirects=False,
                         timeout=(min(3,remaining),min(4,remaining))) as response:
            if response.status_code in (301,302,303,307,308):
                url = urljoin(url,response.headers.get('Location',''))
                continue
            response.raise_for_status()
            if int(response.headers.get('Content-Length',0)) > limit:
                raise ValueError('Image/page too large')
            chunks, size = [], 0
            for chunk in response.iter_content(16_384):
                size += len(chunk)
                if size > limit or monotonic() > deadline:
                    raise ValueError('Image/page budget exceeded')
                chunks.append(chunk)
            return b''.join(chunks), url, response.headers.get('Content-Type','').split(';')[0].lower()
    raise ValueError('Too many redirects')


def image_candidates(html, page_url):
    soup = BeautifulSoup(html,'html.parser')
    urls = []
    for key in ('og:image:secure_url','og:image','og:image:url','twitter:image','twitter:image:src'):
        for tag in soup.find_all('meta'):
            if (tag.get('property') or tag.get('name','')).lower() == key:
                url = urljoin(page_url, tag.get('content','').strip())
                if url not in urls and _allowed(url, IMAGE_HOSTS):
                    urls.append(url)
    return urls[:3]


def raster_image(data, content_type):
    """Decode bounded raster formats; WebP/ICO become PNG or JPEG for inboxes."""
    if content_type not in ('image/png', 'image/jpeg', 'image/jpg', 'image/webp',
                            'image/x-icon', 'image/vnd.microsoft.icon', 'application/octet-stream'):
        raise ValueError('Unsupported image type')
    try:
        with Image.open(BytesIO(data)) as original:
            if original.format not in ('PNG', 'JPEG', 'WEBP', 'ICO'):
                raise ValueError('Unsupported raster format')
            if original.width * original.height > MAX_PIXELS:
                raise ValueError('Image dimensions too large')
            original.seek(0)
            original.load()
            if original.format in ('PNG', 'JPEG') and max(original.size) <= 1600 and len(data) <= IMAGE_LIMIT:
                return data, original.format.lower()
            image = ImageOps.exif_transpose(original).convert('RGBA')
            image.thumbnail((1200, 1200), Image.Resampling.LANCZOS)
            output = BytesIO()
            if image.getextrema()[3][0] < 255:
                image.save(output, format='PNG', optimize=True)
                if output.tell() <= IMAGE_LIMIT:
                    return output.getvalue(), 'png'
            background = Image.new('RGB', image.size, 'white')
            background.paste(image, mask=image.getchannel('A'))
            for quality in (85, 65, 45):
                output = BytesIO()
                background.save(output, format='JPEG', quality=quality, optimize=True)
                if output.tell() <= IMAGE_LIMIT:
                    return output.getvalue(), 'jpeg'
    except (UnidentifiedImageError, Image.DecompressionBombError, OSError) as exc:
        raise ValueError('Invalid raster image') from exc
    raise ValueError('Converted image too large')


def youtube_thumbnail(url):
    if not _allowed(url, ARTICLE_HOSTS):
        return None
    p = urlsplit(url)
    if p.hostname == 'youtu.be':
        video_id = p.path.strip('/')
    elif p.hostname in ('youtube.com', 'www.youtube.com', 'm.youtube.com'):
        if p.path == '/watch':
            video_id = parse_qs(p.query).get('v', [''])[0]
        elif p.path.startswith(('/shorts/', '/live/', '/embed/')):
            video_id = p.path.split('/')[2]
        else:
            return None
    else:
        return None
    return f'https://i.ytimg.com/vi/{video_id}/hqdefault.jpg' if re.fullmatch(r'[\w-]{11}', video_id, re.ASCII) else None


def logo_candidates(html, page_url):
    soup = BeautifulSoup(html, 'html.parser')
    urls = []
    for rel in ('apple-touch-icon', 'icon', 'shortcut'):
        for tag in soup.find_all('link'):
            if rel in tag.get('rel', []):
                target = urljoin(page_url, tag.get('href', ''))
                if _allowed(target, IMAGE_HOSTS) and target not in urls and not urlsplit(target).path.lower().endswith('.svg'):
                    urls.append(target)
    fallback = urljoin(page_url, '/favicon.ico')
    if _allowed(fallback, IMAGE_HOSTS) and fallback not in urls:
        urls.append(fallback)
    return urls[:4]


def _session():
    session = requests.Session()
    session.trust_env = False
    session.headers.update({'User-Agent': 'Mozilla/5.0 (compatible; ai-news-radar/0.1)',
                            'Accept': 'text/html,image/webp,image/jpeg,image/png;q=0.9'})
    return session


def _download_image(session, candidates, deadline, *, kind='cover'):
    for candidate in candidates:
        if monotonic() >= deadline:
            break
        try:
            data, _, content_type = fetch_public(session, candidate, limit=DOWNLOAD_LIMIT, deadline=deadline)
            data, subtype = raster_image(data, content_type)
            cid = 'radar-image-' + sha256(data).hexdigest()[:20]
            # Some publishers (notably arXiv) put their site logo in og:image.
            # Do not describe that generic branding as an article cover.
            filename = urlsplit(candidate).path.rsplit('/', 1)[-1].lower()
            image_kind = 'source_logo' if re.search(r'(^|[-_.])(logo|favicon)([-_.]|$)', filename) else kind
            return StoryImage(data, subtype, cid, image_kind)
        except (requests.RequestException, OSError, ValueError):
            continue
    return None


def _cover(url, deadline):
    page, final_url = b'', url
    deadline = min(deadline, monotonic() + 6)
    if monotonic() >= deadline:
        return None, page, final_url
    with _session() as session:
        thumbnail = youtube_thumbnail(url)
        if thumbnail:
            return _download_image(session, [thumbnail], deadline), page, final_url
        try:
            page, final_url, kind = fetch_public(session, url, limit=PAGE_LIMIT, deadline=deadline)
            if kind in ('text/html', 'application/xhtml+xml'):
                return _download_image(session, image_candidates(page, final_url), deadline), page, final_url
        except (requests.RequestException, OSError, ValueError):
            log.debug('Cover unavailable for %s', urlsplit(url).hostname)
    return None, page, final_url


def _logo(page, url, deadline):
    with _session() as session:
        return _download_image(session, logo_candidates(page, url), min(deadline, monotonic()+5), kind='source_logo')


def collect_story_images(stories, *, budget_seconds=25):
    """Four workers share a bounded cover phase; reserve time for source logos."""
    found, total, deadline = {}, 0, monotonic() + budget_seconds
    urls = {}
    for story in stories[:12]:
        original = story.raw_item.url
        try:
            parsed = urlsplit(original)
            # Older arXiv RSS entries use HTTP; fetch only their HTTPS equivalent.
            canonical = urlunsplit(parsed._replace(scheme='https')) if parsed.scheme == 'http' and parsed.hostname in ('arxiv.org','export.arxiv.org') else original
            if _allowed(canonical, ARTICLE_HOSTS):
                urls[original] = canonical
        except ValueError:
            continue
    if budget_seconds <= 0 or not urls:
        return found
    cover_deadline = deadline - min(5, budget_seconds/3)
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {url: pool.submit(_cover, target, cover_deadline) for url, target in urls.items()}
        missing, logo_pages = {}, {}
        for url, future in futures.items():
            cover, page, final_url = future.result()
            if cover and total + len(cover.data) <= TOTAL_LIMIT:
                found[url] = cover
                total += len(cover.data)
            elif not cover:
                host = urlsplit(final_url).hostname
                missing[url] = host
                if host not in logo_pages or page:
                    logo_pages[host] = (page, final_url)
        logos = {host: pool.submit(_logo, page, url, deadline) for host, (page, url) in logo_pages.items()}
        for url, host in missing.items():
            logo = logos[host].result()
            if logo and total + len(logo.data) <= TOTAL_LIMIT:
                found[url] = logo
                total += len(logo.data)
    return found
