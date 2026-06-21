import pytz
from datetime import datetime

_TZ = pytz.timezone("Asia/Tashkent")

def today():
    """Toshkent vaqtidagi bugungi sana (server UTC bo'lsa ham to'g'ri ishlaydi)."""
    return datetime.now(_TZ).date()
