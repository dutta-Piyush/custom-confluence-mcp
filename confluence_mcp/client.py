from __future__ import annotations

import httpx

from confluence_mcp.config import CONFLUENCE_PAT, VERIFY_SSL


class ConfluenceError(Exception):
    """Raised when the Confluence API returns an error."""


class _ConfluenceClient(httpx.Client):
    """HTTP client that converts Confluence API errors to user-friendly messages."""

    def _check(self, resp: httpx.Response) -> httpx.Response:
        try:
            resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            code = e.response.status_code
            msgs = {
                401: "Unauthorized \u2014 check your CONFLUENCE_PAT",
                403: "Forbidden \u2014 your PAT may lack permissions for this operation",
                404: "Not found \u2014 page or resource does not exist",
                409: "Conflict \u2014 page was modified by someone else, try again",
            }
            raise ConfluenceError(
                msgs.get(code, f"Confluence API error {code}: {e.response.text[:200]}")
            ) from e
        return resp

    def get(self, *args, **kwargs) -> httpx.Response:  # type: ignore[override]
        return self._check(super().get(*args, **kwargs))

    def post(self, *args, **kwargs) -> httpx.Response:  # type: ignore[override]
        return self._check(super().post(*args, **kwargs))

    def put(self, *args, **kwargs) -> httpx.Response:  # type: ignore[override]
        return self._check(super().put(*args, **kwargs))

    def delete(self, *args, **kwargs) -> httpx.Response:  # type: ignore[override]
        return self._check(super().delete(*args, **kwargs))


def _headers() -> dict:
    if not CONFLUENCE_PAT:
        raise ConfluenceError("CONFLUENCE_PAT environment variable is not set")
    return {
        "Authorization": f"Bearer {CONFLUENCE_PAT}",
        "Accept": "application/json",
    }


def _client() -> _ConfluenceClient:
    return _ConfluenceClient(
        headers=_headers(),
        verify=VERIFY_SSL,
        timeout=httpx.Timeout(total=60, connect=10),
        trust_env=False,
    )
