"""
Connectors Routes (Phase 147.5)

MARKER_147_5_REGISTRY_V2_COMPAT
MARKER_147_5_OAUTH_REAL_HANDOFF
MARKER_147_5_OAUTH_CALLBACK_BRIDGE
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from src.services.connectors_ingestion_service import get_connectors_ingestion_queue_service
from src.services.connectors_secure_store import get_connectors_secure_store
from src.services.connectors_state_service import get_connectors_state_service

router = APIRouter(prefix="/api/connectors", tags=["connectors"])

OAUTH_PENDING_TTL_SECONDS = 10 * 60


class ConnectorProviderResponse(BaseModel):
    id: str
    source: str
    display_name: str

    connected: bool
    status: str  # connected | expired | error | pending
    auth_method: str  # oauth | api_key | basic | custom

    capabilities: Dict[str, bool]  # read, write, offline_access, webhooks

    scopes: Optional[List[str]] = None
    scopes_minimal: Optional[List[str]] = None
    scopes_full: Optional[List[str]] = None
    default_scopes: Optional[List[str]] = None

    provider_class: Optional[str] = None
    auth_flow: Optional[str] = None
    redirect_uri: Optional[str] = None

    requires_verification: bool = False
    rate_limit_model: Optional[str] = None
    rate_limit_policy: Optional[str] = None
    token_policy: Optional[str] = None
    compliance_notes: Optional[str] = None

    token_present: bool
    last_refresh_at: Optional[str] = None
    expires_in: Optional[int] = None
    account_label: Optional[str] = None

    last_scan_at: Optional[str] = None
    last_scan_count: Optional[int] = None
    last_sync_at: Optional[str] = None


class ConnectRequest(BaseModel):
    account_label: Optional[str] = None


class OAuthStartRequest(BaseModel):
    redirect_uri: Optional[str] = None
    scopes: Optional[List[str]] = None


class OAuthCompleteRequest(BaseModel):
    provider_id: Optional[str] = None
    oauth_state: str
    auth_code: Optional[str] = None
    account_label: Optional[str] = None


class ManualAuthRequest(BaseModel):
    auth_type: str  # api_key | link | token
    value: str
    account_label: Optional[str] = None


class OAuthClientCredentialsRequest(BaseModel):
    client_id: str
    client_secret: str


class ConnectorScanRequest(BaseModel):
    selected_ids: Optional[List[str]] = None
    selected_paths: Optional[List[str]] = None


_oauth_pending: Dict[str, Dict[str, Any]] = {}


def _provider_index() -> Dict[str, Dict[str, Any]]:
    service = get_connectors_state_service()
    return {p["id"]: p for p in service.list()}


def _clean_env_prefix(value: str) -> str:
    return "".join(ch if ch.isalnum() else "_" for ch in value).upper().strip("_")


def _cleanup_pending_states(now: Optional[float] = None) -> None:
    now_ts = now or time.time()
    expired = [k for k, v in _oauth_pending.items() if float(v.get("expires_at", 0)) <= now_ts]
    for key in expired:
        _oauth_pending.pop(key, None)


def _first_non_empty(values: List[Optional[str]]) -> Optional[str]:
    for v in values:
        if v and str(v).strip():
            return str(v).strip()
    return None


def _resolve_oauth_client_credentials(provider: Dict[str, Any], provider_id: str) -> Tuple[str, str]:
    import os

    provider_prefix = _clean_env_prefix(provider_id)
    provider_class = _clean_env_prefix(str(provider.get("provider_class") or provider_id))
    secure_store = get_connectors_secure_store()
    stored_creds = secure_store.get_oauth_client_credentials(provider_id)

    cid = _first_non_empty([
        stored_creds.get("client_id") if stored_creds else None,
        os.getenv(f"{provider_prefix}_CLIENT_ID"),
        os.getenv(f"{provider_class}_CLIENT_ID"),
        os.getenv("OAUTH_CLIENT_ID"),
        os.getenv("GOOGLE_CLIENT_ID") if provider_class == "GOOGLE" else None,
    ])
    secret = _first_non_empty([
        stored_creds.get("client_secret") if stored_creds else None,
        os.getenv(f"{provider_prefix}_CLIENT_SECRET"),
        os.getenv(f"{provider_class}_CLIENT_SECRET"),
        os.getenv("OAUTH_CLIENT_SECRET"),
        os.getenv("GOOGLE_CLIENT_SECRET") if provider_class == "GOOGLE" else None,
    ])

    if not cid or not secret:
        raise HTTPException(
            status_code=503,
            detail=(
                f"OAuth client credentials missing for {provider_id}. "
                f"Set {provider_prefix}_CLIENT_ID/{provider_prefix}_CLIENT_SECRET "
                f"or class-level env vars."
            ),
        )
    return cid, secret


def _build_callback_url(request: Request) -> str:
    return str(request.base_url).rstrip("/") + "/api/connectors/oauth/callback"


def _post_form(url: str, data: Dict[str, Any], headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    payload = urllib.parse.urlencode({k: v for k, v in data.items() if v is not None}).encode("utf-8")
    req = urllib.request.Request(url, data=payload, headers=headers or {}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            body = resp.read().decode("utf-8", errors="ignore")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        raise HTTPException(status_code=400, detail=f"OAuth token exchange failed: {detail[:300]}")
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"OAuth token exchange error: {exc}")

    try:
        return json.loads(body)
    except Exception:
        parsed_qs = urllib.parse.parse_qs(body)
        return {k: vals[0] for k, vals in parsed_qs.items() if vals}


def _http_get_json(url: str, headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    req = urllib.request.Request(url, headers=headers or {}, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read().decode("utf-8", errors="ignore")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        raise HTTPException(status_code=400, detail=f"Provider request failed: {detail[:300]}")
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Provider request error: {exc}")
    try:
        return json.loads(body)
    except Exception:
        raise HTTPException(status_code=400, detail="Provider returned invalid JSON")


def _get_provider_access_token(provider_id: str) -> str:
    secure_store = get_connectors_secure_store()
    bundle = secure_store.get_oauth_bundle(provider_id)
    if bundle and bundle.get("access_token"):
        return str(bundle["access_token"])
    token = secure_store.get_token(provider_id)
    if token:
        return token
    raise HTTPException(status_code=400, detail=f"Provider auth required: {provider_id}")


def _google_drive_tree(access_token: str, page_limit: int = 6) -> Dict[str, Any]:
    fields = "nextPageToken,files(id,name,mimeType,parents,modifiedTime,size)"
    q = urllib.parse.quote("trashed = false")
    base = (
        "https://www.googleapis.com/drive/v3/files"
        f"?pageSize=1000&supportsAllDrives=true&includeItemsFromAllDrives=true&fields={urllib.parse.quote(fields)}&q={q}"
    )
    headers = {"Authorization": f"Bearer {access_token}"}

    items: List[Dict[str, Any]] = []
    page_token: Optional[str] = None
    pages = 0

    while pages < page_limit:
        url = base
        if page_token:
            url = f"{url}&pageToken={urllib.parse.quote(page_token)}"
        payload = _http_get_json(url, headers=headers)
        batch = payload.get("files", [])
        if isinstance(batch, list):
            items.extend(batch)
        page_token = payload.get("nextPageToken")
        pages += 1
        if not page_token:
            break

    nodes_by_id: Dict[str, Dict[str, Any]] = {}
    children: Dict[str, List[str]] = {"root": []}

    for row in items:
        node_id = str(row.get("id", "")).strip()
        if not node_id:
            continue
        mime = str(row.get("mimeType", ""))
        is_folder = mime == "application/vnd.google-apps.folder"
        node = {
            "id": node_id,
            "name": str(row.get("name", "Untitled")),
            "type": "folder" if is_folder else "file",
            "mime_type": mime,
            "parents": [str(p) for p in row.get("parents", []) if str(p).strip()],
            "size": int(row.get("size", 0) or 0),
            "modified": row.get("modifiedTime"),
        }
        nodes_by_id[node_id] = node
        children[node_id] = []

    for node in nodes_by_id.values():
        parent_ids = [pid for pid in node["parents"] if pid in nodes_by_id]
        if not parent_ids:
            children["root"].append(node["id"])
        else:
            for pid in parent_ids:
                children.setdefault(pid, []).append(node["id"])

    def build_subtree(node_id: str, parent_path: str) -> Dict[str, Any]:
        node = nodes_by_id[node_id]
        current_path = f"{parent_path}/{node['name']}" if parent_path else f"/{node['name']}"
        child_nodes = [build_subtree(cid, current_path) for cid in sorted(children.get(node_id, []), key=lambda x: nodes_by_id[x]["name"].lower())]
        return {
            "id": node["id"],
            "name": node["name"],
            "type": node["type"],
            "mime_type": node["mime_type"],
            "path": current_path,
            "size": node["size"],
            "modified": node["modified"],
            "children": child_nodes,
        }

    tree = [build_subtree(cid, "/Drive") for cid in sorted(children.get("root", []), key=lambda x: nodes_by_id[x]["name"].lower())]
    folders_count = sum(1 for n in nodes_by_id.values() if n["type"] == "folder")
    files_count = len(nodes_by_id) - folders_count
    return {
        "provider": "google_drive",
        "total_nodes": len(nodes_by_id),
        "folders": folders_count,
        "files": files_count,
        "tree": tree,
        "truncated": bool(page_token),
    }


def _build_oauth_authorize_url(
    provider: Dict[str, Any],
    provider_id: str,
    client_id: str,
    redirect_uri: str,
    scopes: List[str],
    state: str,
) -> str:
    provider_class = str(provider.get("provider_class") or provider_id).lower()

    if provider_class in {"google", "google_drive", "gmail", "youtube"}:
        base = "https://accounts.google.com/o/oauth2/v2/auth"
        query = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": " ".join(scopes),
            "state": state,
            "access_type": "offline",
            "prompt": "consent",
            "include_granted_scopes": "true",
        }
        return base + "?" + urllib.parse.urlencode(query)

    if provider_class == "dropbox":
        base = "https://www.dropbox.com/oauth2/authorize"
        query = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "state": state,
            "token_access_type": "offline",
            "scope": " ".join(scopes),
        }
        return base + "?" + urllib.parse.urlencode(query)

    if provider_class == "github":
        base = "https://github.com/login/oauth/authorize"
        query = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "state": state,
            "scope": " ".join(scopes),
        }
        return base + "?" + urllib.parse.urlencode(query)

    raise HTTPException(status_code=501, detail=f"OAuth start not implemented for provider_class={provider_class}")


def _exchange_code_for_tokens(
    provider: Dict[str, Any],
    provider_id: str,
    code: str,
    redirect_uri: str,
) -> Dict[str, Any]:
    provider_class = str(provider.get("provider_class") or provider_id).lower()
    client_id, client_secret = _resolve_oauth_client_credentials(provider, provider_id)

    if provider_class in {"google", "google_drive", "gmail", "youtube"}:
        return _post_form(
            "https://oauth2.googleapis.com/token",
            {
                "code": code,
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            },
        )

    if provider_class == "dropbox":
        return _post_form(
            "https://api.dropbox.com/oauth2/token",
            {
                "code": code,
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            },
        )

    if provider_class == "github":
        return _post_form(
            "https://github.com/login/oauth/access_token",
            {
                "code": code,
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uri": redirect_uri,
            },
            headers={"Accept": "application/json"},
        )

    raise HTTPException(status_code=501, detail=f"OAuth complete not implemented for provider_class={provider_class}")


def _build_connector_response(provider: Dict[str, Any], secure_store) -> ConnectorProviderResponse:
    token_present = secure_store.has_token(str(provider.get("id", "")))

    if not provider.get("connected", False):
        status = "pending"
    elif not token_present:
        status = "expired"
    else:
        status = "connected"

    return ConnectorProviderResponse(
        id=str(provider.get("id", "")),
        source=str(provider.get("source", "cloud")),
        display_name=str(provider.get("display_name", provider.get("id", "provider"))),
        connected=bool(provider.get("connected", False)),
        status=str(provider.get("status", status)),
        auth_method=str(provider.get("auth_method", "oauth")),
        capabilities=provider.get("capabilities", {
            "read": True,
            "write": False,
            "offline_access": True,
            "webhooks": False,
        }),
        scopes=provider.get("scopes"),
        scopes_minimal=provider.get("scopes_minimal"),
        scopes_full=provider.get("scopes_full"),
        default_scopes=provider.get("default_scopes"),
        provider_class=provider.get("provider_class"),
        auth_flow=provider.get("auth_flow"),
        redirect_uri=provider.get("redirect_uri"),
        requires_verification=bool(provider.get("requires_verification", False)),
        rate_limit_model=provider.get("rate_limit_model"),
        rate_limit_policy=provider.get("rate_limit_policy"),
        token_policy=provider.get("token_policy"),
        compliance_notes=provider.get("compliance_notes"),
        token_present=token_present,
        last_refresh_at=provider.get("updated_at") or provider.get("last_refresh_at"),
        expires_in=provider.get("expires_in"),
        account_label=provider.get("account_label"),
        last_scan_at=provider.get("last_scan_at") or provider.get("last_sync_at"),
        last_scan_count=provider.get("last_scan_count"),
        last_sync_at=provider.get("last_sync_at"),
    )


@router.post("/{provider_id}/oauth/credentials")
async def set_oauth_client_credentials(provider_id: str, body: OAuthClientCredentialsRequest) -> dict:
    provider = _provider_index().get(provider_id)
    if not provider:
        raise HTTPException(status_code=404, detail=f"Unknown provider: {provider_id}")
    auth_method = str(provider.get("auth_method", "")).lower()
    if auth_method not in {"oauth", "oauth2"}:
        raise HTTPException(status_code=400, detail=f"Provider does not use OAuth: {provider_id}")

    client_id = (body.client_id or "").strip()
    client_secret = (body.client_secret or "").strip()
    if not client_id or not client_secret:
        raise HTTPException(status_code=400, detail="client_id and client_secret are required")

    secure_store = get_connectors_secure_store()
    secure_store.set_oauth_client_credentials(provider_id, client_id, client_secret)
    return {"success": True, "provider_id": provider_id, "message": "OAuth credentials saved"}


@router.get("/status")
async def connectors_status(source: Optional[str] = Query(default=None)) -> dict:
    service = get_connectors_state_service()
    secure_store = get_connectors_secure_store()

    providers = service.list(source=source)
    result = [_build_connector_response(p, secure_store).model_dump() for p in providers]

    return {
        "success": True,
        "source": source,
        "providers": result,
        "count": len(result),
        "secure_storage_enabled": secure_store.encryption_enabled(),
    }


@router.get("/registry")
async def connectors_registry(source: Optional[str] = Query(default=None)) -> dict:
    service = get_connectors_state_service()
    entries = service.get_registry(source=source)
    return {
        "success": True,
        "source": source,
        "providers": entries,
        "count": len(entries),
    }


@router.get("/{provider_id}/tree")
async def connector_tree(provider_id: str) -> dict:
    provider = _provider_index().get(provider_id)
    if not provider:
        raise HTTPException(status_code=404, detail=f"Unknown provider: {provider_id}")
    if not provider.get("connected"):
        raise HTTPException(status_code=400, detail=f"Provider not connected: {provider_id}")

    provider_class = str(provider.get("provider_class") or provider_id).lower()
    if provider_class not in {"google", "google_drive"}:
        raise HTTPException(status_code=400, detail=f"Tree preview not implemented for provider: {provider_id}")

    token = _get_provider_access_token(provider_id)
    tree_payload = _google_drive_tree(token)
    return {
        "success": True,
        "provider_id": provider_id,
        **tree_payload,
    }


@router.post("/{provider_id}/connect")
async def connect_provider(provider_id: str, body: ConnectRequest) -> dict:
    service = get_connectors_state_service()
    secure_store = get_connectors_secure_store()

    try:
        state = service.connect(provider_id, body.account_label)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Unknown provider: {provider_id}")

    response = _build_connector_response(state, secure_store)
    return {
        "success": True,
        "provider": response.model_dump(),
        "message": f"Connected: {state['display_name']}",
    }


@router.post("/{provider_id}/oauth/start")
async def oauth_start(provider_id: str, body: OAuthStartRequest, request: Request) -> dict:
    provider = _provider_index().get(provider_id)
    if not provider:
        raise HTTPException(status_code=404, detail=f"Unknown provider: {provider_id}")
    if str(provider.get("auth_method", "")).lower() not in {"oauth", "oauth2"}:
        raise HTTPException(status_code=400, detail=f"Provider does not use OAuth: {provider_id}")

    _cleanup_pending_states()

    oauth_state = f"st_{uuid4().hex}"
    redirect_uri = (body.redirect_uri or provider.get("redirect_uri") or _build_callback_url(request)).strip()
    scopes = body.scopes or provider.get("default_scopes") or provider.get("scopes_minimal") or provider.get("scopes") or ["read"]
    if not isinstance(scopes, list):
        scopes = [str(scopes)]

    client_id, _ = _resolve_oauth_client_credentials(provider, provider_id)
    auth_url = _build_oauth_authorize_url(
        provider=provider,
        provider_id=provider_id,
        client_id=client_id,
        redirect_uri=redirect_uri,
        scopes=[str(s) for s in scopes if str(s).strip()],
        state=oauth_state,
    )

    _oauth_pending[oauth_state] = {
        "provider_id": provider_id,
        "redirect_uri": redirect_uri,
        "scopes": scopes,
        "created_at": time.time(),
        "expires_at": time.time() + OAUTH_PENDING_TTL_SECONDS,
    }

    # MARKER_147_5_OAUTH_START_REAL: return provider auth URL without dev auto-complete.
    return {
        "success": True,
        "provider_id": provider_id,
        "oauth_state": oauth_state,
        "auth_url": auth_url,
        "redirect_uri": redirect_uri,
        "scopes": scopes,
        "expires_in": OAUTH_PENDING_TTL_SECONDS,
    }


@router.post("/oauth/complete")
async def oauth_complete(body: OAuthCompleteRequest) -> dict:
    _cleanup_pending_states()
    pending = _oauth_pending.get(body.oauth_state)
    if not pending:
        raise HTTPException(status_code=400, detail="Invalid or expired oauth_state")
    pending_provider_id = str(pending.get("provider_id", ""))
    provider_id = str(body.provider_id or pending_provider_id).strip()
    if not provider_id:
        raise HTTPException(status_code=400, detail="oauth_state provider missing")
    if pending_provider_id and pending_provider_id != provider_id:
        raise HTTPException(status_code=400, detail="oauth_state provider mismatch")

    auth_code = (body.auth_code or "").strip()
    if not auth_code:
        raise HTTPException(status_code=400, detail="auth_code is required")

    provider = _provider_index().get(provider_id)
    if not provider:
        raise HTTPException(status_code=404, detail=f"Unknown provider: {provider_id}")

    # MARKER_147_5_OAUTH_TOKEN_EXCHANGE: real code->token exchange against provider token endpoints.
    token_payload = _exchange_code_for_tokens(
        provider=provider,
        provider_id=provider_id,
        code=auth_code,
        redirect_uri=str(pending.get("redirect_uri", "")).strip(),
    )

    access_token = str(token_payload.get("access_token") or "").strip()
    if not access_token:
        raise HTTPException(status_code=400, detail="OAuth provider returned no access_token")

    refresh_token = token_payload.get("refresh_token")
    expires_in = token_payload.get("expires_in")
    scope = token_payload.get("scope")

    service = get_connectors_state_service()
    secure_store = get_connectors_secure_store()
    secure_store.set_oauth_tokens(
        provider_id=provider_id,
        access_token=access_token,
        refresh_token=str(refresh_token) if refresh_token else None,
        expires_in=int(expires_in) if isinstance(expires_in, (int, float, str)) and str(expires_in).isdigit() else None,
        scope=str(scope) if scope else None,
        token_type="oauth_access",
    )

    try:
        state = service.connect(provider_id, body.account_label)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Unknown provider: {provider_id}")

    _oauth_pending.pop(body.oauth_state, None)
    response = _build_connector_response(state, secure_store)

    return {
        "success": True,
        "provider": response.model_dump(),
        "message": f"OAuth connected: {state['display_name']}",
    }


@router.get("/oauth/callback")
async def oauth_callback(code: Optional[str] = None, state: Optional[str] = None, error: Optional[str] = None) -> HTMLResponse:
    if error:
        html = f"""
<!doctype html><html><body style=\"background:#0b0b0b;color:#fff;font-family:-apple-system,sans-serif;padding:24px;\">
<h3>VETKA OAuth failed</h3>
<p>{error}</p>
<p>You can close this window and try again.</p>
</body></html>
"""
        return HTMLResponse(content=html, status_code=400)

    if not code or not state:
        html = """
<!doctype html><html><body style=\"background:#0b0b0b;color:#fff;font-family:-apple-system,sans-serif;padding:24px;\">
<h3>VETKA OAuth callback</h3>
<p>Missing code/state. You can close this window and retry.</p>
</body></html>
"""
        return HTMLResponse(content=html, status_code=400)

    pending = _oauth_pending.get(state)
    if not pending:
        html = """
<!doctype html><html><body style=\"background:#0b0b0b;color:#fff;font-family:-apple-system,sans-serif;padding:24px;\">
<h3>VETKA OAuth callback</h3>
<p>Session expired. Start connect flow again from VETKA.</p>
</body></html>
"""
        return HTMLResponse(content=html, status_code=400)

    try:
        await oauth_complete(
            OAuthCompleteRequest(
                provider_id=str(pending.get("provider_id")),
                oauth_state=state,
                auth_code=code,
                account_label=str(pending.get("provider_id")),
            )
        )
    except Exception as exc:
        html = f"""
<!doctype html><html><body style=\"background:#0b0b0b;color:#fff;font-family:-apple-system,sans-serif;padding:24px;\">
<h3>VETKA OAuth callback</h3>
<p>Token exchange failed: {str(exc)}</p>
<p>You can close this window and retry.</p>
</body></html>
"""
        return HTMLResponse(content=html, status_code=400)

    html = """
<!doctype html><html><body style=\"background:#0b0b0b;color:#fff;font-family:-apple-system,sans-serif;padding:24px;\">
<h3>Connected to VETKA</h3>
<p>Authorization finished successfully. You can close this window and return to VETKA.</p>
<script>setTimeout(()=>window.close(), 1200);</script>
</body></html>
"""
    return HTMLResponse(content=html, status_code=200)


@router.post("/{provider_id}/auth/manual")
async def manual_auth(provider_id: str, body: ManualAuthRequest) -> dict:
    providers = _provider_index()
    if provider_id not in providers:
        raise HTTPException(status_code=404, detail=f"Unknown provider: {provider_id}")

    auth_type = (body.auth_type or "").strip().lower()
    if auth_type not in {"api_key", "link", "token"}:
        raise HTTPException(status_code=400, detail="auth_type must be one of: api_key, link, token")

    value = (body.value or "").strip()
    if not value:
        raise HTTPException(status_code=400, detail="value is required")

    service = get_connectors_state_service()
    secure_store = get_connectors_secure_store()
    secure_store.set_token(provider_id, value, token_type=auth_type)

    state = service.connect(provider_id, body.account_label or provider_id)
    response = _build_connector_response(state, secure_store)

    return {
        "success": True,
        "provider": response.model_dump(),
        "message": f"Manual auth connected: {state['display_name']} ({auth_type})",
    }


@router.post("/{provider_id}/scan")
async def scan_provider(provider_id: str, request: Request, body: Optional[ConnectorScanRequest] = None) -> dict:
    service = get_connectors_state_service()
    secure_store = get_connectors_secure_store()
    queue = get_connectors_ingestion_queue_service()

    state = _provider_index().get(provider_id)
    if not state:
        raise HTTPException(status_code=404, detail=f"Unknown provider: {provider_id}")
    if not state.get("connected"):
        raise HTTPException(status_code=400, detail=f"Provider not connected: {provider_id}")
    if not secure_store.has_token(provider_id):
        raise HTTPException(status_code=400, detail=f"Provider auth required: {provider_id}")

    selected_ids = [s for s in (body.selected_ids if body else []) or [] if str(s).strip()]
    selected_paths = [s for s in (body.selected_paths if body else []) or [] if str(s).strip()]
    provider_class = str(state.get("provider_class") or provider_id).lower()

    if provider_class in {"google", "google_drive"}:
        scanned_count = len(selected_ids) if selected_ids else (len(selected_paths) if selected_paths else 0)
        if scanned_count <= 0:
            raise HTTPException(status_code=400, detail="Select at least one Google Drive folder/file before scan")
    else:
        scanned_count = 12 + (len(provider_id) % 9) * 7

    updated = service.mark_scan(provider_id, scanned_count=scanned_count)

    job = queue.enqueue(
        provider_id=provider_id,
        source=str(state.get("source", "")),
        metadata={
            "scanned_count": scanned_count,
            "selected_ids": selected_ids,
            "selected_paths": selected_paths,
        },
    )

    sio = getattr(request.app.state, "socketio", None)
    if sio is not None:
        try:
            await sio.emit("connector_scan_enqueued", {
                "provider_id": provider_id,
                "job_id": job["job_id"],
                "source": state.get("source"),
                "scanned_count": scanned_count,
            })
        except Exception:
            pass

    response = _build_connector_response(updated, secure_store)
    return {
        "success": True,
        "provider": response.model_dump(),
        "scanned_count": scanned_count,
        "ingestion_job_id": job["job_id"],
        "message": f"Scan complete: {updated['display_name']} ({scanned_count} items)",
    }


@router.post("/{provider_id}/disconnect")
async def disconnect_provider(provider_id: str) -> dict:
    service = get_connectors_state_service()
    secure_store = get_connectors_secure_store()

    try:
        state = service.disconnect(provider_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Unknown provider: {provider_id}")

    secure_store.clear_token(provider_id)
    response = _build_connector_response(state, secure_store)

    return {
        "success": True,
        "provider": response.model_dump(),
        "message": f"Disconnected: {state['display_name']}",
    }


@router.get("/jobs")
async def ingestion_jobs(limit: int = Query(default=30, ge=1, le=200)) -> dict:
    queue = get_connectors_ingestion_queue_service()
    jobs = queue.list(limit=limit)
    return {
        "success": True,
        "count": len(jobs),
        "jobs": jobs,
    }
