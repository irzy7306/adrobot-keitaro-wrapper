"""Create campaign plus two ordered flows.  The upstream is the source of truth."""
import re
from uuid import uuid4
from fastapi import HTTPException
from sqlalchemy.orm import Session
from .config import get_settings
from .keitaro import Keitaro
from .models import CampaignRecord, AuditEvent
from .schemas import CampaignCreate


def make_alias(name: str):
    alias = re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')[:60]
    return f'{alias or "campaign"}-{uuid4().hex[:6]}'


def name_with_prefix(name: str) -> str:
    prefix = get_settings().campaign_prefix
    return name if name.startswith(prefix) else prefix + name


def offer_entries(stream: dict):
    """Normalize offer associations; stream.offers may be a list of objects."""
    raw = stream.get('offers') or []
    return [{'offer_id': int(x['offer_id']), 'share': int(x.get('share', 100)),
             'state': x.get('state', 'active')} for x in raw if isinstance(x, dict) and x.get('offer_id')]


async def create_campaign(api: Keitaro, db: Session, data: CampaignCreate):
    await api.ensure_offer(data.offer_id)
    # Verify selectable references before making any changes.
    for path, wanted in [('domains', data.domain_id), ('groups', data.group_id),
                         ('traffic_sources', data.traffic_source_id)]:
        response = await api.get(path)
        entries = response if isinstance(response, list) else response.get('data', [])
        if not any(int(row.get('id', 0)) == wanted for row in entries):
            raise HTTPException(422, f'{path}: id {wanted} not found')

    name = name_with_prefix(data.name.strip())
    campaign = await api.post('campaigns', {
        'name': name, 'alias': make_alias(name), 'type': 'position',
        'domain_id': data.domain_id, 'group_id': data.group_id,
        'traffic_source_id': data.traffic_source_id,
    })
    campaign_id = int(campaign['id'])
    stream_ids = []
    try:
        # Keitaro schema: forced flow overrides other flows; regular falls through.
        google = await api.post('streams', {
            'name': f'{data.geo} → Google', 'campaign_id': campaign_id,
            'type': 'forced', 'position': 1, 'state': 'active',
            'schema': 'redirect', 'action_type': 'http',
            'action_payload': 'https://www.google.com/',
            'filters': [{'name': 'geo', 'mode': 'accept', 'payload': data.geo}],
        })
        stream_ids.append(int(google['id']))
        offers = await api.post('streams', {
            'name': 'Main offer', 'campaign_id': campaign_id,
            'type': 'regular', 'position': 2, 'state': 'active',
            'schema': 'offers',
            'offers': [{'offer_id': data.offer_id, 'share': 100, 'state': 'active'}],
        })
        stream_ids.append(int(offers['id']))
    except Exception:
        # Avoid leaving partially configured active campaigns; keep for inspection.
        try: await api.put(f'campaigns/{campaign_id}', {'state': 'disabled'})
        except Exception: pass
        raise
    db.add(CampaignRecord(keitaro_campaign_id=campaign_id, name=name,
                          geo=data.geo, offer_stream_id=stream_ids[1]))
    db.add(AuditEvent(campaign_id=campaign_id, operation='create', payload={'stream_ids': stream_ids}))
    db.commit()
    return {'campaign': campaign, 'stream_ids': stream_ids}


async def update_stream_offers(api: Keitaro, db: Session, campaign_id: int,
                               stream_id: int, offer_id: int, add: bool, share: int = 100):
    streams = await api.streams(campaign_id)
    stream = next((x for x in streams if int(x['id']) == stream_id), None)
    if stream is None: raise HTTPException(404, 'Stream does not belong to this campaign')
    if stream.get('schema') not in ('offers', 'landings_offers'):
        raise HTTPException(409, 'Cannot edit offers in a stream without an offer schema')
    current = offer_entries(stream)
    if add:
        await api.ensure_offer(offer_id)
        if any(x['offer_id'] == offer_id for x in current):
            raise HTTPException(409, 'Offer is already attached to this stream')
        current.append({'offer_id': offer_id, 'share': share, 'state': 'active'})
    else:
        if not any(x['offer_id'] == offer_id for x in current):
            raise HTTPException(404, 'Offer is not attached to this stream')
        current = [x for x in current if x['offer_id'] != offer_id]
    # Important: update only associations; never overwrite unrelated stream filters/config.
    await api.put(f'streams/{stream_id}', {'offers': current})
    db.add(AuditEvent(campaign_id=campaign_id, operation='add_offer' if add else 'remove_offer',
                      payload={'stream_id': stream_id, 'offer_id': offer_id}))
    db.commit()
    return await api.get(f'streams/{stream_id}')
