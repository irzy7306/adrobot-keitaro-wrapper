import pytest
from unittest.mock import AsyncMock
from fastapi import HTTPException
from app.service import make_alias, offer_entries, update_stream_offers

class Db:
    def __init__(self): self.logs = []
    def add(self, obj): self.logs.append(obj)
    def commit(self): pass

def test_alias_is_safe_and_unique():
    assert make_alias('My Campaign').startswith('my-campaign-')
    assert make_alias('My Campaign') != make_alias('My Campaign')

def test_offer_entries():
    assert offer_entries({'offers': [{'offer_id': 12, 'share': 25}]}) == [
        {'offer_id': 12, 'share': 25, 'state': 'active'}]

@pytest.mark.asyncio
async def test_add_preserves_existing_offer():
    api = AsyncMock()
    api.streams.return_value = [{'id': 7, 'campaign_id': 3, 'schema': 'offers',
                                  'offers': [{'offer_id': 1, 'share': 45}]}]
    api.get.return_value = {'id': 7}
    await update_stream_offers(api, Db(), 3, 7, 2, True)
    assert api.put.await_args.args[1]['offers'] == [
        {'offer_id': 1, 'share': 45, 'state': 'active'},
        {'offer_id': 2, 'share': 100, 'state': 'active'}]

@pytest.mark.asyncio
async def test_wrong_stream_rejected():
    api = AsyncMock()
    api.streams.return_value = []
    with pytest.raises(HTTPException) as error:
        await update_stream_offers(api, Db(), 3, 9, 2, False)
    assert error.value.status_code == 404
