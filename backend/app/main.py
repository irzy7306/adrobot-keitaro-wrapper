from datetime import date
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from .config import get_settings
from .db import get_db
from .keitaro import Keitaro
from .schemas import CampaignCreate, OfferAdd, OfferRemove, ReportRequest
from .service import create_campaign, update_stream_offers, offer_entries

app = FastAPI(title='Adrobot — Keitaro Wrapper', version='0.1.0')
app.add_middleware(CORSMiddleware, allow_origins=get_settings().cors_origins.split(','),
                   allow_credentials=False, allow_methods=['GET', 'POST', 'DELETE'], allow_headers=['Content-Type'])

@app.get('/api/health')
async def health(): return {'status': 'ok', 'keitaro_key_configured': bool(get_settings().keitaro_api_key)}

@app.get('/api/options')
async def options():
    async with Keitaro() as api:
        paths = ('domains', 'groups', 'traffic_sources', 'offers')
        values = {}
        for path in paths:
            result = await api.get(path)
            values[path] = result if isinstance(result, list) else result.get('data', [])
        return values

@app.get('/api/campaigns')
async def campaigns():
    async with Keitaro() as api: return await api.get('campaigns')

@app.get('/api/campaigns/{campaign_id}')
async def campaign_detail(campaign_id: int):
    async with Keitaro() as api:
        campaign = await api.get(f'campaigns/{campaign_id}')
        streams = await api.streams(campaign_id)
        return {'campaign': campaign, 'streams': streams}

@app.post('/api/campaigns', status_code=201)
async def create(payload: CampaignCreate, db: Session = Depends(get_db)):
    async with Keitaro() as api: return await create_campaign(api, db, payload)

@app.post('/api/campaigns/{campaign_id}/offers')
async def add_offer(campaign_id: int, payload: OfferAdd, db: Session = Depends(get_db)):
    async with Keitaro() as api:
        return await update_stream_offers(api, db, campaign_id, payload.stream_id, payload.offer_id, True, payload.share)

@app.delete('/api/campaigns/{campaign_id}/offers/{offer_id}')
async def remove_offer(campaign_id: int, offer_id: int, payload: OfferRemove, db: Session = Depends(get_db)):
    async with Keitaro() as api:
        return await update_stream_offers(api, db, campaign_id, payload.stream_id, offer_id, False)

@app.post('/api/campaigns/{campaign_id}/stats')
async def stats(campaign_id: int, payload: ReportRequest):
    if date.fromisoformat(payload.start) > date.fromisoformat(payload.end):
        raise HTTPException(422, 'Start date must be before end date')
    async with Keitaro() as api:
        # Keitaro report/build: group by stream and offer to preserve tracker counts.
        result = await api.post('report/build', {
            'range': {'interval': 'custom_date', 'from': payload.start, 'to': payload.end, 'timezone': 'UTC'},
            'columns': [], 'metrics': ['clicks', 'conversions', 'sale_revenue', 'cost', 'profit'],
            'grouping': ['stream_id', 'offer_id'],
            'filters': [{'name': 'campaign_id', 'operator': 'EQUALS', 'expression': str(campaign_id)}],
            'summary': True, 'limit': 1000, 'offset': 0,
        })
        return result
