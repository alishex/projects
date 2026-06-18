"""
Bitrix24 CRM dan TIROX leadlarini o'chiradi.
Ishlatish: python3 delete_tirox_leads.py
"""
import os, sys, time
import requests

WEBHOOK = "https://allmax.bitrix24.kz/rest/63/cbpqec8zljzqbc93/"
TIMEOUT = 20

def bx(method, payload=None):
    url = f"{WEBHOOK}{method}.json"
    r = requests.post(url, json=payload or {}, timeout=TIMEOUT)
    r.raise_for_status()
    d = r.json()
    if "error" in d:
        raise RuntimeError(f"Bitrix error: {d['error']} — {d.get('error_description','')}")
    return d

def fetch_tirox_lead_ids():
    ids = []
    start = 0
    while True:
        d = bx("crm.lead.list", {
            "filter": {"%TITLE": "TIROX"},
            "select": ["ID", "TITLE"],
            "start": start,
        })
        rows = d.get("result", [])
        ids += [int(r["ID"]) for r in rows]
        print(f"  {start}–{start+len(rows)}: {[r['TITLE'][:40] for r in rows[:3]]}...")
        total = int(d.get("total", 0))
        start += 50
        if start >= total or not rows:
            print(f"Jami topildi: {total} ta TIROX lead")
            break
        time.sleep(0.3)
    return ids, total

def delete_leads(ids):
    deleted = 0
    for lid in ids:
        try:
            bx("crm.lead.delete", {"id": lid})
            deleted += 1
            print(f"  ✓ O'chirildi: {lid}")
        except Exception as e:
            print(f"  ✗ Xato {lid}: {e}")
        time.sleep(0.2)  # rate limit
    return deleted

def main():
    print("=== TIROX leadlarini qidirish ===")
    try:
        ids, total = fetch_tirox_lead_ids()
    except RuntimeError as e:
        print(f"API xato: {e}")
        sys.exit(1)

    if not ids:
        print("TIROX lead topilmadi.")
        return

    print(f"\n{len(ids)} ta lead o'chiriladi. Davom etamizmi? (ha/yoq): ", end="")
    ans = input().strip().lower()
    if ans not in ("ha", "h", "yes", "y"):
        print("Bekor qilindi.")
        return

    print(f"\n=== O'chirish boshlandi ===")
    n = delete_leads(ids)
    print(f"\nNatija: {n}/{len(ids)} ta TIROX lead o'chirildi.")

if __name__ == "__main__":
    main()
