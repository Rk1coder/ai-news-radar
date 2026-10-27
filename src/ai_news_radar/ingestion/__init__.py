from ai_news_radar.ingestion.arxiv import ArxivConnector
from ai_news_radar.ingestion.base import Connector
from ai_news_radar.ingestion.blogs import DogusBlogConnector, JsonLdBlogConnector, MakeBlogConnector
from ai_news_radar.ingestion.hackernews import HackerNewsConnector
from ai_news_radar.ingestion.huggingface_papers import HuggingFaceDailyPapersConnector
from ai_news_radar.ingestion.rss import MultiRssConnector, RssConnector
from ai_news_radar.ingestion.substack import SubstackTopicsConnector

# Karar 1-A: aktif kaynaklar burada toplanir; cli ve web/app.py bu listeyi paylasir.
# "defense"/"social" turu kaynaklar icin verification/rules.py henuz capraz dogrulama
# yapmadigindan (Karar 2-B/C), bu kaynaklar eklenirse kayitlari pending_cross_verification
# olarak dusup siniflandirmaya girmez - bu beklenen bir davranistir.
def default_connectors() -> list[Connector]:
    return [
        ArxivConnector(),
        RssConnector("huggingface-blog", "https://huggingface.co/blog/feed.xml",
                     max_results=50, lookback_days=4, latest_fallback=1),
        HuggingFaceDailyPapersConnector(),
        SubstackTopicsConnector(),
        RssConnector("openai-news", "https://openai.com/news/rss.xml"),
        RssConnector("deepmind-blog", "https://deepmind.google/blog/rss.xml"),
        RssConnector(
            "techcrunch-ai", "https://techcrunch.com/category/artificial-intelligence/feed/"
        ),
        RssConnector("mit-technology-review", "https://www.technologyreview.com/feed/"),
        RssConnector("nvidia-blog", "https://blogs.nvidia.com/feed/"),
        RssConnector("aws-ml-blog", "https://aws.amazon.com/blogs/machine-learning/feed/"),
        RssConnector("google-ai-blog", "https://blog.google/innovation-and-ai/technology/ai/rss/"),
        RssConnector("ai-weekly", "https://aiweekly.co/rss/", source_type="media", max_results=10),
        RssConnector(
            "smol-ai-news", "https://news.smol.ai/rss.xml", source_type="media", max_results=10
        ),
        RssConnector(
            "theverge-ai",
            "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml",
            source_type="media",
        ),
        RssConnector(
            "arstechnica-ai", "https://arstechnica.com/ai/feed/", source_type="media"
        ),
        RssConnector(
            "wired-ai", "https://www.wired.com/feed/tag/ai/latest/rss", source_type="media"
        ),
        RssConnector("the-decoder", "https://the-decoder.com/feed/", source_type="media"),
        RssConnector(
            "import-ai", "https://importai.substack.com/feed", source_type="media", max_results=10
        ),
        RssConnector(
            "github-transformers",
            "https://github.com/huggingface/transformers/releases.atom",
            max_results=5,
        ),
        RssConnector(
            "github-ollama", "https://github.com/ollama/ollama/releases.atom", max_results=5
        ),
        RssConnector(
            "github-vllm", "https://github.com/vllm-project/vllm/releases.atom", max_results=5
        ),
        RssConnector(
            "github-langchain",
            "https://github.com/langchain-ai/langchain/releases.atom",
            max_results=5,
        ),
        RssConnector(
            "lesswrong", "https://www.lesswrong.com/feed.xml", source_type="social", max_results=10
        ),
        RssConnector(
            "alignment-forum",
            "https://www.alignmentforum.org/feed.xml",
            source_type="social",
            max_results=10,
        ),
        RssConnector(
            "github-llamaindex",
            "https://github.com/run-llama/llama_index/releases.atom",
            max_results=5,
        ),
        RssConnector(
            "github-langgraph",
            "https://github.com/langchain-ai/langgraph/releases.atom",
            max_results=5,
        ),
        RssConnector(
            "github-sd-webui",
            "https://github.com/AUTOMATIC1111/stable-diffusion-webui/releases.atom",
            max_results=5,
        ),
        RssConnector(
            "bens-bites", "https://www.bensbites.com/feed.xml", source_type="media",
            max_results=50, lookback_days=4, latest_fallback=1
        ),
        RssConnector(
            "tldr-ai", "https://tldr.tech/api/rss/ai", source_type="media", max_results=10
        ),
        RssConnector(
            "defensescoop-ai",
            "https://defensescoop.com/tag/artificial-intelligence/feed/",
            source_type="defense",
        ),
        RssConnector(
            "c4isrnet-ai",
            "https://www.c4isrnet.com/artificial-intelligence/feed/",
            source_type="defense",
        ),
        HackerNewsConnector(),
        *automation_and_local_ai_connectors(),
        *youtube_and_community_connectors(),
    ]


def automation_and_local_ai_connectors() -> list[Connector]:
    """Requested sources: rolling four days, or the latest post for quiet blogs.

    Platform feed sizes bound coverage; this is not a complete historical crawl.
    The shared scheduler checks these on every scan (15 minutes by default).
    """
    recent = dict(max_results=50, lookback_days=4, latest_fallback=1)
    return [
        RssConnector('n8n-blog', 'https://blog.n8n.io/rss/', **recent),
        MakeBlogConnector(),
        RssConnector('zapier-blog', 'https://zapier.com/blog/feeds/latest/', **recent),
        RssConnector('the-rundown-ai', 'https://www.therundown.ai/feed', source_type='media', **recent),
        MultiRssConnector('medium-ai-automation', [
            'https://medium.com/feed/tag/artificial-intelligence',
            'https://medium.com/feed/tag/automation',
            'https://medium.com/feed/tag/yapay-zeka',
            'https://medium.com/feed/tag/otomasyon',
        ], source_type='social', **recent),
        RssConnector('dogus-teknoloji-medium', 'https://medium.com/feed/dogus-teknoloji', **recent),
        DogusBlogConnector(),
        JsonLdBlogConnector('atalay-tech', 'https://atalay.tech/blog'),
        RssConnector('ollama-blog', 'https://ollama.com/blog/rss.xml', **recent),
        RssConnector('lm-studio-blog', 'https://lmstudio.ai/rss.xml', **recent),
        RssConnector('civitai-education', 'https://education.civitai.com/feed/', **recent),
        RssConnector('stable-diffusion-art', 'https://stable-diffusion-art.com/feed/', source_type='media', **recent),
        RssConnector('openzeka-blog', 'https://blog.openzeka.com/feed/', **recent),
        RssConnector('masqot-blog', 'https://www.masqot.co/feed/', source_type='media', **recent),
    ]


def youtube_and_community_connectors() -> list[Connector]:
    """Requested sources: YouTube AI kanallari + daha fazla Reddit/forum toplulugu."""
    recent = dict(max_results=50, lookback_days=4, latest_fallback=1)
    reddit = dict(source_type='social', max_results=100, lookback_days=4, latest_fallback=1)
    youtube = 'https://www.youtube.com/feeds/videos.xml?channel_id='
    return [
        RssConnector('yt-two-minute-papers', youtube + 'UCbfYPyITQ-7l4upoX8nvctg',
                     source_type='media', **recent),
        RssConnector('yt-yannic-kilcher', youtube + 'UCZHmQk67mSJgfCCTn7xBfew',
                     source_type='media', **recent),
        RssConnector('yt-ai-explained', youtube + 'UCNJ1Ymd5yFuUPtn21xtRbbw',
                     source_type='media', **recent),
        RssConnector('yt-lex-fridman', youtube + 'UCSHZKyawb77ixDdsGog4iWA',
                     source_type='media', **recent),
        RssConnector('yt-matt-wolfe', youtube + 'UChpleBmo18P08aKCIgti38g',
                     source_type='media', **recent),
        RssConnector('yt-ai-jason', youtube + 'UCrXSVX9a1mj8l0CMLwKgMVw',
                     source_type='media', **recent),
        # Karar: Reddit'in anonim rate limiti IP basina, subreddit basina degil - 7 ayri
        # istek yerine Reddit'in kendi "+" ile coklu subreddit birlestirme ozelligiyle
        # TEK istekte topluyoruz (daha once her subreddit ayri connector'di, hepsi ayni
        # taramada art arda 429/403 aliyordu).
        RssConnector(
            'reddit-ai-communities',
            'https://www.reddit.com/r/LocalLLaMA+MachineLearning+artificial+singularity'
            '+OpenAI+StableDiffusion+ChatGPT/new/.rss?limit=100',
            **reddit,
        ),
        RssConnector('huggingface-forum', 'https://discuss.huggingface.co/latest.rss',
                     source_type='social', **recent),
        RssConnector('openai-community-forum', 'https://community.openai.com/latest.rss',
                     source_type='social', **recent),
    ]


def active_connectors(session) -> list[Connector]:
    """Karar: default_connectors()'tan kullanicinin kapattigi kaynaklari cikarir,
    ekledigi ozel RSS kaynaklarini ekler. scans.py burayi default_connectors() yerine cagirir."""
    from ai_news_radar.models import CustomSource, SourceToggle

    disabled = {row.source_name for row in session.query(SourceToggle).filter_by(enabled=False)}
    connectors = [c for c in default_connectors() if c.source_name not in disabled]
    connectors += [
        RssConnector(cs.name, cs.feed_url, cs.source_type)
        for cs in session.query(CustomSource).filter_by(enabled=True)
    ]
    return connectors
