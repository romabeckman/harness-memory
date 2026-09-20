from uuid import UUID
from pydantic import BaseModel


class KnowledgePublicationResponse(BaseModel):
    status: str
    publication_id: UUID
    snapshot_id: UUID
