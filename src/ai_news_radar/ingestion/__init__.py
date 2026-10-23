from ai_news_radar.ingestion.arxiv import ArxivConnector
from ai_news_radar.ingestion.base import Connector
from ai_news_radar.ingestion.hackernews import HackerNewsConnector
from ai_news_radar.ingestion.rss import RssConnector

# Karar 1-A: aktif kaynaklar burada toplanir; cli ve web/app.py bu listeyi paylasir.
# "defense"/"social" turu kaynaklar icin verification/rules.py henuz capraz dogrulama
# yapmadigindan (Karar 2-B/C), bu kaynaklar eklenirse kayitlari pending_cross_verification
# olarak dusup siniflandirmaya girmez - bu beklenen bir davranistir.
def default_connectors() -> list[Connector]:
    return [
        ArxivConnector(),
        RssConnector("huggingface-blog", "https://huggingface.co/blog/feed.xml"),
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
            "github-llama-cpp", "https://github.com/ggml-org/llama.cpp/releases.atom", max_results=5
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
            "bens-bites", "https://www.bensbites.com/feed.xml", source_type="media", max_results=10
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
    ]
