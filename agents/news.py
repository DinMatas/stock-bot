"""סוכן חדשות + סנטימנט: כותרות מגוגל חדשות (ופינהאב אם יש מפתח).
מזהה: גל חריג של כתבות, וטון חיובי/שלילי לפי מילים פיננסיות בכותרות.
"""
import datetime as dt, re, urllib.parse
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from . import net
import config

POS = {"beat": 1.5, "beats": 1.5, "surge": 1.2, "surges": 1.2, "soar": 1.2, "soars": 1.2, "jump": 1, "jumps": 1,
       "rally": 1, "rallies": 1, "record": 0.8, "upgrade": 1.5, "upgraded": 1.5, "upgrades": 1.5, "raises": 1, "raised": 1,
       "outperform": 1, "buy": 0.5, "bullish": 1, "growth": 0.5, "profit": 0.5, "approval": 1.2, "approved": 1.2,
       "wins": 1, "win": 0.7, "partnership": 0.7, "deal": 0.5, "strong": 0.7, "higher": 0.5, "gains": 0.7, "buyback": 1,
       "dividend": 0.4, "tops": 1, "exceeds": 1.2, "optimistic": 0.8, "boost": 0.8, "boosts": 0.8}
NEG = {"miss": 1.5, "misses": 1.5, "plunge": 1.3, "plunges": 1.3, "tumble": 1.2, "tumbles": 1.2, "fall": 0.7, "falls": 0.7,
       "drop": 0.8, "drops": 0.8, "slump": 1.1, "downgrade": 1.5, "downgraded": 1.5, "downgrades": 1.5, "cut": 0.8,
       "cuts": 0.8, "lawsuit": 1, "sued": 1, "probe": 1.1, "investigation": 1.1, "recall": 1, "layoffs": 0.7,
       "bearish": 1, "sell": 0.5, "weak": 0.8, "lower": 0.5, "warning": 1, "warns": 1.1, "loss": 0.8, "losses": 0.8,
       "fraud": 1.5, "halt": 1, "delay": 0.7, "delays": 0.7, "fine": 0.6, "fined": 1, "antitrust": 0.8, "bankruptcy": 2,
       "concerns": 0.6, "slashes": 1.1, "underperform": 1, "crash": 1.3, "tariff": 0.5, "tariffs": 0.5}
WORD = re.compile(r"[a-z]+")


def tone(title):
    words = WORD.findall(title.lower())
    return sum(POS.get(w, 0) for w in words) - sum(NEG.get(w, 0) for w in words)


def _google(ticker, name):
    q = urllib.parse.quote(f'"{ticker}" stock when:7d')
    xml = net.get(f"https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en", min_gap=1.0)
    items = []
    for it in ET.fromstring(xml).iter("item"):
        try:
            when = parsedate_to_datetime(it.findtext("pubDate"))
        except Exception:
            continue
        src = it.find("source")
        items.append({"title": it.findtext("title") or "", "link": it.findtext("link") or "",
                      "when": when, "source": src.text if src is not None else ""})
    return items


def _finnhub(ticker):
    today = dt.date.today()
    d = net.get_json(f"https://finnhub.io/api/v1/company-news?symbol={ticker}&from={today - dt.timedelta(days=7)}"
                     f"&to={today}&token={config.FINNHUB_KEY}", min_gap=1.1)
    return [{"title": x.get("headline", ""), "link": x.get("url", ""), "source": x.get("source", ""),
             "when": dt.datetime.fromtimestamp(x["datetime"], dt.timezone.utc)} for x in d if x.get("datetime")]


def analyze(ticker, name=""):
    out = {"ok": False, "score": 0.0, "signals": [], "alert": False, "data": {}, "headlines": []}
    items, errs = [], []
    for fn in ([_google] + ([lambda t, n: _finnhub(t)] if config.FINNHUB_KEY else [])):
        try:
            items += fn(ticker, name)
        except Exception as e:
            errs.append(str(e)[:120])
    if not items:
        out["error"] = "; ".join(errs) or "אין כתבות"
        out["ok"] = not errs
        return out
    # הסרת כפילויות לפי כותרת
    seen, uniq = set(), []
    for it in sorted(items, key=lambda x: x["when"], reverse=True):
        k = it["title"].lower()[:70]
        if k not in seen:
            seen.add(k)
            uniq.append(it)
    now = dt.datetime.now(dt.timezone.utc)
    last24 = [i for i in uniq if now - i["when"] <= dt.timedelta(hours=24)]
    older = [i for i in uniq if dt.timedelta(hours=24) < now - i["when"] <= dt.timedelta(days=7)]
    per_day = len(older) / 6 if older else 0
    tones = [tone(i["title"]) for i in last24]
    avg_tone = sum(tones) / len(tones) if tones else 0
    out["ok"] = True
    out["data"] = {"news_24h": len(last24), "news_per_day": round(per_day, 1), "tone": round(avg_tone, 2)}
    for i in last24[:6]:
        out["headlines"].append({"title": i["title"], "link": i["link"], "source": i["source"], "tone": tone(i["title"])})
    top = out["headlines"][0]["link"] if out["headlines"] else ""

    if len(last24) >= 5 and len(last24) >= 2.5 * max(per_day, 1):
        out["signals"].append({"text": f"גל חריג של כתבות: {len(last24)} ב-24 שעות (רגיל: כ-{per_day:.0f} ביום)",
                               "weight": 0.0, "source": top})
        out["alert"] = True
    if last24 and abs(avg_tone) >= 0.4:
        w = max(-1.5, min(1.5, avg_tone * 1.5))
        txt = "חיובי" if avg_tone > 0 else "שלילי"
        out["signals"].append({"text": f"הטון בכותרות של היממה האחרונה {txt}", "weight": round(w, 2), "source": top})
    out["score"] = sum(s["weight"] for s in out["signals"])
    return out
