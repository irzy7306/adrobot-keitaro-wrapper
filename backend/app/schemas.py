from pydantic import BaseModel, Field, field_validator

class CampaignCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    geo: str = Field(pattern=r'^[A-Za-z]{2}$')
    offer_id: int = Field(gt=0)
    domain_id: int = Field(gt=0)
    group_id: int = Field(gt=0)
    traffic_source_id: int = Field(gt=0)
    @field_validator('geo')
    @classmethod
    def uppercase(cls, value: str) -> str: return value.upper()

class OfferAdd(BaseModel):
    offer_id: int = Field(gt=0)
    stream_id: int = Field(gt=0)
    share: int = Field(default=100, ge=1, le=100)

class OfferRemove(BaseModel):
    stream_id: int = Field(gt=0)

class ReportRequest(BaseModel):
    start: str = Field(pattern=r'^\d{4}-\d{2}-\d{2}$')
    end: str = Field(pattern=r'^\d{4}-\d{2}-\d{2}$')
