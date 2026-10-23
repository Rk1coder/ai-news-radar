from ai_news_radar.models import RawItem, Source

# Karar 2-A: kaynak turune gore varsayilan guvenilirlik agirligi ve capraz dogrulama gerekliligi.
# Yeni kaynak turleri (savunma, sosyal) eklenirken buraya girdi eklenir.
SOURCE_TYPE_DEFAULTS = {
    "academic": {"credibility_weight": 0.9, "requires_cross_verification": False},
    "company": {"credibility_weight": 0.8, "requires_cross_verification": False},
    "media": {"credibility_weight": 0.75, "requires_cross_verification": False},
    "defense": {"credibility_weight": 0.6, "requires_cross_verification": True},
    "social": {"credibility_weight": 0.3, "requires_cross_verification": True},
}


def verify(raw_item: RawItem, source: Source) -> tuple[bool, str, str]:
    """Karar 2: kaynak turune gore degisen esik.

    Dondurur: (verified, verification_method, notes)
    """
    if not source.requires_cross_verification:
        return True, "rule", f"'{source.source_type}' kaynak turu icin tek kaynak yeterli."

    # Karar 2-B/C henuz devrede degil (MVP tek kaynak turuyle basliyor).
    # Capraz teyit gerektiren bir kaynak turu eklendiginde burada embedding
    # kumeleme ve/veya LLM tabanli dogrulama cagrisi yapilacak.
    return (
        False,
        "pending_cross_verification",
        f"'{source.source_type}' kaynak turu capraz teyit gerektiriyor; "
        "henuz ikinci bagimsiz kaynakla eslesme mantigi (Karar 2-B/C) devreye alinmadi.",
    )
