"""Keitaro Admin API integration; no API credentials are sent to the browser."""
import httpx
from fastapi import HTTPException
from .config import get_settings

class Keitaro:
    def __init__(self, client: httpx.AsyncClient | None = None):
        settings = get_settings()
        if not settings.keitaro_api_key:
            raise HTTPException(status_code=503, detail='KEITARO_API_KEY is not configured')
        self.client = client or httpx.AsyncClient(
            base_url=settings.keitaro_url.rstrip('/') + '/admin_api/v1/',
            headers={'Api-Key': settings.keitaro_api_key},
            timeout=25,
            follow_redirects=False,
        )
        self.owned = client is None

    async def __aenter__(self): return self
    async def __aexit__(self, *_):
        if self.owned: await self.client.aclose()

    async def request(self, method: str, path: str, **kwargs):
        try:
            response = await self.client.request(method, path.lstrip('/'), **kwargs)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            # Do not leak upstream headers, URLs, or auth credentials.
            raise HTTPException(status_code=502, detail=f'Keitaro returned HTTP {exc.response.status_code}: {exc.response.text[:350]}') from exc
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=502, detail=f'Cannot connect to Keitaro: {type(exc).__name__}') from exc
        if response.status_code == 204 or not response.content: return {}
        try: return response.json()
        except ValueError as exc: raise HTTPException(status_code=502, detail='Keitaro returned invalid JSON') from exc

    async def get(self, path: str, **kwargs): return await self.request('GET', path, **kwargs)
    async def post(self, path: str, payload: dict): return await self.request('POST', path, json=payload)
    async def put(self, path: str, payload: dict): return await self.request('PUT', path, json=payload)
    async def delete(self, path: str): return await self.request('DELETE', path)

    async def streams(self, campaign_id: int):
        result = await self.get(f'campaigns/{campaign_id}/streams')
        # Some tracker versions return a complete list regardless of query parameter.
        items = result if isinstance(result, list) else result.get('data', [])
        return [x for x in items if int(x.get('campaign_id', -1)) == campaign_id]

    async def ensure_offer(self, offer_id: int):
        item = await self.get(f'offers/{offer_id}')
        if not isinstance(item, dict) or int(item.get('id', -1)) != offer_id:
            raise HTTPException(404, 'Offer not found in Keitaro')
        return item
