"""Exercise the actual production gateway without contacting a real database."""
from contextlib import asynccontextmanager
from pathlib import Path
import pytest
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.testclient import TestClient
from app.production import ProductionGateway, create_production_app

@pytest.fixture
def gateway(tmp_path):
    (tmp_path / 'index.html').write_text('<h1>Veritas frontend</h1>')
    (tmp_path / 'assets').mkdir()
    (tmp_path / 'assets' / 'app.js').write_text('console.log("frontend loaded");')
    async def health(request):
        return JSONResponse({'status': 'ok', 'database_ready': True})
    async def probe(request):
        return JSONResponse({'record': 'demo case data'})
    @asynccontextmanager
    async def lifespan(app):
        app.state.started = True
        yield
        app.state.stopped = True
    api = Starlette(routes=[Route('/health', health), Route('/api/v1/probe', probe, methods=['GET', 'POST']), Route('/docs', probe), Route('/openapi.json', probe)], lifespan=lifespan)
    return ProductionGateway(api, tmp_path), api


def test_frontend_api_and_documentation_are_public_without_login(gateway):
    app, _ = gateway
    with TestClient(app) as client:
        for path in ['/', '/guardian/case', '/api/v1/probe', '/docs', '/openapi.json', '/assets/app.js']:
            response = client.get(path, headers={'Accept': 'text/html'})
            assert response.status_code == 200
            assert 'www-authenticate' not in response.headers
        assert client.post('/api/v1/probe').json() == {'record': 'demo case data'}


def test_health_and_original_api_lifespan_work_without_a_login(gateway):
    app, api = gateway
    with TestClient(app) as client:
        assert api.state.started
        assert client.get('/health').json() == {'status': 'ok', 'database_ready': True}
    assert api.state.stopped


def test_serves_frontend_assets_and_spa_routes_but_not_api_fallbacks(gateway):
    app, _ = gateway
    with TestClient(app) as client:
        assert 'Veritas frontend' in client.get('/').text
        assert client.get('/assets/app.js').status_code == 200
        assert client.get('/guardian/case', headers={'Accept': 'text/html'}).status_code == 200
        assert client.get('/assets/missing.js', headers={'Accept': 'text/html'}).status_code == 404
        assert client.get('/assets/missing', headers={'Accept': 'text/html'}).status_code == 404
        assert client.get('/assets/', headers={'Accept': 'text/html'}).status_code == 404
        assert client.get('/api/v1/unknown', headers={'Accept': 'text/html'}).status_code == 404
        assert client.get('/backend/.env', headers={'Accept': 'text/html'}).status_code == 404
        assert client.get('/../backend/.env').status_code == 404


def test_browser_cross_origin_writes_are_rejected_and_responses_are_not_cached(gateway):
    app, _ = gateway
    with TestClient(app) as client:
        assert client.post('/api/v1/probe', headers={'Origin': 'https://untrusted.example'}).status_code == 403
        response = client.post('/api/v1/probe', headers={'Origin': 'http://testserver'})
        assert response.status_code == 200
        assert response.headers['cache-control'] == 'no-store'
        assert response.headers['x-content-type-options'] == 'nosniff'


def test_production_starts_without_login_credentials_and_requires_frontend(tmp_path, monkeypatch):
    monkeypatch.delenv('DEPLOY_USERNAME', raising=False)
    monkeypatch.delenv('DEPLOY_PASSWORD', raising=False)
    monkeypatch.setenv('VERITAS_FRONTEND_DIR', str(tmp_path))
    (tmp_path / 'index.html').write_text('<h1>Veritas frontend</h1>')
    assert isinstance(create_production_app(), ProductionGateway)
    with pytest.raises(ValueError, match='index.html'):
        ProductionGateway(Starlette(), tmp_path / 'missing')
