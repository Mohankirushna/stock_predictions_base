"""Google OAuth (authorization-code flow), implemented directly over httpx —
no framework session middleware required. The API layer generates and
verifies the CSRF `state` value itself (signed, short-lived JWT)."""
from dataclasses import dataclass
from urllib.parse import urlencode

import httpx

from app.core.config import AuthSettings
from app.core.errors import ExternalServiceError

_AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
_TOKEN_URL = "https://oauth2.googleapis.com/token"
_USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"


@dataclass(frozen=True)
class GoogleUserInfo:
    sub: str
    email: str
    email_verified: bool
    name: str


class GoogleOAuthClient:
    def __init__(self, settings: AuthSettings) -> None:
        self._settings = settings

    def authorize_url(self, state: str) -> str:
        params = {
            "client_id": self._settings.google_client_id,
            "redirect_uri": self._settings.google_redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
            "access_type": "online",
            "prompt": "select_account",
        }
        return f"{_AUTHORIZE_URL}?{urlencode(params)}"

    async def exchange_code(self, code: str) -> GoogleUserInfo:
        async with httpx.AsyncClient(timeout=10.0) as client:
            token_resp = await client.post(
                _TOKEN_URL,
                data={
                    "code": code,
                    "client_id": self._settings.google_client_id,
                    "client_secret": self._settings.google_client_secret,
                    "redirect_uri": self._settings.google_redirect_uri,
                    "grant_type": "authorization_code",
                },
            )
            if token_resp.status_code != 200:
                raise ExternalServiceError("google token exchange failed", {"body": token_resp.text})
            access_token = token_resp.json()["access_token"]

            info_resp = await client.get(
                _USERINFO_URL, headers={"Authorization": f"Bearer {access_token}"}
            )
            if info_resp.status_code != 200:
                raise ExternalServiceError("google userinfo fetch failed", {"body": info_resp.text})
            data = info_resp.json()

        return GoogleUserInfo(
            sub=data["sub"],
            email=data["email"],
            email_verified=bool(data.get("email_verified", False)),
            name=data.get("name", ""),
        )
