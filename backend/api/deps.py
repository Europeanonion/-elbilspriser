from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

import db.session


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with db.session.async_session_factory() as session:
        yield session


DBSession = Annotated[AsyncSession, Depends(get_db)]
