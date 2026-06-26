"""
ALLMAX Web Dashboard
Port : 8080
Auth : session cookie, 7 kun
"""
import secrets
import sqlite3
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import FastAPI, Form, Request
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

EMAIL    = "allmaxfixprice.work@gmail.com"
PASSWORD = "@llm@x20260101"
TG_DB    = Path("/opt/AllmaxProjects/allmax_telethon/analytics/telegram_dm_log.sqlite3")
IG_DB    = Path("/opt/AllmaxProjects/allmax_instagram_agent/data/instagram_dm_bot.sqlite3")
TTL      = 86400 * 7
UZT      = timezone(timedelta(hours=5))

app = FastAPI(docs_url=None, redoc_url=None)
app.mount("/static", StaticFiles(directory="static"), name="static")

_sessions: dict[str, float] = {}


def authed(request: Request) -> bool:
    t = request.cookies.get("sid")
    if not t:
        return False
    exp = _sessions.get(t)
    if exp is None or exp < time.time():
        _sessions.pop(t, None)
        return False
    return True


def db(path: Path):
    return sqlite3.connect(str(path), check_same_thread=False)


def q1(con, sql, p=()):
    r = con.execute(sql, p).fetchone()
    return (r[0] or 0) if r else 0


def time_ago(ts_str: str) -> str:
    try:
        dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UZT)
        now = datetime.now(tz=timezone.utc)
        s = int((now - dt).total_seconds())
        if s < 60:     return f"{s} sek"
        if s < 3600:   return f"{s//60} min"
        if s < 86400:  return f"{s//3600} soat"
        return f"{s//86400} kun"
    except Exception:
        return "—"


# ── Pages ──────────────────────────────────────────────────────────────────────

@app.get("/login")
def login_page():
    return FileResponse("static/login.html")


@app.post("/login")
async def login_post(request: Request,
                     email: str = Form(...), password: str = Form(...)):
    if email.strip() == EMAIL and password == PASSWORD:
        tok = secrets.token_urlsafe(32)
        _sessions[tok] = time.time() + TTL
        r = RedirectResponse("/", status_code=303)
        r.set_cookie("sid", tok, httponly=True, max_age=TTL, samesite="lax")
        return r
    return RedirectResponse("/login?err=1", status_code=303)


@app.get("/logout")
def logout(request: Request):
    _sessions.pop(request.cookies.get("sid", ""), None)
    r = RedirectResponse("/login", status_code=303)
    r.delete_cookie("sid")
    return r


@app.get("/")
def index(request: Request):
    if not authed(request):
        return RedirectResponse("/login", status_code=302)
    return FileResponse("static/index.html")


@app.get("/ig")
def ig_page(request: Request):
    if not authed(request):
        return RedirectResponse("/login", status_code=302)
    return FileResponse("static/instagram.html")


# ── Telegram API ───────────────────────────────────────────────────────────────

@app.get("/api/stats")
def api_stats(request: Request):
    if not authed(request):
        return JSONResponse({"error": "unauth"}, 401)
    con = db(TG_DB)
    today = datetime.now().strftime("%Y-%m-%d")
    week  = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    month = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    out = {
        "today_users":    q1(con, "SELECT COUNT(DISTINCT user_id) FROM dm_events WHERE date(ts)=?", (today,)),
        "today_msgs":     q1(con, "SELECT COUNT(*) FROM dm_events WHERE date(ts)=?", (today,)),
        "week_users":     q1(con, "SELECT COUNT(DISTINCT user_id) FROM dm_events WHERE date(ts)>=?", (week,)),
        "month_users":    q1(con, "SELECT COUNT(DISTINCT user_id) FROM dm_events WHERE date(ts)>=?", (month,)),
        "total_users":    q1(con, "SELECT COUNT(DISTINCT user_id) FROM dm_events"),
        "total_msgs":     q1(con, "SELECT COUNT(*) FROM dm_events"),
        "total_leads":    q1(con, "SELECT COUNT(*) FROM lead_group_messages"),
        "today_contacts": q1(con, "SELECT COUNT(*) FROM daily_contacts WHERE date=?", (today,)),
        "today_human":    q1(con, "SELECT COUNT(*) FROM daily_contacts WHERE date=? AND contact_type=?", (today, "human")),
        "ts": datetime.now().strftime("%H:%M:%S"),
    }
    con.close()
    return JSONResponse(out)


@app.get("/api/daily")
def api_daily(request: Request, days: int = 14):
    if not authed(request):
        return JSONResponse({"error": "unauth"}, 401)
    con = db(TG_DB)
    rows = con.execute(
        "SELECT date(ts),COUNT(DISTINCT user_id),COUNT(*) FROM dm_events "
        "WHERE ts>=datetime('now','-'||?||' days') GROUP BY date(ts) ORDER BY date(ts)",
        (days,)
    ).fetchall()
    con.close()
    return JSONResponse([{"date": r[0], "users": r[1], "msgs": r[2]} for r in rows])


@app.get("/api/contacts")
def api_contacts(request: Request, limit: int = 30):
    if not authed(request):
        return JSONResponse({"error": "unauth"}, 401)
    con = db(TG_DB)
    rows = con.execute(
        "SELECT date,display_name,username,topic,contact_type,updated_at "
        "FROM daily_contacts ORDER BY updated_at DESC LIMIT ?", (limit,)
    ).fetchall()
    out = []
    for r in rows:
        out.append({
            "date": r[0], "name": r[1] or "Noma'lum",
            "username": r[2] or "", "topic": (r[3] or "—")[:90],
            "type": r[4] or "general", "ago": time_ago(r[5] or ""),
        })
    con.close()
    return JSONResponse(out)


# ── Instagram API ──────────────────────────────────────────────────────────────

@app.get("/api/ig/stats")
def api_ig_stats(request: Request):
    if not authed(request):
        return JSONResponse({"error": "unauth"}, 401)
    con = db(IG_DB)
    today = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
    week  = (datetime.now(tz=timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%d")
    month = (datetime.now(tz=timezone.utc) - timedelta(days=30)).strftime("%Y-%m-%d")
    out = {
        "today_users":   q1(con, "SELECT COUNT(*) FROM conversations WHERE date(updated_at)=?", (today,)),
        "week_users":    q1(con, "SELECT COUNT(*) FROM conversations WHERE date(updated_at)>=?", (week,)),
        "month_users":   q1(con, "SELECT COUNT(*) FROM conversations WHERE date(updated_at)>=?", (month,)),
        "total_users":   q1(con, "SELECT COUNT(*) FROM conversations"),
        "total_leads":   q1(con, "SELECT COUNT(*) FROM sent_leads"),
        "today_leads":   q1(con, "SELECT COUNT(*) FROM sent_leads WHERE date(created_at)=?", (today,)),
        "total_targets": q1(con, "SELECT COUNT(*) FROM conversations WHERE target_detected=1"),
        "today_targets": q1(con, "SELECT COUNT(*) FROM conversations WHERE target_detected=1 AND date(updated_at)=?", (today,)),
        "total_phones":  q1(con, "SELECT COUNT(*) FROM conversations WHERE contact_found=1"),
        "ts": datetime.now().strftime("%H:%M:%S"),
    }
    con.close()
    return JSONResponse(out)


@app.get("/api/ig/daily")
def api_ig_daily(request: Request, days: int = 14):
    if not authed(request):
        return JSONResponse({"error": "unauth"}, 401)
    con = db(IG_DB)
    since = (datetime.now(tz=timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")
    rows = con.execute(
        "SELECT date(updated_at), COUNT(*), SUM(contact_found), SUM(target_detected) "
        "FROM conversations WHERE date(updated_at)>=? "
        "GROUP BY date(updated_at) ORDER BY date(updated_at)",
        (since,)
    ).fetchall()
    con.close()
    return JSONResponse([{
        "date": r[0], "users": r[1], "phones": r[2] or 0, "targets": r[3] or 0
    } for r in rows])


@app.get("/api/ig/contacts")
def api_ig_contacts(request: Request, limit: int = 30):
    if not authed(request):
        return JSONResponse({"error": "unauth"}, 401)
    con = db(IG_DB)
    rows = con.execute(
        "SELECT username, full_name, phone, contact_found, target_detected, "
        "bitrix_lead_id, updated_at "
        "FROM conversations ORDER BY updated_at DESC LIMIT ?", (limit,)
    ).fetchall()
    out = []
    for r in rows:
        ctype = "lead" if r[5] else ("target" if r[4] else ("phone" if r[3] else "general"))
        out.append({
            "username":  r[0] or "",
            "name":      r[1] or r[0] or "Noma'lum",
            "phone":     r[2] or "",
            "has_phone": bool(r[3]),
            "is_target": bool(r[4]),
            "has_lead":  bool(r[5]),
            "type":      ctype,
            "ago":       time_ago(r[6] or ""),
        })
    con.close()
    return JSONResponse(out)
