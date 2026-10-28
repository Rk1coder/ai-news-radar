"""Daily scan rules shared by settings and scheduling."""
import re

from ai_news_radar.config import SCAN_HOURS

CADENCES = (5, 10, 15, 20, 30, 60)
_TIME = re.compile(r"(?:[01][0-9]|2[0-3]):[0-5][0-9]")


def default_program() -> dict:
    return {"times": [f"{hour:02d}:00" for hour in sorted(set(SCAN_HOURS))], "windows": []}


def normalize_program(value) -> dict:
    """Validate before any settings are mutated; return a fresh canonical value."""
    if not isinstance(value, dict) or set(value) != {"times", "windows"}:
        raise ValueError("Program, tarama saatleri ve zaman aralıkları içermeli.")
    times, windows = value["times"], value["windows"]
    if not isinstance(times, list) or len(times) > 48:
        raise ValueError("En fazla 48 tarama saati ekleyebilirsin.")
    if not isinstance(windows, list) or len(windows) > 12:
        raise ValueError("En fazla 12 zaman aralığı ekleyebilirsin.")

    def valid_time(time):
        return isinstance(time, str) and _TIME.fullmatch(time) is not None

    if not all(valid_time(time) for time in times):
        raise ValueError("Tarama saatlerini 00:00–23:59 arasında seç.")
    normalized_windows = set()
    for window in windows:
        if not isinstance(window, dict) or set(window) != {"start", "end", "interval_minutes"}:
            raise ValueError("Her aralık için başlangıç, bitiş ve tekrar süresi gerekli.")
        start, end, cadence = window["start"], window["end"], window["interval_minutes"]
        if not valid_time(start) or not valid_time(end):
            raise ValueError("Başlangıç ve bitiş saatlerini 00:00–23:59 arasında seç.")
        if start == end:
            raise ValueError("Başlangıç ve bitiş saatleri aynı olamaz.")
        if type(cadence) is not int or cadence not in CADENCES:
            raise ValueError("Tekrar süresi 5, 10, 15, 20, 30 veya 60 dakika olmalı.")
        normalized_windows.add((start, end, cadence))
    return {
        "times": sorted(set(times)),
        "windows": [{"start": start, "end": end, "interval_minutes": cadence}
                    for start, end, cadence in sorted(normalized_windows)],
    }


def program_minutes(program: dict) -> list[int]:
    def minute(time):
        hour, minute = map(int, time.split(":"))
        return hour * 60 + minute

    minutes = {minute(time) for time in program["times"]}
    for window in program["windows"]:
        start, end = minute(window["start"]), minute(window["end"])
        if end < start:
            end += 1440
        minutes.update(offset % 1440 for offset in range(start, end + 1, window["interval_minutes"]))
    return sorted(minutes)
