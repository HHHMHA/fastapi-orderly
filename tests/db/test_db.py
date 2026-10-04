import pytest
from fastapi import Request

import fastapi_orderly.core.db.registry  # noqa: F401
from fastapi_orderly.core.db.session import Database, get_session
from fastapi_orderly.modules.auth.models import UserAccount


@pytest.mark.asyncio
async def test_expire_on_commit_off(no_app_db: Database, fake_request: Request) -> None:
    setattr(fake_request.state, "database", no_app_db)  # noqa: B010
    async for session in get_session(fake_request):
        u = UserAccount(
            username="test",
            email="test@example.com",
            password="test",
        )
        session.add(u)
        await session.commit()
        assert u is not None
        assert u.id == 1
        assert u.username == "test"
        assert u.email == "test@example.com"
        assert u.password == "test"

        db_u: UserAccount | None = await session.get(UserAccount, 1)
        assert db_u is not None
        assert str(db_u) == f"<Model {db_u.__tablename__} - id = {db_u.id}>"
        assert repr(db_u) == f"<Model {db_u.__tablename__} - id = {db_u.id}>"
        assert db_u.username == u.username
        assert db_u.email == u.email
        assert db_u.password == u.password
        assert db_u.id == u.id
        await session.delete(db_u)
        await session.commit()
        db_u = await session.get(UserAccount, 1)
        assert db_u is None
