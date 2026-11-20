"""הגדרות הבוט. פה משנים את רשימת המניות ואת הספים."""
import os

# רשימת המניות למעקב (סימול: שם בעברית/קצר)
WATCHLIST = {
    "AAPL": "אפל",
    "MSFT": "מיקרוסופט",
    "NVDA": "אנבידיה",
    "AMZN": "אמזון",
    "GOOGL": "גוגל (אלפאבית)",
    "META": "מטא (פייסבוק)",
    "TSLA": "טסלה",
    "AMD": "AMD",
    "NFLX": "נטפליקס",
    "JPM": "ג'יי.פי מורגן",
    "XOM": "אקסון מוביל",
    "KO": "קוקה קולה",
    "PLTR": "פלנטיר",
    "INTC": "אינטל",
    "TEVA": "טבע",
    "ANT": "אנתרופיק",
}

# זיהוי מול ה-SEC (רשות ניירות הערך האמריקאית). הכללים שלהם דורשים שם + מייל ליצירת קשר.
# כדאי לשים פה מייל אמיתי שלך (לא מתפרסם בשום מקום, נשלח רק ל-SEC).
SEC_USER_AGENT = os.environ.get("SEC_USER_AGENT", "MatasStockWatch personal-research stockbot@example.com")

# מפתחות חינמיים (לא חובה). אם קיימים, הבוט משתמש בהם כגיבוי למחירים/חדשות.
TIINGO_KEY = os.environ.get("TIINGO_KEY", "")
FINNHUB_KEY = os.environ.get("FINNHUB_KEY", "")

# ספים
VOLUME_SPIKE = 2.0        # מחזור מסחר פי 2 מהממוצע = חריג
BIG_MOVE_PCT = 4.0        # תזוזה יומית של 4%+ = חריג
ALERT_SCORE = 2.5         # מאיזה ציון (חיובי/שלילי) מסמנים "שווה לבדוק"
HORIZONS = [1, 5]         # בודקים כל תחזית אחרי יום מסחר אחד ואחרי 5
NEUTRAL_BAND_PCT = 1.0    # תזוזה קטנה מ-1% נחשבת "ניטרלי" בבדיקת הדיוק

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(HERE, "data")
OUT_DIR = os.path.join(HERE, "docs")  # docs/ = התיקייה שגיטהאב מציג כאתר

# מעקב "תחתית": מניה -> מאיזה תאריך מסתכלים. מתריעים כשיש סימן שהירידה נעצרה או שמונה מנכ"ל.
WATCH_BOTTOM = {"NVDA": "2026-11-12"}
