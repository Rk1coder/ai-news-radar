from ai_news_radar.models import RawItem, Source
from ai_news_radar.verification.rules import verify


def test_academic_source_verified_without_cross_check():
    source = Source(
        name="arxiv", source_type="academic", credibility_weight=0.9,
        requires_cross_verification=False,
    )
    raw_item = RawItem(source_id=1, external_id="x", title="t", url="u", summary="s")
    raw_item.source = source

    verified, method, _ = verify(raw_item, source)

    assert verified is True
    assert method == "rule"


def test_social_source_requires_cross_verification():
    source = Source(
        name="twitter", source_type="social", credibility_weight=0.3,
        requires_cross_verification=True,
    )
    raw_item = RawItem(source_id=1, external_id="x", title="t", url="u", summary="s")
    raw_item.source = source

    verified, method, notes = verify(raw_item, source)

    assert verified is False
    assert method == "pending_cross_verification"
    assert "capraz teyit" in notes
