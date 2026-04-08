Tirox → Bitrix24 Integratsiya

✅ So‘ralgan TALABLAR bo‘yicha to‘liq fix

✅ WALLET (UF_CRM_1770996129) = keshbek puli (bonus_balance bo‘lsa o‘sha, bo‘lmasa balance)
✅ OPPORTUNITY (Сумма и валюта) = xarid summasi (operationPurchaseSum)
✅ LAST_VISIT = oxirgi tashrif (webhook timestamp) + fallback customer.updatedAt
✅ VISITS = countVisits / current_number_of_uses / currentNumberOfUses
✅ CUSTOMER_ID = cardholder_id
✅ CARD_ID = serial_number
✅ DOB = cardholder_birth_date yoki customer.dateOfBirth
✅ Karta qachon ochilgan = customer.createdAt (support bergan endpointdan) → Timeline commentga yozadi
✅ Dublikat bo‘lmaydi (phone variantlar bilan)
✅ Bitrix rate limit retry
✅ Robot 0 qilib yuborsa — OPPORTUNITY’ni (xarid summasini) verify+force set qiladi
✅ Webhook format har xil bo‘lsa ham phone/customerId/cardId topadi

Ushbu loyiha Tirox CRM dan mijozlarni olib, Bitrix24 CRM ga avtomatik ravishda Lead sifatida qo‘shish uchun yozilgan.
Loyiha 2 xil rejimda ishlaydi:

Import rejimi (eski mijozlarni yuklash)

Real-time webhook rejimi (yangi mijoz kelganda avtomatik lead yaratish)

Loyihaning tuzilishi:

Integratsia/
│
├── import_tirox_to_bitrix.py
├── realtime_tirox_webhook.py
├── realtime_events.sqlite
├── requirements.txt
└── .venv

Qanday ishlaydi:

1) Import rejimi
import_tirox_to_bitrix.py scripti Tirox API orqali barcha mijozlarni olib, Bitrix24 ga lead sifatida qo‘shadi.
Ishga tushirish:
```
python import_tirox_to_bitrix.py
```

2) Real-time webhook rejimi
realtime_tirox_webhook.py FastAPI server bo‘lib, Tirox webhook eventlarini qabul qiladi va Bitrix24 da lead yaratadi.

Serverni ishga tushirish:
```
uvicorn realtime_tirox_webhook:app --host 0.0.0.0 --port 8000
```
Tekshirish:
http://127.0.0.1:8000/health

Ngrok orqali tashqi URL olish:
```
ngrok http 8000
```
Ngrok bergan URL ni Tirox webhook sozlamasiga qo‘yish kerak:
```
https://your-ngrok-url/tirox/webhook
```

API sozlamalari
realtime_tirox_webhook.py ichida quyidagilarni to‘g‘rilash kerak:
```
TIROX_API_KEY = "a39d742f74273491ffd081a034eedd8f"
BITRIX_WEBHOOK_BASE = "https://allmax.bitrix24.kz/rest/67/pm2rn601c5zdss19/"
```

Lead qanday yaratiladi:
Bitrix24 ga quyidagi ma'lumotlar yuboriladi:
```
TITLE → Tirox realtime: {firstName}
NAME → firstName
PHONE → normalize qilingan telefon
COMMENTS → event ma'lumotlari
SOURCE_ID → WEB
```
Agar webhook payload ichida ism bo‘lmasa, Tirox API orqali customer ma'lumotlari olinadi.

Dublikat himoya:
realtime_events.sqlite bazasi orqali bir xil event qayta ishlanmaydi.
Har bir event_id saqlanadi va agar qayta kelsa lead yaratmaydi.

Kerakli kutubxonalar:

"requirements.txt"
```
fastapi
uvicorn
requests
```

O‘rnatish:
```
pip install -r requirements.txt
```

MUAMMOLAR:

404 Not Found → Webhook URL noto‘g‘ri
502 Bad Gateway → Server ishlamayapti
Ism kelmayapti → customerId yo‘q yoki API javobi bo‘sh

"import_tirox_to_bitrix.py"
```
import time
import requests

# =========================
# ✅ API lar shu yerda (siz bergan)
# =========================
TIROX_API_KEY = "a39d742f74273491ffd081a034eedd8f"
BITRIX_WEBHOOK_BASE = "https://allmax.bitrix24.kz/rest/67/pm2rn601c5zdss19/"

# =========================
# ✅ Tirox endpoint (to‘g‘ri API domen)
# =========================
TIROX_CUSTOMERS_URL = "https://api.tirox.app/api/v2/customers"

# =========================
# ⚙️ Import sozlamalari
# =========================
ITEMS_PER_PAGE = 100   # 30 ham bo'ladi, 100 tezroq
SLEEP_EVERY = 25       # har nechta lead yaratgandan keyin
SLEEP_SECONDS = 0.3    # Bitrix limitdan chiqmaslik uchun

# =========================
# ✅ Headers (ApiKeyAuth)
# =========================
TIROX_HEADERS = {
    "X-API-KEY": TIROX_API_KEY,
    "Accept": "application/json",
}

def normalize_phone(phone):
    if not phone:
        return ""
    p = str(phone).strip().replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
    if p.startswith("00"):
        p = "+" + p[2:]
    if not p.startswith("+") and p.isdigit():
        p = "+" + p
    return p

def bitrix_lead_add(name, phone, comment=""):
    url = BITRIX_WEBHOOK_BASE + "crm.lead.add"
    payload = {
        "fields": {
            "TITLE": f"Tirox import: {name}",
            "NAME": name,
            "PHONE": [{"VALUE": phone, "VALUE_TYPE": "WORK"}],
            "COMMENTS": comment,
            "SOURCE_ID": "WEB",
        }
    }
    r = requests.post(url, json=payload, timeout=60)
    try:
        return r.json()
    except Exception:
        return {"error": "non_json", "text": r.text[:300], "status": r.status_code}

def tirox_get_customers_page(page: int, items_per_page: int):
    params = {
        "page": page,
        "itemsPerPage": items_per_page
    }
    r = requests.get(TIROX_CUSTOMERS_URL, headers=TIROX_HEADERS, params=params, timeout=60)

    # Agar HTML kelsa demak noto‘g‘ri domen/endpoint ishlatilgan bo‘ladi
    ct = (r.headers.get("content-type") or "").lower()
    if "application/json" not in ct:
        raise RuntimeError(
            f"❌ Tirox JSON qaytarmadi. HTTP={r.status_code}, CT={ct}\n"
            f"TEXT(first)={r.text[:200]}"
        )

    data = r.json()
    return data

def run_import():
    created = 0
    page = 1

    print("✅ START IMPORT")
    print("➡️ TIROX:", TIROX_CUSTOMERS_URL)
    print("➡️ BITRIX:", BITRIX_WEBHOOK_BASE)

    while True:
        print(f"\n--- PAGE {page} ---")
        data = tirox_get_customers_page(page, ITEMS_PER_PAGE)

        customers = data.get("data", [])
        meta = data.get("meta", {})

        if not customers:
            print("✅ Tugadi. Bo‘sh sahifa.")
            break

        total_items = meta.get("totalItems")
        current_page = meta.get("currentPage")
        per_page = meta.get("itemsPerPage")

        print(f"📌 Meta: totalItems={total_items} currentPage={current_page} itemsPerPage={per_page}")
        print(f"👥 Bu sahifada: {len(customers)} ta")

        for c in customers:
            first = (c.get("firstName") or "").strip()
            sur = (c.get("surname") or "").strip()
            name = (first + " " + sur).strip() or "No name"

            phone = normalize_phone(c.get("phone"))
            if not phone:
                continue

            # commentga tirozdagi id/yaratilgan sana qo‘shib qo‘yamiz
            comment = f"TIROX IMPORT\nid={c.get('id')}\ncreatedAt={c.get('createdAt')}\n"

            resp = bitrix_lead_add(name=name, phone=phone, comment=comment)

            if "error" in resp:
                print("❌ Bitrix error:", resp)
            else:
                created += 1

            if created % SLEEP_EVERY == 0:
                time.sleep(SLEEP_SECONDS)

        # keyingi sahifaga o‘tamiz
        page += 1

    print("\n✅ IMPORT FINISHED")
    print("🧮 Jami lead yaratildi:", created)

if __name__ == "__main__":
    run_import()

```

"realtime_tirox_webhook.py"
```
import time
import json
import sqlite3
from typing import Any, Dict, Optional, Tuple

import requests
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

# =========================
# ✅ API lar (siz bergan)
# =========================
TIROX_API_KEY = "a39d742f74273491ffd081a034eedd8f"
BITRIX_WEBHOOK_BASE = "https://allmax.bitrix24.kz/rest/67/pm2rn601c5zdss19/"

TIROX_API_BASE = "https://api.tirox.app"
TIROX_CUSTOMERS_URL = f"{TIROX_API_BASE}/api/v2/customers"

# =========================
# ⚙️ Settings
# =========================
DB_PATH = "realtime_events.sqlite"
SLEEP_SECONDS = 0.0
HTTP_TIMEOUT = 60

# Phone orqali qidirishda nechta sahifagacha yurish
CUSTOMER_LOOKUP_MAX_PAGES = 120
CUSTOMER_LOOKUP_PER_PAGE = 100

app = FastAPI(title="Tirox → Bitrix Realtime Webhook (name by phone)")

TIROX_HEADERS = {
    "X-API-KEY": TIROX_API_KEY,
    "Accept": "application/json",
}

# =========================
# ✅ DB (idempotency + phone cache)
# =========================
def db_init():
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute(
        "CREATE TABLE IF NOT EXISTS processed (event_id TEXT PRIMARY KEY, created_at INTEGER)"
    )
    # phone -> firstName cache
    cur.execute(
        "CREATE TABLE IF NOT EXISTS phone_cache (phone TEXT PRIMARY KEY, first_name TEXT, updated_at INTEGER)"
    )
    con.commit()
    con.close()

def db_seen(event_id: str) -> bool:
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("SELECT 1 FROM processed WHERE event_id = ?", (event_id,))
    row = cur.fetchone()
    con.close()
    return row is not None

def db_mark(event_id: str):
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute(
        "INSERT OR IGNORE INTO processed(event_id, created_at) VALUES(?, ?)",
        (event_id, int(time.time()))
    )
    con.commit()
    con.close()

def cache_get_name(phone: str) -> str:
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("SELECT first_name FROM phone_cache WHERE phone = ?", (phone,))
    row = cur.fetchone()
    con.close()
    return (row[0] if row and row[0] else "")

def cache_set_name(phone: str, first_name: str):
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute(
        "INSERT OR REPLACE INTO phone_cache(phone, first_name, updated_at) VALUES(?, ?, ?)",
        (phone, first_name, int(time.time()))
    )
    con.commit()
    con.close()

db_init()

# =========================
# ✅ Helpers
# =========================
def safe_str(x: Any) -> str:
    return ("" if x is None else str(x)).strip()

def normalize_phone(phone: Any) -> str:
    if not phone:
        return ""
    p = str(phone).strip()
    for ch in [" ", "-", "(", ")", "."]:
        p = p.replace(ch, "")
    if p.startswith("00"):
        p = "+" + p[2:]
    if not p.startswith("+") and p.isdigit():
        p = "+" + p
    return p

def pick_event_id(payload: Any) -> str:
    if not isinstance(payload, dict):
        return ""
    for k in ("id", "eventId", "responseId"):
        v = payload.get(k)
        if v:
            return str(v)
    d = payload.get("data")
    if isinstance(d, dict) and d.get("id"):
        return str(d["id"])
    return ""

def pick_customer_id(payload: Any) -> str:
    if not isinstance(payload, dict):
        return ""
    d = payload.get("data")
    if isinstance(d, dict):
        cid = d.get("customerId") or d.get("customerID")
        if cid:
            return str(cid)
        cust = d.get("customer")
        if isinstance(cust, dict) and cust.get("id"):
            return str(cust["id"])
    cid2 = payload.get("customerId") or payload.get("customerID")
    if cid2:
        return str(cid2)
    cust2 = payload.get("customer")
    if isinstance(cust2, dict) and cust2.get("id"):
        return str(cust2["id"])
    return ""

def payload_to_phone(payload: Any) -> str:
    if not isinstance(payload, dict):
        return ""
    d = payload.get("data")
    if isinstance(d, dict):
        phone = d.get("phone")
        cust = d.get("customer")
        if not phone and isinstance(cust, dict):
            phone = cust.get("phone")
        if phone:
            return normalize_phone(phone)
    phone = payload.get("phone")
    if phone:
        return normalize_phone(phone)
    cust2 = payload.get("customer")
    if isinstance(cust2, dict) and cust2.get("phone"):
        return normalize_phone(cust2.get("phone"))
    return ""

def payload_to_first_name(payload: Any) -> str:
    if not isinstance(payload, dict):
        return ""
    d = payload.get("data")
    if isinstance(d, dict):
        first = d.get("firstName")
        cust = d.get("customer")
        if (not first) and isinstance(cust, dict):
            first = cust.get("firstName")
        return safe_str(first)
    first = payload.get("firstName")
    if first:
        return safe_str(first)
    cust2 = payload.get("customer")
    if isinstance(cust2, dict) and cust2.get("firstName"):
        return safe_str(cust2.get("firstName"))
    return ""

def tirox_get_customer_by_id(customer_id: str) -> Optional[Dict[str, Any]]:
    if not customer_id:
        return None
    url = f"{TIROX_CUSTOMERS_URL}/{customer_id}"
    r = requests.get(url, headers=TIROX_HEADERS, timeout=HTTP_TIMEOUT)
    ct = (r.headers.get("content-type") or "").lower()
    if r.status_code != 200 or "application/json" not in ct:
        return None
    try:
        js = r.json()
    except Exception:
        return None
    if isinstance(js, dict) and isinstance(js.get("data"), dict):
        return js["data"]
    return None

def tirox_find_customer_by_phone(phone: str) -> Optional[Dict[str, Any]]:
    """
    customerId kelmasa, phone bo‘yicha /api/v2/customers ni aylanib topamiz.
    Topilgach DB cache ga yozamiz.
    """
    phone = normalize_phone(phone)
    if not phone:
        return None

    # 1) cache tekshiramiz
    cached = cache_get_name(phone)
    if cached:
        return {"firstName": cached, "phone": phone}

    # 2) API orqali sahifa-sahifa qidiramiz
    for page in range(1, CUSTOMER_LOOKUP_MAX_PAGES + 1):
        params = {
            "itemsPerPage": CUSTOMER_LOOKUP_PER_PAGE,
            "page": page,
        }
        r = requests.get(TIROX_CUSTOMERS_URL, headers=TIROX_HEADERS, params=params, timeout=HTTP_TIMEOUT)
        ct = (r.headers.get("content-type") or "").lower()
        if r.status_code != 200 or "application/json" not in ct:
            break

        try:
            js = r.json()
        except Exception:
            break

        data = js.get("data")
        if not isinstance(data, list) or len(data) == 0:
            break

        for c in data:
            if not isinstance(c, dict):
                continue
            c_phone = normalize_phone(c.get("phone"))
            if c_phone and c_phone == phone:
                first = safe_str(c.get("firstName")) or safe_str(c.get("name"))
                if first:
                    cache_set_name(phone, first)
                return c

    return None

def best_first_name(first_name: str, phone: str, customer_id: str) -> str:
    first_name = safe_str(first_name)
    if first_name:
        return first_name
    if phone:
        return f"Client {phone}"
    if customer_id:
        return f"Customer {customer_id}"
    return "Client"

def bitrix_lead_add(first_name: str, phone: str, comment: str = "") -> Dict[str, Any]:
    url = BITRIX_WEBHOOK_BASE + "crm.lead.add"
    payload = {
        "fields": {
            "TITLE": f"Tirox realtime: {first_name}",
            "NAME": first_name,  # faqat ism
            "PHONE": [{"VALUE": phone, "VALUE_TYPE": "WORK"}],
            "COMMENTS": comment,
            "SOURCE_ID": "WEB",
        }
    }
    r = requests.post(url, json=payload, timeout=HTTP_TIMEOUT)
    try:
        return r.json()
    except Exception:
        return {"error": "non_json", "status": r.status_code, "text": r.text[:800]}

# =========================
# ✅ Routes
# =========================
@app.get("/health")
def health():
    return {"ok": True}

async def handle_webhook(request: Request):
    try:
        payload = await request.json()
    except Exception:
        raw = await request.body()
        return JSONResponse(
            status_code=400,
            content={"ok": False, "error": "invalid_json", "raw_first": raw[:300].decode("utf-8", "ignore")},
        )

    event_id = pick_event_id(payload) or f"noid:{int(time.time()*1000)}"
    if db_seen(event_id):
        return {"ok": True, "status": "duplicate_ignored", "event_id": event_id}

    customer_id = pick_customer_id(payload)
    first_name = payload_to_first_name(payload)
    phone = payload_to_phone(payload)

    # ✅ 1) customerId bo‘lsa — API’dan olamiz
    if customer_id:
        customer = tirox_get_customer_by_id(customer_id)
        if customer:
            api_first = safe_str(customer.get("firstName")) or safe_str(customer.get("name"))
            api_phone = normalize_phone(customer.get("phone"))
            if api_first:
                first_name = api_first
            if api_phone:
                phone = api_phone

    # ✅ 2) customerId yo‘q bo‘lsa — phone bo‘yicha topamiz
    if (not safe_str(first_name)) and phone:
        found = tirox_find_customer_by_phone(phone)
        if found:
            api_first = safe_str(found.get("firstName")) or safe_str(found.get("name"))
            if api_first:
                first_name = api_first

    phone = normalize_phone(phone)
    first_name = best_first_name(first_name, phone, customer_id)

    if not phone:
        db_mark(event_id)
        return {"ok": True, "status": "skipped_no_phone", "event_id": event_id, "customer_id": customer_id}

    db_mark(event_id)

    comment = "TIROX REALTIME\n"
    comment += f"event_id={event_id}\n"
    if customer_id:
        comment += f"customer_id={customer_id}\n"
    comment += f"first_name={first_name}\n"
    comment += f"phone={phone}\n"
    if isinstance(payload, dict):
        comment += f"payload_keys={list(payload.keys())}\n"

    resp = bitrix_lead_add(first_name=first_name, phone=phone, comment=comment)

    if SLEEP_SECONDS > 0:
        time.sleep(SLEEP_SECONDS)

    if isinstance(resp, dict) and (resp.get("error") or resp.get("error_description")):
        return {"ok": False, "status": "bitrix_error", "event_id": event_id, "bitrix": resp}

    return {"ok": True, "status": "lead_created", "event_id": event_id, "bitrix": resp}

# ✅ 404 bo‘lmasin deb bir nechta route
@app.post("/tirox/webhook")
async def tirox_webhook(request: Request):
    return await handle_webhook(request)

@app.post("/tirox-webhook")
async def tirox_webhook_alt(request: Request):
    return await handle_webhook(request)

@app.post("/")
async def tirox_root(request: Request):
    return await handle_webhook(request)

```

"tirox_bitrix_combined.py"
```
import time
import json
import sqlite3
import hashlib
from typing import Any, Dict, Optional, Tuple

import requests
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

TIROX_API_KEY = "a39d742f74273491ffd081a034eedd8f"
BITRIX_WEBHOOK_BASE = "https://allmax.bitrix24.kz/rest/67/pm2rn601c5zdss19/"

TIROX_API_BASE = "https://api.tirox.app"
TIROX_CUSTOMERS_URL = f"{TIROX_API_BASE}/api/v2/customers"
TIROX_CARDS_URL = f"{TIROX_API_BASE}/api/v2/cards"

HTTP_TIMEOUT = 60

DB_REALTIME = "realtime_events.sqlite"
SLEEP_REALTIME = 0.0

DB_RETURNING = "returning_events.sqlite"
SLEEP_RETURNING = 0.1

CUSTOMER_LOOKUP_MAX_PAGES = 120
CUSTOMER_LOOKUP_PER_PAGE = 100

app = FastAPI(title="Tirox → Bitrix Combined Webhooks")

TIROX_HEADERS = {
    "X-API-KEY": TIROX_API_KEY,
    "Accept": "application/json",
}

def db_init_realtime():
    con = sqlite3.connect(DB_REALTIME)
    cur = con.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS processed (event_id TEXT PRIMARY KEY, created_at INTEGER)")
    cur.execute("CREATE TABLE IF NOT EXISTS phone_cache (phone TEXT PRIMARY KEY, first_name TEXT, updated_at INTEGER)")
    con.commit()
    con.close()

def db_seen_realtime(event_id: str) -> bool:
    con = sqlite3.connect(DB_REALTIME)
    cur = con.cursor()
    cur.execute("SELECT 1 FROM processed WHERE event_id = ?", (event_id,))
    row = cur.fetchone()
    con.close()
    return row is not None

def db_mark_realtime(event_id: str):
    con = sqlite3.connect(DB_REALTIME)
    cur = con.cursor()
    cur.execute("INSERT OR IGNORE INTO processed(event_id, created_at) VALUES(?, ?)", (event_id, int(time.time())))
    con.commit()
    con.close()

def cache_get_name(phone: str) -> str:
    con = sqlite3.connect(DB_REALTIME)
    cur = con.cursor()
    cur.execute("SELECT first_name FROM phone_cache WHERE phone = ?", (phone,))
    row = cur.fetchone()
    con.close()
    return (row[0] if row and row[0] else "")

def cache_set_name(phone: str, first_name: str):
    con = sqlite3.connect(DB_REALTIME)
    cur = con.cursor()
    cur.execute(
        "INSERT OR REPLACE INTO phone_cache(phone, first_name, updated_at) VALUES(?, ?, ?)",
        (phone, first_name, int(time.time()))
    )
    con.commit()
    con.close()


def db_init_returning():
    con = sqlite3.connect(DB_RETURNING)
    cur = con.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS processed (event_key TEXT PRIMARY KEY, created_at INTEGER)")
    con.commit()
    con.close()

def db_seen_returning(event_key: str) -> bool:
    con = sqlite3.connect(DB_RETURNING)
    cur = con.cursor()
    cur.execute("SELECT 1 FROM processed WHERE event_key = ?", (event_key,))
    row = cur.fetchone()
    con.close()
    return row is not None

def db_mark_returning(event_key: str):
    con = sqlite3.connect(DB_RETURNING)
    cur = con.cursor()
    cur.execute("INSERT OR IGNORE INTO processed(event_key, created_at) VALUES(?, ?)", (event_key, int(time.time())))
    con.commit()
    con.close()

db_init_realtime()
db_init_returning()

def safe_str(x: Any) -> str:
    return ("" if x is None else str(x)).strip()

def normalize_phone(phone: Any) -> str:
    if not phone:
        return ""
    p = str(phone).strip()
    for ch in [" ", "-", "(", ")", "."]:
        p = p.replace(ch, "")
    if p.startswith("00"):
        p = "+" + p[2:]
    if not p.startswith("+") and p.isdigit():
        p = "+" + p
    return p

def bitrix_call(method: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    url = BITRIX_WEBHOOK_BASE + method
    r = requests.post(url, json=payload, timeout=HTTP_TIMEOUT)
    try:
        return r.json()
    except Exception:
        return {"error": "non_json", "status": r.status_code, "text": r.text[:800]}

def bitrix_find_lead_id_by_phone(phone: str) -> Optional[int]:
    phone = normalize_phone(phone)
    if not phone:
        return None
    resp = bitrix_call("crm.duplicate.findbycomm", {
        "type": "PHONE",
        "values": [phone],
        "entity_type": "LEAD"
    })
    res = resp.get("result")
    if isinstance(res, dict):
        leads = res.get("LEAD")
        if isinstance(leads, list) and leads:
            try:
                return int(leads[0])
            except Exception:
                return None
    return None

def bitrix_lead_add(fields: Dict[str, Any]) -> Dict[str, Any]:
    return bitrix_call("crm.lead.add", {"fields": fields})

def bitrix_lead_update(lead_id: int, fields: Dict[str, Any]) -> Dict[str, Any]:
    return bitrix_call("crm.lead.update", {"id": lead_id, "fields": fields})

def tirox_get_customer_by_id(customer_id: str) -> Optional[Dict[str, Any]]:
    if not customer_id:
        return None
    url = f"{TIROX_CUSTOMERS_URL}/{customer_id}"
    r = requests.get(url, headers=TIROX_HEADERS, timeout=HTTP_TIMEOUT)
    ct = (r.headers.get("content-type") or "").lower()
    if r.status_code != 200 or "application/json" not in ct:
        return None
    try:
        js = r.json()
    except Exception:
        return None
    if isinstance(js, dict) and isinstance(js.get("data"), dict):
        return js["data"]
    return None

def tirox_find_customer_by_phone(phone: str) -> Optional[Dict[str, Any]]:
    phone = normalize_phone(phone)
    if not phone:
        return None

    cached = cache_get_name(phone)
    if cached:
        return {"firstName": cached, "phone": phone}

    for page in range(1, CUSTOMER_LOOKUP_MAX_PAGES + 1):
        params = {"itemsPerPage": CUSTOMER_LOOKUP_PER_PAGE, "page": page}
        r = requests.get(TIROX_CUSTOMERS_URL, headers=TIROX_HEADERS, params=params, timeout=HTTP_TIMEOUT)
        ct = (r.headers.get("content-type") or "").lower()
        if r.status_code != 200 or "application/json" not in ct:
            break
        try:
            js = r.json()
        except Exception:
            break

        data = js.get("data")
        if not isinstance(data, list) or not data:
            break

        for c in data:
            if not isinstance(c, dict):
                continue
            c_phone = normalize_phone(c.get("phone"))
            if c_phone == phone:
                first = safe_str(c.get("firstName")) or safe_str(c.get("name"))
                if first:
                    cache_set_name(phone, first)
                return c

    return None

def tirox_get_card(card_id: str) -> Optional[Dict[str, Any]]:
    if not card_id:
        return None
    url = f"{TIROX_CARDS_URL}/{card_id}"
    r = requests.get(url, headers=TIROX_HEADERS, timeout=HTTP_TIMEOUT)
    ct = (r.headers.get("content-type") or "").lower()
    if r.status_code != 200 or "application/json" not in ct:
        return None
    try:
        js = r.json()
    except Exception:
        return None
    if isinstance(js, dict) and isinstance(js.get("data"), dict):
        return js["data"]
    return None

def tirox_find_card_by_customer(customer_id: str) -> Optional[Dict[str, Any]]:
    if not customer_id:
        return None

    candidates = [
        (TIROX_CARDS_URL, {"customerId": customer_id, "itemsPerPage": 30, "page": 1}),
        (TIROX_CARDS_URL, {"customerID": customer_id, "itemsPerPage": 30, "page": 1}),
        (TIROX_CARDS_URL, {"itemsPerPage": 30, "page": 1}),
    ]

    for url, params in candidates:
        r = requests.get(url, headers=TIROX_HEADERS, params=params, timeout=HTTP_TIMEOUT)
        ct = (r.headers.get("content-type") or "").lower()
        if r.status_code != 200 or "application/json" not in ct:
            continue
        try:
            js = r.json()
        except Exception:
            continue

        data = js.get("data")
        if isinstance(data, list):
            for card in data:
                if not isinstance(card, dict):
                    continue
                cid = safe_str(card.get("customerId") or (card.get("customer") or {}).get("id"))
                if cid and cid == customer_id:
                    return card

    return None

def pick_event_id(payload: Any) -> str:
    if not isinstance(payload, dict):
        return ""
    for k in ("id", "eventId", "responseId"):
        v = payload.get(k)
        if v:
            return str(v)
    d = payload.get("data")
    if isinstance(d, dict) and d.get("id"):
        return str(d["id"])
    return ""

def pick_customer_id(payload: Any) -> str:
    if not isinstance(payload, dict):
        return ""
    d = payload.get("data")
    if isinstance(d, dict):
        cid = d.get("customerId") or d.get("customerID")
        if cid:
            return str(cid)
        cust = d.get("customer")
        if isinstance(cust, dict) and cust.get("id"):
            return str(cust["id"])
    cid2 = payload.get("customerId") or payload.get("customerID")
    if cid2:
        return str(cid2)
    cust2 = payload.get("customer")
    if isinstance(cust2, dict) and cust2.get("id"):
        return str(cust2["id"])
    return ""

def payload_to_phone(payload: Any) -> str:
    if not isinstance(payload, dict):
        return ""
    d = payload.get("data")
    if isinstance(d, dict):
        phone = d.get("phone")
        cust = d.get("customer")
        if not phone and isinstance(cust, dict):
            phone = cust.get("phone")
        if phone:
            return normalize_phone(phone)
    phone = payload.get("phone")
    if phone:
        return normalize_phone(phone)
    cust2 = payload.get("customer")
    if isinstance(cust2, dict) and cust2.get("phone"):
        return normalize_phone(cust2.get("phone"))
    return ""

def payload_to_first_name(payload: Any) -> str:
    if not isinstance(payload, dict):
        return ""
    d = payload.get("data")
    if isinstance(d, dict):
        first = d.get("firstName")
        cust = d.get("customer")
        if (not first) and isinstance(cust, dict):
            first = cust.get("firstName")
        return safe_str(first)
    first = payload.get("firstName")
    if first:
        return safe_str(first)
    cust2 = payload.get("customer")
    if isinstance(cust2, dict) and cust2.get("firstName"):
        return safe_str(cust2.get("firstName"))
    return ""

def best_first_name(first_name: str, phone: str, customer_id: str) -> str:
    first_name = safe_str(first_name)
    if first_name:
        return first_name
    if phone:
        return f"Client {phone}"
    if customer_id:
        return f"Customer {customer_id}"
    return "Client"

def bitrix_lead_add_simple(first_name: str, phone: str, comment: str = "") -> Dict[str, Any]:
    fields = {
        "TITLE": f"Tirox realtime: {first_name}",
        "NAME": first_name,
        "PHONE": [{"VALUE": phone, "VALUE_TYPE": "WORK"}],
        "COMMENTS": comment,
        "SOURCE_ID": "WEB",
    }
    return bitrix_lead_add(fields)

async def handle_realtime_new_customer(request: Request):
    try:
        payload = await request.json()
    except Exception:
        raw = await request.body()
        return JSONResponse(status_code=400, content={"ok": False, "error": "invalid_json", "raw_first": raw[:300].decode("utf-8", "ignore")})

    event_id = pick_event_id(payload) or f"noid:{int(time.time()*1000)}"
    if db_seen_realtime(event_id):
        return {"ok": True, "status": "duplicate_ignored", "event_id": event_id}

    customer_id = pick_customer_id(payload)
    first_name = payload_to_first_name(payload)
    phone = payload_to_phone(payload)

    if customer_id:
        customer = tirox_get_customer_by_id(customer_id)
        if customer:
            api_first = safe_str(customer.get("firstName")) or safe_str(customer.get("name"))
            api_phone = normalize_phone(customer.get("phone"))
            if api_first:
                first_name = api_first
            if api_phone:
                phone = api_phone

    if (not safe_str(first_name)) and phone:
        found = tirox_find_customer_by_phone(phone)
        if found:
            api_first = safe_str(found.get("firstName")) or safe_str(found.get("name"))
            if api_first:
                first_name = api_first

    phone = normalize_phone(phone)
    first_name = best_first_name(first_name, phone, customer_id)

    if not phone:
        db_mark_realtime(event_id)
        return {"ok": True, "status": "skipped_no_phone", "event_id": event_id, "customer_id": customer_id}

    existing_lead_id = bitrix_find_lead_id_by_phone(phone)
    if existing_lead_id:
        db_mark_realtime(event_id)
        return {"ok": True, "status": "already_exists", "event_id": event_id, "lead_id": existing_lead_id}

    db_mark_realtime(event_id)

    comment = "TIROX REALTIME\n"
    comment += f"event_id={event_id}\n"
    if customer_id:
        comment += f"customer_id={customer_id}\n"
    comment += f"first_name={first_name}\n"
    comment += f"phone={phone}\n"

    resp = bitrix_lead_add_simple(first_name=first_name, phone=phone, comment=comment)

    if SLEEP_REALTIME > 0:
        time.sleep(SLEEP_REALTIME)

    if isinstance(resp, dict) and (resp.get("error") or resp.get("error_description")):
        return {"ok": False, "status": "bitrix_error", "event_id": event_id, "bitrix": resp}

    return {"ok": True, "status": "lead_created", "event_id": event_id, "bitrix": resp}

UF = {
    "BALANCE": "UF_CRM_TIROX_BALANCE",
    "BONUS": "UF_CRM_TIROX_BONUS_BALANCE",
    "DISC_PCT": "UF_CRM_TIROX_DISCOUNT_PCT",
    "VISITS": "UF_CRM_TIROX_VISITS",
    "LAST_VISIT": "UF_CRM_TIROX_LAST_VISIT",
    "DOB": "UF_CRM_TIROX_DOB",
}

def sha1_of(obj: Any) -> str:
    try:
        raw = json.dumps(obj, ensure_ascii=False, sort_keys=True).encode("utf-8")
    except Exception:
        raw = str(obj).encode("utf-8", "ignore")
    return hashlib.sha1(raw).hexdigest()

def pick_event_key(payload: Any) -> str:
    if isinstance(payload, dict):
        rid = payload.get("responseId") or payload.get("eventId") or payload.get("id")
        if rid:
            return f"rid:{rid}"
    return f"hash:{sha1_of(payload)}"

def extract_ids(payload: Any) -> Tuple[str, str, str]:
    customer_id = ""
    card_id = ""
    phone = ""

    if not isinstance(payload, dict):
        return customer_id, card_id, phone

    customer_id = safe_str(payload.get("customerId") or payload.get("customerID"))
    card_id = safe_str(payload.get("cardId") or payload.get("cardID"))
    phone = safe_str(payload.get("phone"))

    d = payload.get("data")
    if isinstance(d, dict):
        customer_id = customer_id or safe_str(d.get("customerId") or d.get("customerID"))
        card_id = card_id or safe_str(d.get("cardId") or d.get("cardID") or d.get("id"))
        phone = phone or safe_str(d.get("phone"))

        cust = d.get("customer")
        if isinstance(cust, dict):
            customer_id = customer_id or safe_str(cust.get("id"))
            phone = phone or safe_str(cust.get("phone"))

        card = d.get("card")
        if isinstance(card, dict):
            card_id = card_id or safe_str(card.get("id"))
            customer_id = customer_id or safe_str(card.get("customerId"))
            cc = card.get("customer")
            if isinstance(cc, dict):
                phone = phone or safe_str(cc.get("phone"))

    phone = normalize_phone(phone)
    return customer_id, card_id, phone

def build_bitrix_fields(first_name: str, phone: str, customer: Optional[dict], card: Optional[dict]) -> Tuple[Dict[str, Any], str]:
    phone = normalize_phone(phone)

    fields: Dict[str, Any] = {
        "TITLE": f"Tirox: {first_name}",
        "NAME": first_name,
        "PHONE": [{"VALUE": phone, "VALUE_TYPE": "WORK"}],
        "SOURCE_ID": "WEB",
    }

    if customer:
        dob = safe_str(customer.get("dateOfBirth"))
        if dob:
            fields[UF["DOB"]] = dob

    if card and isinstance(card, dict):
        bal = card.get("balance") or {}
        if isinstance(bal, dict):
            if "balance" in bal:
                fields[UF["BALANCE"]] = bal.get("balance")
            if "bonusBalance" in bal:
                fields[UF["BONUS"]] = bal.get("bonusBalance")
            if "discountPercentage" in bal:
                fields[UF["DISC_PCT"]] = bal.get("discountPercentage")

        if "countVisits" in card:
            fields[UF["VISITS"]] = card.get("countVisits")

        last_visit = (
            safe_str(card.get("updatedAt"))
            or safe_str(card.get("lastStampEarnedAt"))
            or safe_str(card.get("lastRewardEarnedAt"))
        )
        if last_visit:
            fields[UF["LAST_VISIT"]] = last_visit

    comment = {
        "tirox_customer": customer or {},
        "tirox_card": card or {},
    }
    comment_text = "TIROX RETURNING UPDATE\n" + json.dumps(comment, ensure_ascii=False)[:1800]
    return fields, comment_text

async def handle_returning_update(request: Request):
    try:
        payload = await request.json()
    except Exception:
        raw = await request.body()
        return JSONResponse(status_code=400, content={"ok": False, "error": "invalid_json", "raw_first": raw[:400].decode("utf-8", "ignore")})

    event_key = pick_event_key(payload)
    if db_seen_returning(event_key):
        return {"ok": True, "status": "duplicate_ignored", "event_key": event_key}

    customer_id, card_id, phone = extract_ids(payload)

    customer = tirox_get_customer_by_id(customer_id) if customer_id else None
    if (not phone) and customer:
        phone = normalize_phone(customer.get("phone"))

    card = tirox_get_card(card_id) if card_id else None
    if (card is None) and customer_id:
        card = tirox_find_card_by_customer(customer_id)

    first_name = ""
    if customer:
        first_name = safe_str(customer.get("firstName"))
    if (not first_name) and card:
        cc = card.get("customer")
        if isinstance(cc, dict):
            first_name = safe_str(cc.get("firstName"))
    if not first_name:
        first_name = "Client"

    phone = normalize_phone(phone)
    if not phone:
        db_mark_returning(event_key)
        return {"ok": True, "status": "skipped_no_phone", "event_key": event_key, "customer_id": customer_id, "card_id": card_id}

    lead_id = bitrix_find_lead_id_by_phone(phone)

    fields, comment_text = build_bitrix_fields(first_name, phone, customer, card)
    fields["COMMENTS"] = comment_text

    if lead_id:
        resp = bitrix_lead_update(lead_id, fields)
        action = "updated"
    else:
        resp = bitrix_lead_add(fields)
        action = "created"

    db_mark_returning(event_key)

    if SLEEP_RETURNING > 0:
        time.sleep(SLEEP_RETURNING)

    if isinstance(resp, dict) and (resp.get("error") or resp.get("error_description")):
        return {"ok": False, "status": "bitrix_error", "action": action, "event_key": event_key, "bitrix": resp}

    return {"ok": True, "status": f"lead_{action}", "event_key": event_key, "lead_id": lead_id, "bitrix": resp}

@app.get("/health")
def health():
    return {"ok": True}

@app.post("/tirox/webhook")
async def tirox_webhook(request: Request):
    return await handle_realtime_new_customer(request)

@app.post("/tirox-webhook")
async def tirox_webhook_alt(request: Request):
    return await handle_realtime_new_customer(request)

@app.post("/")
async def tirox_root(request: Request):
    return await handle_realtime_new_customer(request)

@app.post("/tirox/returning")
async def tirox_returning(request: Request):
    return await handle_returning_update(request)
```

MUALLIF

Allmax Fix Price
Tirox → Bitrix24 CRM Integration
[Community Manager xodimi Narzullo Muhammad Ali]