import uuid
from pathlib import Path

from cachetools import TTLCache
from fastapi import Cookie, Depends, FastAPI, HTTPException, Request, Form
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from starlette.middleware.base import BaseHTTPMiddleware

from src.core import config
from src.core.auth import (
    require_auth, require_api_auth, require_api_user, require_api_role,
    verify_password, hash_password,
    issue_token, revoke_token,
    issue_refresh_token, validate_refresh_token, revoke_refresh_token,
    set_auth_cookie, clear_auth_cookie,
    set_refresh_cookie, clear_refresh_cookie,
    setup_totp, enable_totp, disable_totp, is_totp_enabled, verify_totp,
    issue_totp_temp_token, validate_totp_temp_token,
    set_totp_pending_cookie, clear_totp_pending_cookie,
    security_headers_middleware,
)
from src.core.llm import get_llm
from src.core.logger import get_logger
from src.core.services import (
    UserService, TokenService, ConversationService,
    get_user_service, get_token_service, get_conversation_service,
)
from src.modules.planner import PlannerSession, get_week_status

app = FastAPI(title="AI Assistant")
log = get_logger("web")

app.add_middleware(BaseHTTPMiddleware, dispatch=security_headers_middleware)

STATIC_DIR = Path(__file__).parent / "static"

_sessions: TTLCache = TTLCache(maxsize=256, ttl=7200)  # 2h — evicts abandoned browser sessions
_FREE_CHAT_SYSTEM = "You are a helpful personal AI assistant. Be concise and practical."


def _api_error(exc: Exception) -> dict:
    try:
        body = getattr(exc, "body", None)
        if isinstance(body, dict):
            detail = body.get("error", {}).get("message", str(exc))
            code = getattr(exc, "status_code", None)
            msg = f"API {code}: {detail}" if code else detail
        else:
            msg = str(exc)
    except Exception:
        msg = str(exc)
    log.error(f"LLM error: {msg}")
    return {"message": f"Error: {msg}", "error": True}


def _client_ip(request: Request) -> str:
    return request.headers.get("CF-Connecting-IP") or (request.client.host if request.client else "unknown")


# ── Health ──

@app.get("/health")
def health():
    return {"status": "ok"}


# ── Auth routes (public) ──

@app.get("/login", response_class=HTMLResponse)
def login_page(error: str = ""):
    err = f'<p class="error">{error}</p>' if error else ""
    return HTMLResponse(_login_html(err))


@app.post("/login")
def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    users: UserService = Depends(get_user_service),
):
    ip = _client_ip(request)
    _FAIL = "Invalid credentials."
    _LOCK = f"Too many failed attempts. Try again in {config.LOGIN_LOCKOUT_MINUTES} minutes."

    if users.is_locked(username):
        log.warning(f"login blocked (rate limit) '{username}' from {ip}")
        return RedirectResponse(f"/login?error={_LOCK}", status_code=303)

    user = users.get(username)
    if not user or user["deleted"] or not verify_password(password, user["password_hash"]):
        users.increment_failed_login(username)
        log.warning(f"login failed for '{username}' from {ip}")
        return RedirectResponse(f"/login?error={_FAIL}", status_code=303)

    if is_totp_enabled(username):
        temp = issue_totp_temp_token(username)
        response = RedirectResponse("/login/totp", status_code=303)
        set_totp_pending_cookie(response, temp)
        return response

    users.reset_failed_login(username)
    response = RedirectResponse("/", status_code=303)
    set_auth_cookie(response, issue_token(username))
    set_refresh_cookie(response, issue_refresh_token(username))
    log.info(f"login ok: '{username}' from {ip}")
    return response


@app.get("/login/totp", response_class=HTMLResponse)
def login_totp_page(ai_totp_pending: str = Cookie(default=None), error: str = ""):
    if not ai_totp_pending:
        return RedirectResponse("/login", status_code=303)
    username = validate_totp_temp_token(ai_totp_pending)
    if not username:
        return RedirectResponse("/login", status_code=303)
    err = f'<p class="error">{error}</p>' if error else ""
    return HTMLResponse(_totp_html(username, err))


@app.post("/login/totp")
def login_totp(
    request: Request,
    code: str = Form(...),
    ai_totp_pending: str = Cookie(default=None),
    users: UserService = Depends(get_user_service),
):
    ip = _client_ip(request)
    if not ai_totp_pending:
        return RedirectResponse("/login", status_code=303)

    username = validate_totp_temp_token(ai_totp_pending)
    if not username:
        return RedirectResponse("/login?error=Session+expired.+Please+log+in+again.", status_code=303)

    if users.is_locked(username):
        response = RedirectResponse("/login?error=Too+many+failed+attempts.", status_code=303)
        clear_totp_pending_cookie(response)
        log.warning(f"login blocked (rate limit/totp) '{username}' from {ip}")
        return response

    if not verify_totp(username, code.strip()):
        users.increment_failed_login(username)
        log.warning(f"login failed (wrong totp) '{username}' from {ip}")
        return RedirectResponse("/login/totp?error=Invalid+code.+Try+again.", status_code=303)

    users.reset_failed_login(username)
    response = RedirectResponse("/", status_code=303)
    set_auth_cookie(response, issue_token(username))
    set_refresh_cookie(response, issue_refresh_token(username))
    clear_totp_pending_cookie(response)
    log.info(f"login ok (totp): '{username}' from {ip}")
    return response


@app.post("/logout")
def logout(ai_token: str = Cookie(default=None), ai_refresh: str = Cookie(default=None)):
    if ai_token:
        revoke_token(ai_token)
    if ai_refresh:
        revoke_refresh_token(ai_refresh)
    response = RedirectResponse("/login", status_code=303)
    clear_auth_cookie(response)
    clear_refresh_cookie(response)
    return response


# ── Token refresh (called by frontend on 401) ──

@app.post("/api/token/refresh")
def token_refresh(
    request: Request,
    ai_refresh: str = Cookie(default=None),
    users: UserService = Depends(get_user_service),
):
    if not ai_refresh:
        raise HTTPException(status_code=401, detail="no_refresh_token")
    username = validate_refresh_token(ai_refresh)
    if not username:
        raise HTTPException(status_code=401, detail="invalid_refresh_token")
    if not users.is_active(username):
        raise HTTPException(status_code=401, detail="user_inactive")
    log.debug(f"token refreshed: '{username}'")
    response = JSONResponse({"ok": True})
    set_auth_cookie(response, issue_token(username))
    return response


# ── Current user ──

@app.get("/api/me")
def me(user: dict = Depends(require_api_user)):
    return {
        "username": user["username"],
        "role": user["role"],
        "totp_enabled": is_totp_enabled(user["username"]),
    }


# ── Account: password change ──

class PasswordChangeReq(BaseModel):
    current_password: str
    new_password: str


@app.post("/api/me/password")
def change_password(
    request: Request,
    req: PasswordChangeReq,
    user: dict = Depends(require_api_user),
    users: UserService = Depends(get_user_service),
    tokens: TokenService = Depends(get_token_service),
):
    u = users.get(user["username"])
    if not verify_password(req.current_password, u["password_hash"]):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    if len(req.new_password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    users.update_password(user["username"], hash_password(req.new_password))
    tokens.revoke_all_user_refresh(user["username"])
    log.info(f"password changed: '{user['username']}' from {_client_ip(request)}")
    return {"ok": True}


# ── Account: TOTP ──

@app.get("/api/me/totp/status")
def totp_status(user: dict = Depends(require_api_user)):
    return {"enabled": is_totp_enabled(user["username"])}


@app.post("/api/me/totp/setup")
def totp_setup(user: dict = Depends(require_api_user)):
    secret, uri = setup_totp(user["username"])
    return {"secret": secret, "uri": uri}


class TOTPCodeReq(BaseModel):
    code: str


@app.post("/api/me/totp/enable")
def totp_enable(request: Request, req: TOTPCodeReq, user: dict = Depends(require_api_user)):
    if not enable_totp(user["username"], req.code.strip()):
        raise HTTPException(status_code=400, detail="Invalid TOTP code")
    log.info(f"totp enabled: '{user['username']}' from {_client_ip(request)}")
    return {"ok": True}


class TOTPDisableReq(BaseModel):
    password: str


@app.post("/api/me/totp/disable")
def totp_disable(
    request: Request,
    req: TOTPDisableReq,
    user: dict = Depends(require_api_user),
    users: UserService = Depends(get_user_service),
):
    u = users.get(user["username"])
    if not verify_password(req.password, u["password_hash"]):
        raise HTTPException(status_code=400, detail="Incorrect password")
    disable_totp(user["username"])
    log.info(f"totp disabled: '{user['username']}' from {_client_ip(request)}")
    return {"ok": True}


# ── Admin: user management ──

@app.get("/api/admin/users")
def admin_list_users(
    _: dict = Depends(require_api_role("admin")),
    users: UserService = Depends(get_user_service),
):
    return {"users": users.list_all()}


class RoleReq(BaseModel):
    role: str


@app.post("/api/admin/users/{username}/role")
def admin_set_role(
    username: str,
    req: RoleReq,
    request: Request,
    admin: dict = Depends(require_api_role("admin")),
    users: UserService = Depends(get_user_service),
):
    if req.role not in ("admin", "member"):
        raise HTTPException(status_code=400, detail="Invalid role")
    users.update_role(username, req.role)
    log.info(f"role changed: '{username}' -> {req.role} by '{admin['username']}' from {_client_ip(request)}")
    return {"ok": True}


@app.post("/api/admin/users/{username}/delete")
def admin_delete_user(
    username: str,
    request: Request,
    admin: dict = Depends(require_api_role("admin")),
    users: UserService = Depends(get_user_service),
    tokens: TokenService = Depends(get_token_service),
):
    if username == admin["username"]:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")
    if not users.get(username):
        raise HTTPException(status_code=404, detail="User not found")
    users.soft_delete(username)
    tokens.revoke_all_user_refresh(username)
    log.info(f"user deleted: '{username}' by '{admin['username']}' from {_client_ip(request)}")
    return {"ok": True}


@app.post("/api/admin/users/{username}/restore")
def admin_restore_user(
    username: str,
    request: Request,
    admin: dict = Depends(require_api_role("admin")),
    users: UserService = Depends(get_user_service),
):
    users.restore(username)
    log.info(f"user restored: '{username}' by '{admin['username']}' from {_client_ip(request)}")
    return {"ok": True}


# ── Admin: cache debug ──

@app.get("/api/admin/cache")
def admin_cache_stats(
    _: dict = Depends(require_api_role("admin")),
    users: UserService = Depends(get_user_service),
    tokens: TokenService = Depends(get_token_service),
):
    return {
        "user_cache": {
            "entries": users.cache_entries(mask={"password_hash"}),
            **users.cache_stats(),
        },
        "token_cache": {
            "entries": tokens.cache_entries(),
            **tokens.cache_stats(),
        },
    }


# ── Planning sessions ──

class StartReq(BaseModel):
    type: str


class ReplyReq(BaseModel):
    session_id: str
    message: str


@app.post("/api/start")
def start_session(req: StartReq, _: str = Depends(require_api_auth)):
    try:
        session_id = str(uuid.uuid4())
        session = PlannerSession(req.type, session_id)
        _sessions[session_id] = session
        msg = session.start()
        log.info(f"web planner session started type={req.type}")
        return {"session_id": session_id, "message": msg}
    except Exception as exc:
        return _api_error(exc)


@app.post("/api/reply")
def reply(req: ReplyReq, _: str = Depends(require_api_auth)):
    session = _sessions.get(req.session_id)
    if not session:
        return {"message": "Session expired. Start a new one from the sidebar."}
    try:
        return {"message": session.reply(req.message)}
    except Exception as exc:
        return _api_error(exc)


# ── Free chat ──

class ChatReq(BaseModel):
    message: str
    session_id: str


@app.post("/api/chat")
def free_chat(
    req: ChatReq,
    _: str = Depends(require_api_auth),
    convs: ConversationService = Depends(get_conversation_service),
):
    from llama_index.core.llms import ChatMessage, MessageRole
    try:
        llm = get_llm()
        history = convs.get_recent(req.session_id, limit=10)
        messages = [ChatMessage(role=MessageRole.SYSTEM, content=_FREE_CHAT_SYSTEM)]
        for turn in history:
            role = MessageRole.USER if turn["role"] == "user" else MessageRole.ASSISTANT
            messages.append(ChatMessage(role=role, content=turn["content"]))
        messages.append(ChatMessage(role=MessageRole.USER, content=req.message))
        response = llm.chat(messages)
        answer = response.message.content
        turn_num = convs.next_turn(req.session_id)
        convs.save_turn(req.session_id, "chat", "free", turn_num, "user", req.message)
        convs.save_turn(req.session_id, "chat", "free", turn_num + 1, "assistant", answer)
        return {"message": answer}
    except Exception as exc:
        return _api_error(exc)


# ── Status & RAG ──

class AskReq(BaseModel):
    question: str


@app.get("/api/status")
def status(_: str = Depends(require_api_auth)):
    return {"message": get_week_status()}


@app.post("/api/ask")
def ask_kb(req: AskReq, _: str = Depends(require_api_auth)):
    from src.core.query import ask
    try:
        result = ask(req.question)
        answer = result["answer"]
        if result["sources"]:
            answer += "\n\nSources: " + ", ".join(result["sources"])
        return {"message": answer}
    except Exception as exc:
        return _api_error(exc)


# ── GenDB (admin only) ──

@app.post("/api/gendb")
def gendb(_: dict = Depends(require_api_role("admin"))):
    from src.core.migrate import run
    try:
        count = run()
        log.info(f"gendb: {count} migration(s) applied")
        return {"applied": count, "message": f"{count} migration(s) applied."}
    except Exception as exc:
        return _api_error(exc)


# ── Static & index ──

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
def index(_: str = Depends(require_auth)):
    return FileResponse(str(STATIC_DIR / "index.html"))


# ── Login page HTML ──

def _login_html(error_block: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AI Assistant — Login</title>
<style>
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #0f0f0f; color: #e0e0e0; display: flex; align-items: center; justify-content: center; min-height: 100dvh; }}
.card {{ background: #161616; border: 1px solid #242424; border-radius: 14px; padding: 40px 36px; width: 100%; max-width: 360px; }}
.logo {{ font-size: 32px; text-align: center; margin-bottom: 6px; }}
h1 {{ font-size: 18px; font-weight: 600; text-align: center; margin-bottom: 28px; color: #fff; }}
label {{ display: block; font-size: 12px; color: #666; margin-bottom: 6px; letter-spacing: .05em; text-transform: uppercase; }}
input {{ width: 100%; background: #1a1a1a; border: 1px solid #2e2e2e; color: #e0e0e0; border-radius: 8px; padding: 10px 12px; font-size: 14px; outline: none; margin-bottom: 18px; transition: border-color .15s; }}
input:focus {{ border-color: #3a6ea5; }}
button {{ width: 100%; background: #1b3358; color: #7eb8f7; border: 1px solid #234272; border-radius: 8px; padding: 11px; font-size: 14px; font-weight: 500; cursor: pointer; transition: background .12s; }}
button:hover {{ background: #234272; }}
.error {{ color: #ff7070; font-size: 13px; margin-bottom: 16px; text-align: center; }}
.hint {{ color: #444; font-size: 12px; text-align: center; margin-top: 20px; }}
</style>
</head>
<body>
<div class="card">
  <div class="logo">🤖</div>
  <h1>AI Assistant</h1>
  {error_block}
  <form method="post" action="/login">
    <label for="u">Username</label>
    <input id="u" name="username" type="text" autocomplete="username" autofocus required>
    <label for="p">Password</label>
    <input id="p" name="password" type="password" autocomplete="current-password" required>
    <button type="submit">Sign in</button>
  </form>
  <p class="hint">No account? Contact the admin.</p>
</div>
</body>
</html>"""


def _totp_html(username: str, error_block: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AI Assistant — Two-Factor Auth</title>
<style>
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #0f0f0f; color: #e0e0e0; display: flex; align-items: center; justify-content: center; min-height: 100dvh; }}
.card {{ background: #161616; border: 1px solid #242424; border-radius: 14px; padding: 40px 36px; width: 100%; max-width: 360px; }}
.logo {{ font-size: 32px; text-align: center; margin-bottom: 6px; }}
h1 {{ font-size: 18px; font-weight: 600; text-align: center; margin-bottom: 6px; color: #fff; }}
.sub {{ font-size: 13px; color: #555; text-align: center; margin-bottom: 28px; }}
label {{ display: block; font-size: 12px; color: #666; margin-bottom: 6px; letter-spacing: .05em; text-transform: uppercase; }}
input {{ width: 100%; background: #1a1a1a; border: 1px solid #2e2e2e; color: #e0e0e0; border-radius: 8px; padding: 10px 12px; font-size: 22px; outline: none; margin-bottom: 18px; transition: border-color .15s; text-align: center; letter-spacing: .3em; }}
input:focus {{ border-color: #3a6ea5; }}
button {{ width: 100%; background: #1b3358; color: #7eb8f7; border: 1px solid #234272; border-radius: 8px; padding: 11px; font-size: 14px; font-weight: 500; cursor: pointer; transition: background .12s; }}
button:hover {{ background: #234272; }}
.error {{ color: #ff7070; font-size: 13px; margin-bottom: 16px; text-align: center; }}
.back {{ color: #444; font-size: 12px; text-align: center; margin-top: 20px; }}
.back a {{ color: #555; text-decoration: none; }}
.back a:hover {{ color: #888; }}
</style>
</head>
<body>
<div class="card">
  <div class="logo">🔐</div>
  <h1>Two-Factor Auth</h1>
  <p class="sub">Code for <strong>{username}</strong></p>
  {error_block}
  <form method="post" action="/login/totp">
    <label for="code">Authenticator Code</label>
    <input id="code" name="code" type="text" inputmode="numeric" pattern="[0-9]{{6}}"
           maxlength="6" autocomplete="one-time-code" autofocus required placeholder="000000">
    <button type="submit">Verify</button>
  </form>
  <p class="back"><a href="/login">Back to login</a></p>
</div>
</body>
</html>"""
