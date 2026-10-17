"""Exercise the actual production gateway without contacting a real database."""
from contextlib import asynccontextmanager
from pathlib import Path
import pytest
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.testclient import TestClient
from app.production import ProductionGateway, create_production_app

USER = 'veritas-judge'
PASSWORD = 'local-test-password-not-a-real-credential'


@pytest.fixture
def gateway(tmp_path):
    (tmp_path / 'index.html').write_text('<h1>Veritas frontend</h1>')
    (tmp_path / 'assets').mkdir()
    (tmp_path / 'assets' / 'app.js').write_text('console.log("frontend loaded");')
    async def health(request):
        return JSONResponse({'status': 'ok', 'database_ready': True})
    async def probe(request):
        return JSONResponse({'record': 'private case data'})
    @asynccontextmanager
    async def lifespan(app):
        app.state.started = True
        yield
        app.state.stopped = True
    api = Starlette(routes=[Route('/health', health), Route('/api/v1/probe', probe, methods=['GET', 'POST'])], lifespan=lifespan)
    return ProductionGateway(api, tmp_path, USER, PASSWORD), api


def test_authentication_protects_frontend_api_and_documentation(gateway):
    app, _ = gateway
    with TestClient(app) as client:
        for path in ['/', '/guardian/case', '/api/v1/probe', '/docs', '/openapi.json', '/assets/app.js']:
            response = client.get(path)
            assert response.status_code == 401
            assert response.headers['www-authenticate'].startswith('Basic ')
            assert 'private case data' not in response.text
        assert client.get('/api/v1/probe', auth=(USER, 'wrong')).status_code == 401
        assert client.get('/api/v1/probe', auth=(USER, PASSWORD)).json() == {'record': 'private case data'}


def test_health_and_original_api_lifespan_work_without_a_login(gateway):
    app, api = gateway
    with TestClient(app) as client:
        assert api.state.started
        assert client.get('/health').json() == {'status': 'ok', 'database_ready': True}
    assert api.state.stopped


def test_serves_frontend_assets_and_spa_routes_but_not_api_fallbacks(gateway):
    app, _ = gateway
    with TestClient(app) as client:
        client.auth = (USER, PASSWORD)
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
        client.auth = (USER, PASSWORD)
        assert client.post('/api/v1/probe', headers={'Origin': 'https://untrusted.example'}).status_code == 403
        response = client.post('/api/v1/probe', headers={'Origin': 'http://testserver'})
        assert response.status_code == 200
        assert response.headers['cache-control'] == 'no-store'
        assert response.headers['x-content-type-options'] == 'nosniff'


def test_production_refuses_missing_login_credentials_or_frontend(tmp_path, monkeypatch):
    monkeypatch.delenv('DEPLOY_USERNAME', raising=False)
    monkeypatch.delenv('DEPLOY_PASSWORD', raising=False)
    with pytest.raises(RuntimeError, match='DEPLOY_'):
        create_production_app()
    with pytest.raises(ValueError, match='password'):
        ProductionGateway(Starlette(), tmp_path, USER, 'short')
    with pytest.raises(ValueError, match='index.html'):
        ProductionGateway(Starlette(), tmp_path, USER, PASSWORD)
