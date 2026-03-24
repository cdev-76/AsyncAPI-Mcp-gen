"""
OAuth2 Authorization Code flow handler for the MCP server.
Manages token acquisition via browser login, silent refresh via refresh_token,
and persistent storage. Used as the OAUTHBEARER callback for confluent-kafka.
"""
import json
import os
import secrets
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlencode, urlparse

import requests

TOKEN_FILE = '.oauth_tokens.json'
REDIRECT_PORT = 8888
REDIRECT_URI = f'http://localhost:{REDIRECT_PORT}/callback'


class TokenStore:

    def __init__(self, path: str = TOKEN_FILE):
        self._path = path

    def save(self, tokens: dict) -> None:
        tokens['saved_at'] = time.time()
        with open(self._path, 'w') as f:
            json.dump(tokens, f, indent=2)
        os.chmod(self._path, 0o600)  # owner read/write only

    def load(self) -> dict | None:
        if not os.path.exists(self._path):
            return None
        with open(self._path) as f:
            return json.load(f)

    def is_access_valid(self, tokens: dict, buffer: int = 30) -> bool:
        '''Returns True if the access token is still valid (with a safety buffer).'''
        expires_at = tokens.get('saved_at', 0) + tokens.get('expires_in', 0)
        return time.time() < expires_at - buffer

    def clear(self) -> None:
        if os.path.exists(self._path):
            os.remove(self._path)


_store = TokenStore()


def _exchange_code(code: str) -> dict:
    '''Exchange an authorization code for tokens.'''
    resp = requests.post(
        os.getenv('OAUTH_TOKEN_URL', ''),
        data={
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': REDIRECT_URI,
            'client_id': os.getenv('OAUTH_CLIENT_ID', ''),
            'client_secret': os.getenv('OAUTH_CLIENT_SECRET', ''),
        },
        headers={'Content-Type': 'application/x-www-form-urlencoded'},
    )
    resp.raise_for_status()
    return resp.json()


def _refresh(refresh_token: str) -> dict:
    '''Use a refresh token to silently obtain a new access token.'''
    resp = requests.post(
        os.getenv('OAUTH_TOKEN_URL', ''),
        data={
            'grant_type': 'refresh_token',
            'refresh_token': refresh_token,
            'client_id': os.getenv('OAUTH_CLIENT_ID', ''),
            'client_secret': os.getenv('OAUTH_CLIENT_SECRET', ''),
        },
        headers={'Content-Type': 'application/x-www-form-urlencoded'},
    )
    resp.raise_for_status()
    return resp.json()


def _run_browser_flow() -> dict:
    '''
    Open the browser for user login, start a local HTTP server to catch the
    authorization code callback, and exchange it for tokens.
    '''
    state = secrets.token_urlsafe(16)
    auth_url = os.getenv('OAUTH_AUTH_URL', '')
    params = {
        'response_type': 'code',
        'client_id': os.getenv('OAUTH_CLIENT_ID', ''),
        'redirect_uri': REDIRECT_URI,
        'scope': 'openid profile email',
        'state': state,
    }
    full_url = f'{auth_url}?{urlencode(params)}'

    result = {}

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if not self.path.startswith('/callback'):
                self.send_response(404)
                self.end_headers()
                return
            qs = parse_qs(urlparse(self.path).query)
            if qs.get('state', [None])[0] != state:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b'Invalid state parameter.')
                return
            result['code'] = qs.get('code', [None])[0]
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'<html><body><h2>Authentication successful. You can close this tab.</h2></body></html>')

        def log_message(self, *args):
            pass  # suppress HTTP server logs

    server = HTTPServer(('localhost', REDIRECT_PORT), Handler)
    server.timeout = 120  # 2 minutes to complete login

    print(f'\nOpening browser for authentication...')
    print(f'If the browser does not open, visit:\n  {full_url}\n')
    webbrowser.open(full_url)
    server.handle_request()
    server.server_close()

    if 'code' not in result:
        raise RuntimeError('Authentication failed: no authorization code received.')

    return _exchange_code(result['code'])


def get_valid_tokens() -> dict:
    '''
    Return valid tokens. Strategy:
      1. Load stored tokens — return if access token is still valid.
      2. If expired but refresh_token exists — refresh silently.
      3. Otherwise — trigger browser login flow.
    '''
    tokens = _store.load()

    if tokens:
        if _store.is_access_valid(tokens):
            return tokens
        if tokens.get('refresh_token'):
            try:
                tokens = _refresh(tokens['refresh_token'])
                _store.save(tokens)
                print('OAuth2 token refreshed silently.')
                return tokens
            except Exception as e:
                print(f'Token refresh failed ({e}), re-authenticating...')

    tokens = _run_browser_flow()
    _store.save(tokens)
    print('OAuth2 authentication successful.')
    return tokens


def fetch_oauth_token_authcode(config_str: str):
    '''
    OAUTHBEARER callback for confluent-kafka using authorization_code flow.
    Called automatically by the Kafka client when a token is needed or has expired.

    :param config_str: Value of sasl.oauthbearer.config (unused, required by callback signature)
    :returns: Tuple of (access_token, expiry_unix_timestamp_seconds)
    '''
    tokens = get_valid_tokens()
    # Use the actual expiry (saved_at + expires_in), not time.time() + expires_in.
    # If we return a future timestamp for a token that expires sooner, Kafka will keep
    # presenting it after it has already expired and the broker will reject it.
    expiry = tokens.get('saved_at', time.time()) + float(tokens.get('expires_in', 300))
    return tokens['access_token'], expiry
