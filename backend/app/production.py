"""Public, same-origin demo hosting; the local API stays unchanged."""
import os
from pathlib import Path
from urllib.parse import urlsplit

from starlette.datastructures import Headers
from starlette.exceptions import HTTPException
from starlette.responses import FileResponse, PlainTextResponse
from starlette.staticfiles import StaticFiles
from starlette.types import ASGIApp, Message, Receive, Scope, Send


class ProductionGateway:
    """Serve the public hackathon UI and API from one origin."""

    def __init__(self, api: ASGIApp, directory: Path):
        self.directory = directory.resolve()
        if not (self.directory / 'index.html').is_file():
            raise ValueError('Build the frontend first: index.html is missing')
        self.api = api
        self.static = StaticFiles(directory=self.directory, html=True)

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

    directory = Path(os.getenv('VERITAS_FRONTEND_DIR', str(Path(__file__).resolve().parents[2] / 'frontend' / 'dist')))
    return ProductionGateway(app, directory)


if __name__ == '__main__':
    import uvicorn

    # Exactly one worker: the existing API owns its persisted job worker.
    uvicorn.run(create_production_app(), host='0.0.0.0', port=int(os.getenv('PORT', '8000')), proxy_headers=True, workers=1)
