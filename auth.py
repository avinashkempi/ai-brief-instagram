#!/usr/bin/env python3
"""One-time local helper for the Instagram Login OAuth exchange."""

from __future__ import annotations

import getpass
import json
import secrets
import urllib.parse
import urllib.request


def request_json(url: str, data: dict | None = None) -> dict:
    payload = None if data is None else urllib.parse.urlencode(data).encode()
    request = urllib.request.Request(url, data=payload, headers={"User-Agent": "AIBriefPublisher/1.0"})
    with urllib.request.urlopen(request, timeout=40) as response:
        return json.loads(response.read())


repo_owner = input("GitHub username (case-sensitive as shown in the Pages URL): ").strip()
repo_name = input("Public repository name: ").strip()
app_id = input("Meta app ID: ").strip()
redirect_uri = f"https://{repo_owner}.github.io/{repo_name}/oauth-callback/"
state = secrets.token_urlsafe(24)
params = urllib.parse.urlencode({
    "client_id": app_id,
    "redirect_uri": redirect_uri,
    "response_type": "code",
    "scope": "instagram_business_basic,instagram_business_content_publish",
    "enable_fb_login": "0",
    "state": state,
})
print("\n1. Open this URL in your browser and approve the requested Instagram permissions:\n")
print(f"https://www.instagram.com/oauth/authorize?{params}\n")
print(f"2. After redirect, confirm the callback URL's `state` value is exactly {state}.")
print("   If it differs, stop and run this helper again. Then copy the callback URL's `code` value.")
returned_state = input("Paste the callback URL's state value: ").strip()
if not secrets.compare_digest(state, returned_state):
    raise SystemExit("OAuth state did not match. Stop and restart the authorization flow.")
code = input("Paste the one-time authorization code here: ").strip().rstrip("#")
app_secret = getpass.getpass("Meta app secret (hidden while typing): ").strip()

short = request_json("https://api.instagram.com/oauth/access_token", {
    "client_id": app_id,
    "client_secret": app_secret,
    "grant_type": "authorization_code",
    "redirect_uri": redirect_uri,
    "code": code,
})
long_lived = request_json("https://graph.instagram.com/access_token?" + urllib.parse.urlencode({
    "grant_type": "ig_exchange_token",
    "client_secret": app_secret,
    "access_token": short["access_token"],
}))

print("\nAdd these values in your GitHub repository Settings → Secrets and variables → Actions:")
print(f"IG_USER_ID = {short['user_id']}")
print("IG_ACCESS_TOKEN = " + long_lived["access_token"])
print(f"Token lifetime returned by Meta: {int(long_lived.get('expires_in', 0)) // 86400} days")
print("\nKeep these values private. This helper does not save them to disk.")
