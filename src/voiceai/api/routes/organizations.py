"""Organization API routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from voiceai.db.session import get_db_session
from voiceai.schemas.organization import OrganizationCreate, OrganizationRead
from voiceai.services.organization import (
    create_organization,
    ensure_demo_organization,
    list_organizations,
)

router = APIRouter(prefix="/api/v1/organizations", tags=["organizations"])
DatabaseSession = Annotated[AsyncSession, Depends(get_db_session)]


@router.post("", response_model=OrganizationRead, status_code=status.HTTP_201_CREATED)
async def create_organization_endpoint(
    payload: OrganizationCreate,
    session: DatabaseSession,
) -> OrganizationRead:
    org = await create_organization(session, payload)
    return OrganizationRead.model_validate(org)


@router.get("", response_model=list[OrganizationRead])
async def list_organizations_endpoint(session: DatabaseSession) -> list[OrganizationRead]:
    orgs = await list_organizations(session)
    return [OrganizationRead.model_validate(o) for o in orgs]


@router.post("/demo", response_model=OrganizationRead)
async def ensure_demo_endpoint(session: DatabaseSession) -> OrganizationRead:
    org = await ensure_demo_organization(session)
    return OrganizationRead.model_validate(org)
