"""The app over HTTP, against the migrated database (ROWSTILE_APP_URL): the README's walk, as a test.

The policy has tests of its own, in db/tests/ (rowstile test). These are for the app's code on top of it."""

import os
import uuid
from collections.abc import AsyncIterator

import httpx
import pytest
from app.main import make_app

ANN, BO, CY = {"x-user": "1"}, {"x-user": "2"}, {"x-user": "3"}  # cy is in the team "writers" (10)

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
async def api() -> AsyncIterator[httpx.AsyncClient]:
    app = make_app(os.environ["ROWSTILE_APP_URL"])
    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client,
    ):
        yield client


async def test_a_document_is_shared_with_a_person_and_a_team(api: httpx.AsyncClient) -> None:
    title = f"Plan {uuid.uuid4().hex[:8]}"
    made = await api.post("/documents", json={"title": title}, headers=ANN)
    assert made.status_code == 201, made.text
    doc = made.json()["id"]
    try:
        # it is ann's: bo doesn't see it (a 404, not a 403: he isn't told it exists)
        assert (await api.get(f"/documents/{doc}", headers=BO)).status_code == 404
        assert doc not in [d["id"] for d in (await api.get("/documents", headers=BO)).json()]

        # shared with bo as a viewer: he reads it, and a change is refused with the reason
        shared = await api.post(f"/documents/{doc}/shares", json={"relation": "viewer", "user_id": 2}, headers=ANN)
        assert shared.status_code == 201, shared.text
        mine = [d for d in (await api.get("/documents", headers=BO)).json() if d["id"] == doc]
        assert mine and mine[0]["can"] == ["view"], mine
        refused = await api.patch(f"/documents/{doc}", json={"title": "bo's"}, headers=BO)
        assert refused.status_code == 403, refused.text
        assert refused.json()["command"] == "update" and any("edit" in line for line in refused.json()["why"])

        # shared with the writers as editors: cy, a member, changes it
        team = await api.post(f"/documents/{doc}/shares", json={"relation": "editor", "team_id": 10}, headers=ANN)
        assert team.status_code == 201, team.text
        assert (await api.patch(f"/documents/{doc}", json={"body": "by cy"}, headers=CY)).status_code == 200
        assert (await api.get(f"/documents/{doc}", headers=ANN)).json()["body"] == "by cy"

        # only who may share sees whom it is shared with, and who can do what
        assert (await api.get(f"/documents/{doc}/shares", headers=BO)).status_code == 403
        access = (await api.get(f"/documents/{doc}/access", headers=ANN)).json()
        assert access == {"view": ["1", "2", "3"], "edit": ["1", "3"]}, access

        # an editor may not share it, nor delete it
        assert (
            await api.post(f"/documents/{doc}/shares", json={"relation": "viewer", "user_id": 2}, headers=CY)
        ).status_code == 403
        assert (await api.delete(f"/documents/{doc}", headers=CY)).status_code == 403
    finally:
        assert (await api.delete(f"/documents/{doc}", headers=ANN)).status_code == 204


async def test_nobody_signed_in_sees_nothing(api: httpx.AsyncClient) -> None:
    assert (await api.get("/documents")).json() == []
