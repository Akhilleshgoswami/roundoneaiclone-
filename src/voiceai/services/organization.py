"""Business logic for organizations."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from voiceai.models.organization import Organization
from voiceai.schemas.organization import OrganizationCreate


class OrganizationNotFoundError(Exception):
    """Raised when an organization_id does not exist."""


async def create_organization(
    session: AsyncSession,
    payload: OrganizationCreate,
) -> Organization:
    org = Organization(**payload.model_dump())
    session.add(org)
    await session.commit()
    await session.refresh(org)
    return org


async def list_organizations(session: AsyncSession) -> list[Organization]:
    result = await session.scalars(
        select(Organization).order_by(Organization.created_at.desc())
    )
    return list(result.all())


async def get_organization(
    session: AsyncSession,
    organization_id: UUID,
) -> Organization | None:
    return await session.get(Organization, organization_id)


async def require_organization(
    session: AsyncSession,
    organization_id: UUID,
) -> Organization:
    org = await get_organization(session, organization_id)
    if org is None:
        raise OrganizationNotFoundError(
            f"Organization not found: {organization_id}. "
            "Create one with POST /api/v1/organizations or "
            "POST /api/v1/organizations/demo, then use that id."
        )
    return org


async def get_organization_by_slug(
    session: AsyncSession,
    slug: str,
) -> Organization | None:
    result = await session.scalars(
        select(Organization).where(Organization.slug == slug)
    )
    return result.first()


async def ensure_demo_organization(session: AsyncSession) -> Organization:
    existing = await get_organization_by_slug(session, "demo")
    if existing:
        return existing
    return await create_organization(
        session,
        OrganizationCreate(name="Demo Hiring Team", slug="demo"),
    )
