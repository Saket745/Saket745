"""Minimal GitHub REST + GraphQL client, stdlib-only.

Token resolution order (least-privilege first, all optional except the last):
  1. APP_INSTALLATION_TOKEN  - short-lived (1h) token minted in-workflow from a
                                GitHub App installation. Preferred: auto-expires,
                                scoped to exactly the permissions the App was
                                granted, never stored anywhere.
  2. STATS_PAT               - a fine-grained personal access token, only needed
                                if you want private-repo contributions folded
                                into the lifetime totals. Long-lived, so keep
                                its scope minimal (read-only) and set an
                                expiry.
  3. GITHUB_TOKEN             - the token GitHub injects into every Actions run
                                automatically. Zero setup, but only sees public
                                data about the account. This is the safe
                                default and the only one required to run.

No token is ever written to disk, logged, or committed. Only the *data* this
client returns is persisted (into data/stats.json).
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
from urllib.request import Request, urlopen

API_VERSION = "2022-11-28"
USER_AGENT = "profile-intelligence-system"


def resolve_token() -> tuple[str, str]:
    """Return (token, source_label) using the priority order above."""
    for env_name, label in (
        ("APP_INSTALLATION_TOKEN", "github-app-installation-token"),
        ("STATS_PAT", "fine-grained-pat"),
        ("GITHUB_TOKEN", "default-actions-token"),
    ):
        value = os.getenv(env_name, "").strip()
        if value:
            return value, label
    return "", "unauthenticated"


class GitHubClient:
    def __init__(self, token: str | None = None, source: str = "unknown", max_retries: int = 3):
        self.token, self.source = (token, source) if token is not None else resolve_token()
        self.max_retries = max_retries

    def _headers(self, extra: dict | None = None) -> dict:
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": USER_AGENT,
            "X-GitHub-Api-Version": API_VERSION,
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        if extra:
            headers.update(extra)
        return headers

    def _request(self, req: Request):
        last_error = None
        for attempt in range(self.max_retries):
            try:
                with urlopen(req, timeout=30) as response:
                    remaining = response.headers.get("X-RateLimit-Remaining")
                    if remaining is not None and int(remaining) < 50:
                        print(f"::warning::GitHub API rate limit low ({remaining} remaining)")
                    return json.load(response)
            except urllib.error.HTTPError as exc:
                last_error = exc
                if exc.code in (403, 429) and attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)
                    continue
                raise
            except urllib.error.URLError as exc:
                last_error = exc
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)
                    continue
                raise
        raise last_error  # pragma: no cover

    def get(self, url: str):
        return self._request(Request(url, headers=self._headers()))

    def get_paginated(self, url: str, per_page: int = 100, max_pages: int = 10) -> list:
        results = []
        separator = "&" if "?" in url else "?"
        for page in range(1, max_pages + 1):
            batch = self.get(f"{url}{separator}per_page={per_page}&page={page}")
            if not batch:
                break
            results.extend(batch)
            if len(batch) < per_page:
                break
        return results

    def graphql(self, query: str, variables: dict) -> dict:
        payload = json.dumps({"query": query, "variables": variables}).encode("utf-8")
        req = Request(
            "https://api.github.com/graphql",
            data=payload,
            headers=self._headers({"Content-Type": "application/json"}),
            method="POST",
        )
        body = self._request(req)
        if body.get("errors"):
            raise RuntimeError("; ".join(e.get("message", "GraphQL error") for e in body["errors"]))
        return body["data"]

    def post(self, url: str, payload: dict):
        req = Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers=self._headers({"Content-Type": "application/json"}),
            method="POST",
        )
        return self._request(req)
