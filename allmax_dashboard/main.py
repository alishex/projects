"""
ALLMAX Telegram AI Agent — Web Dashboard
Port : 8080
Auth : session cookie, 7 kun
DB   : /opt/AllmaxProjects/allmax_telethon/analytics/telegram_dm_log.sqlite3
"""
import secrets
import sqlite3
import time
from datetime import datetime, timedelta
from pathlib import Path

from fastapi import FastAPI, Form, Request
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

EMAIL    = "allmaxfixprice.work@gmail.com"
PASSWORD = "@llm@x20260101"
DB_PATH  = Path("/opt/AllmaxProjects/allmax_telethon/analytics/telegram_dm_log.sqlite3")
TTL      = 86400 * 7

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


def db():
    return sqlite3.connect(str(DB_PATH), check_same_thread=False)


def q1(con, sql, p=()):
    r = con.execute(sql, p).fetchone()
    return (r[0] or 0) if r else 0


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


# ── API ────────────────────────────────────────────────────────────────────────

@app.get("/api/stats")
def api_stats(request: Request):
    if not authed(request):
        return JSONResponse({"error": "unauth"}, 401)
    con = db()
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
    con = db()
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
    con = db()
    rows = con.execute(
        "SELECT date,display_name,username,topic,contact_type,updated_at "
        "FROM daily_contacts ORDER BY updated_at DESC LIMIT ?", (limit,)
    ).fetchall()
    now = datetime.now()
    out = []
    for r in rows:
        try:
            dt = datetime.fromisoformat(r[5])
            diff = now - dt
            s = int(diff.total_seconds())
            if s < 60:    ago = f"{s} sek"
            elif s < 3600: ago = f"{s//60} min"
            elif diff.days == 0: ago = f"{s//3600} soat"
            else:          ago = f"{diff.days} kun"
        except Exception:
            ago = "—"
        out.append({
            "date": r[0], "name": r[1] or "Noma'lum",
            "username": r[2] or "", "topic": (r[3] or "—")[:90],
            "type": r[4] or "general", "ago": ago,
        })
    con.close()
    return JSONResponse(out)
