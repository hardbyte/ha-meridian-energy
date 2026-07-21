"""Meridian Energy API client.

Meridian's current customer portal (app.meridianenergy.nz) authenticates via
an emailed one-time code rather than a password: request an OTP, verify it to
get a Firebase custom token, then exchange that for a Firebase ID/refresh
token pair. Data is served from a GraphQL API ("Kraken") authenticated with
that ID token as a bearer token.

This flow, the Firebase project config, and the GraphQL query shapes below
were reverse engineered from Meridian's own public web app bundle -- there is
no published API documentation.
"""

from __future__ import annotations

import logging
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx

from .const import (
    AUTH_BASE_URL,
    BRAND,
    DEFAULT_TIMEZONE,
    FIREBASE_API_KEY,
    GRAPHQL_URL,
    IDENTITY_TOOLKIT_URL,
    SECURE_TOKEN_URL,
)
from .queries import ACCOUNTS_LIST_QUERY, MEASUREMENTS_ALL_PROPERTIES_QUERY

_LOGGER = logging.getLogger(__name__)

_CLIENT_HEADERS = {"X-Client-Platform": "web"}

# Refresh this many seconds before the token's actual expiry to avoid racing
# a request against expiry.
_EXPIRY_SAFETY_MARGIN = timedelta(seconds=60)


class MeridianEnergyError(Exception):
    """Base error for the Meridian Energy client."""


class MeridianAuthError(MeridianEnergyError):
    """Raised when authentication fails."""


class MeridianApiError(MeridianEnergyError):
    """Raised when the GraphQL API returns an error."""


@dataclass
class MeridianTokenSet:
    """A Firebase ID/refresh token pair."""

    id_token: str
    refresh_token: str
    expires_at: datetime

    @property
    def is_expired(self) -> bool:
        """Whether this token is expired (with a safety margin)."""
        return datetime.now(UTC) >= self.expires_at - _EXPIRY_SAFETY_MARGIN

    def to_dict(self) -> dict[str, Any]:
        """Serialise for storage in a config entry."""
        return {
            "id_token": self.id_token,
            "refresh_token": self.refresh_token,
            "expires_at": self.expires_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MeridianTokenSet:
        """Deserialise from a config entry."""
        return cls(
            id_token=data["id_token"],
            refresh_token=data["refresh_token"],
            expires_at=datetime.fromisoformat(data["expires_at"]),
        )


OnTokenUpdate = Callable[[MeridianTokenSet], Awaitable[None]]


class MeridianEnergyAuth(httpx.Auth):
    """Handles the OTP sign-in flow and transparent token refresh.

    Mirrors the evnex integration's EvnexAuth: a central httpx.Auth that
    injects the bearer token and refreshes on expiry or a 401, persisting
    the new tokens via an on_token_update callback before they're used.
    """

    requires_response_body = True

    def __init__(
        self,
        tokens: MeridianTokenSet | None = None,
        on_token_update: OnTokenUpdate | None = None,
    ) -> None:
        """Initialise, optionally with a previously-persisted token set."""
        self._tokens = tokens
        self._on_token_update = on_token_update

    @property
    def tokens(self) -> MeridianTokenSet | None:
        """The current token set, if signed in."""
        return self._tokens

    async def request_otp(self, client: httpx.AsyncClient, email: str) -> str:
        """Request an emailed OTP code. Returns a journey_id for verify_otp."""
        journey_id = str(uuid.uuid4())
        response = await client.post(
            f"{AUTH_BASE_URL}/cf/email-connector",
            json={
                "email": email,
                "brand": BRAND,
                "redirectUrl": "",
                "journeyId": journey_id,
                "otpEnabled": True,
            },
            headers=_CLIENT_HEADERS,
        )
        if response.status_code == 403:
            raise MeridianAuthError("Brand access denied")
        if response.status_code == 404:
            raise MeridianAuthError("No Meridian account found for that email")
        if not response.is_success:
            raise MeridianAuthError(
                f"Failed to request OTP: {response.status_code} {response.text}"
            )
        return journey_id

    async def verify_otp(
        self, client: httpx.AsyncClient, email: str, otp: str, journey_id: str
    ) -> MeridianTokenSet:
        """Verify the emailed OTP and complete sign-in."""
        response = await client.post(
            f"{AUTH_BASE_URL}/cf/email-otp-authenticator",
            json={
                "email": email,
                "otp": otp,
                "brand": BRAND,
                "journeyId": journey_id,
            },
            headers=_CLIENT_HEADERS,
        )
        data = response.json()
        if not response.is_success:
            raise MeridianAuthError(data.get("error") or "Failed to validate OTP")

        custom_token = data["customToken"]
        tokens = await self._exchange_custom_token(client, custom_token)
        self._tokens = tokens
        if self._on_token_update is not None:
            await self._on_token_update(tokens)
        return tokens

    async def _exchange_custom_token(
        self, client: httpx.AsyncClient, custom_token: str
    ) -> MeridianTokenSet:
        """Exchange a Firebase custom token for an ID/refresh token pair."""
        response = await client.post(
            f"{IDENTITY_TOOLKIT_URL}/accounts:signInWithCustomToken",
            params={"key": FIREBASE_API_KEY},
            json={"token": custom_token, "returnSecureToken": True},
        )
        if not response.is_success:
            raise MeridianAuthError(
                f"Failed to exchange custom token: {response.status_code} {response.text}"
            )
        payload = response.json()
        return MeridianTokenSet(
            id_token=payload["idToken"],
            refresh_token=payload["refreshToken"],
            expires_at=datetime.now(UTC) + timedelta(seconds=int(payload["expiresIn"])),
        )

    async def _refresh(self, client: httpx.AsyncClient) -> None:
        """Use the refresh token to obtain a new ID token."""
        assert self._tokens is not None
        response = await client.post(
            SECURE_TOKEN_URL,
            params={"key": FIREBASE_API_KEY},
            data={
                "grant_type": "refresh_token",
                "refresh_token": self._tokens.refresh_token,
            },
        )
        if not response.is_success:
            raise MeridianAuthError(
                f"Failed to refresh session: {response.status_code} {response.text}"
            )
        payload = response.json()
        self._tokens = MeridianTokenSet(
            id_token=payload["id_token"],
            refresh_token=payload["refresh_token"],
            expires_at=datetime.now(UTC) + timedelta(seconds=int(payload["expires_in"])),
        )
        if self._on_token_update is not None:
            await self._on_token_update(self._tokens)

    def auth_flow(self, request: httpx.Request):  # pragma: no cover - sync API unused
        """Not supported; this client is async-only."""
        raise NotImplementedError("MeridianEnergyAuth is async-only")

    async def async_auth_flow(self, request: httpx.Request):
        """Attach a bearer token, refreshing first if it's expired or rejected."""
        if self._tokens is None:
            raise MeridianAuthError("Not authenticated")

        if self._tokens.is_expired:
            async with httpx.AsyncClient() as client:
                await self._refresh(client)

        request.headers["Authorization"] = f"Bearer {self._tokens.id_token}"
        response = yield request

        if response.status_code == 401:
            async with httpx.AsyncClient() as client:
                await self._refresh(client)
            request.headers["Authorization"] = f"Bearer {self._tokens.id_token}"
            yield request


class MeridianEnergyApi:
    """Thin GraphQL client for the Meridian Kraken API."""

    def __init__(self, auth: MeridianEnergyAuth, httpx_client: httpx.AsyncClient) -> None:
        """Initialise with an auth handler and a shared httpx client."""
        self._auth = auth
        self._client = httpx_client

    async def _graphql(
        self, operation_name: str, query: str, variables: dict[str, Any]
    ) -> dict[str, Any]:
        """Execute a single GraphQL operation and return its `data` payload."""
        response = await self._client.post(
            GRAPHQL_URL,
            json={
                "operationName": operation_name,
                "query": query,
                "variables": variables,
            },
            auth=self._auth,
        )
        response.raise_for_status()
        payload = response.json()
        if payload.get("errors"):
            raise MeridianApiError(str(payload["errors"]))
        return payload["data"]

    async def get_accounts(self) -> list[dict[str, Any]]:
        """List the accounts (ICPs/properties) visible to the signed-in user."""
        data = await self._graphql("accountsList", ACCOUNTS_LIST_QUERY, {})
        return data["viewer"]["accounts"]

    async def get_measurements(
        self,
        account_number: str,
        *,
        start_at: datetime,
        end_at: datetime,
        first: int = 5000,
        timezone: str = DEFAULT_TIMEZONE,
    ) -> list[dict[str, Any]]:
        """Fetch interval usage (and cost, where available) for an account."""
        variables = {
            "accountNumber": account_number,
            "first": first,
            "startAt": start_at.isoformat(),
            "endAt": end_at.isoformat(),
            "timezone": timezone,
        }
        data = await self._graphql(
            "measurementsAllProperties", MEASUREMENTS_ALL_PROPERTIES_QUERY, variables
        )
        return data["account"]["properties"]
