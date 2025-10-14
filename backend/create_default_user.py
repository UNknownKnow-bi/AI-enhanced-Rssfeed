"""Script to create default user for development"""
import asyncio
import uuid
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models import User


async def create_default_user():
    """Create a default user with fixed UUID"""
    default_user_id = uuid.UUID("00000000-0000-0000-0000-000000000001")

    async with AsyncSessionLocal() as db:
        # Check if user already exists
        result = await db.execute(
            select(User).where(User.id == default_user_id)
        )
        existing_user = result.scalar_one_or_none()

        if existing_user:
            print(f"Default user already exists: {existing_user.email}")
            return

        # Create default user
        user = User(
            id=default_user_id,
            email="default@example.com"
        )

        db.add(user)
        await db.commit()
        print(f"Created default user: {user.email} (ID: {user.id})")


if __name__ == "__main__":
    asyncio.run(create_default_user())
