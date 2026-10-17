"""Authenticated, same-origin demo hosting; the local API stays unchanged."""
import base64
import binascii
import hmac
import os
from pathlib import Path
from urllib.parse import urlsplit

from starlette.datastructures import Headers
from starlette.exceptions import HTTPException
from starlette.responses import FileResponse, PlainTextResponse
from starlette.staticfiles import StaticFiles
from starlette.types import ASGIApp, Message, Receive, Scope, Send


class ProductionGateway:
    """One shared judge account protects all case data, UI assets and API docs."""

    def __init__(self, api: ASGIApp, directory: Path, username: str, password: str):
        if not username or ':' in username or len(password) < 16:
            raise ValueError('Set a username and a password of at least 16 characters')
        self.directory = directory.resolve()
        if not (self.directory / 'index.html').is_file():
            raise ValueError('Build the frontend first: index.html is missing')
        self.api = api
        self.username = username.encode('utf-8')
        self.password = password.encode('utf-8')
        self.static = StaticFiles(directory=self.directory, html=True)

    def _authenticated(self, headers: Headers) -> bool:
        try:
            scheme, token = headers.get('authorization', '').split(' ', 1)
            if scheme.lower() != 'basic':
                return False
            username, password = base64.b64decode(token, validate=True).split(b':', 1)
            # Evaluate both comparisons, including for an incorrect username.
            return hmac.compare_digest(username, self.username) & hmac.compare_digest(password, self.password)
        except (ValueError, binascii.Error):
            return False

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope['type'] == 'lifespan':
            await self.api(scope, receive, send)
            return
        if scope['type'] != 'http':
            if scope['type'] == 'websocket':
                await send({'type': 'websocket.close', 'code': 1008})
            return

        async def protected_send(message: Message):
            if message['type'] == 'http.response.start':
                security = {
                    b'cache-control': b'no-store',
                    b'x-content-type-options': b'nosniff',
                    b'x-frame-options': b'DENY',
                    b'referrer-policy': b'no-referrer',
                }
                message['headers'] = [
                    (key, value) for key, value in message.get('headers', [])
                    if key.lower() not in security
                ] + list(security.items())
            await send(message)

        path = scope['path']
        headers = Headers(scope=scope)
        if path == '/health' and scope['method'] in ('GET', 'HEAD'):
            await self.api(scope, receive, protected_send)
            return
        if not self._authenticated(headers):
            response = PlainTextResponse('Judge login required', status_code=401, headers={
                'WWW-Authenticate': 'Basic realm="Veritas demo", charset="UTF-8"',
            })
            await response(scope, receive, protected_send)
            return

        if scope['method'] not in ('GET', 'HEAD', 'OPTIONS'):
            origin = headers.get('origin')
            # Compare the browser origin to the original public Host. TLS may
            # terminate at the cloud proxy, so the internal ASGI scheme differs.
            try:
                parsed = urlsplit(origin) if origin else None
                wrong_origin = parsed is not None and (
                    parsed.scheme not in ('http', 'https') or parsed.netloc.lower() != headers.get('host', '').lower()
                )
            except ValueError:
                wrong_origin = True
            if wrong_origin or headers.get('sec-fetch-site') == 'cross-site':
                await PlainTextResponse('Cross-origin write rejected', status_code=403)(scope, receive, protected_send)
                return

        if path == '/api' or path.startswith('/api/') or path in ('/docs', '/docs/oauth2-redirect', '/openapi.json', '/redoc'):
            await self.api(scope, receive, protected_send)
            return
        if any(part.startswith('.') for part in path.split('/') if part):
            await PlainTextResponse('Not Found', status_code=404)(scope, receive, protected_send)
            return
        try:
            await self.static(scope, receive, protected_send)
        except HTTPException as exc:
            # Only navigation routes get the SPA shell. Missing assets and
            # API paths must retain real 404 responses.
            asset_path = path == '/assets' or path.startswith('/assets/')
            if exc.status_code == 404 and not asset_path and scope['method'] in ('GET', 'HEAD') and '.' not in path.rsplit('/', 1)[-1] and 'text/html' in headers.get('accept', ''):
                await FileResponse(self.directory / 'index.html')(scope, receive, protected_send)
            else:
                await PlainTextResponse('Not Found' if exc.status_code == 404 else 'Method Not Allowed', status_code=exc.status_code)(scope, receive, protected_send)


def create_production_app() -> ProductionGateway:
    # Importing the existing API loads ignored backend/.env for local rehearsal.
    from .main import app

    username = os.getenv('DEPLOY_USERNAME', '')
    password = os.getenv('DEPLOY_PASSWORD', '')
    if not username or not password:
        raise RuntimeError('Production requires DEPLOY_USERNAME and DEPLOY_PASSWORD')
    directory = Path(os.getenv('VERITAS_FRONTEND_DIR', str(Path(__file__).resolve().parents[2] / 'frontend' / 'dist')))
    return ProductionGateway(app, directory, username, password)


if __name__ == '__main__':
    import uvicorn

    # Exactly one worker: the existing API owns its persisted job worker.
    uvicorn.run(create_production_app(), host='0.0.0.0', port=int(os.getenv('PORT', '8000')), proxy_headers=True, workers=1)
