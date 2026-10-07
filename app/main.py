"""Documents shared with people and teams. There is no permission check in this file: each request's
transactions sign in as its user, Postgres filters what they read and refuses what they may not write, and
rowstile answers a refusal with 403 (and the reason) and a row the user can't see with 404."""

import os
from typing import Literal

import rowstile
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from rowstile import NotFound
from rowstile import sqlalchemy as authz_sa
from rowstile.fastapi import Rowstile
from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from .authz_client import ObjectType, Permission
from .models import Document

# queries by permission that take only the policy's names: a misspelled one doesn't type-check
queries = authz_sa.Queries[ObjectType, Permission]()


def user_of(request: Request) -> str | None:
    """Who the request is. THIS IS A PLACEHOLDER: it believes a header. Read your session or verify your token
    here instead, and return the user's id (None: nobody is signed in)."""
    return request.headers.get("x-user")


def signed_in() -> int:
    """The user this request acts for, as the tables' key."""
    who = rowstile.current()
    if who is None or who.id is None:
        raise HTTPException(401, "sign in first")
    return int(who.id)


class NewDocument(BaseModel):
    title: str
    body: str = ""


class Changes(BaseModel):
    title: str | None = None
    body: str | None = None


class Share(BaseModel):
    """Whom a document is shared with: one person, or a team's members."""

    relation: Literal["viewer", "editor"]
    user_id: int | None = None
    team_id: int | None = None

    def subject(self) -> tuple[str, str, str]:
        if (self.user_id is None) == (self.team_id is None):
            raise ValueError("give user_id or team_id, one of them")
        return ("user", str(self.user_id), "") if self.user_id is not None else ("team", str(self.team_id), "member")


def make_app(url: str | None = None) -> FastAPI:
    # the app's own connection, as the role the policy names (app role starter_app): never the owner's
    engine = create_async_engine(url or os.environ["ROWSTILE_APP_URL"])
    Session = async_sessionmaker(engine, expire_on_commit=False)
    app = FastAPI(title="rowstile starter: shared documents")
    # signs every transaction in as the request's user, turns refusals into 403 and hidden rows into 404,
    # and refuses to start on a connection that skips row-level security
    Rowstile(app, engine, user=user_of)

    @app.get("/documents")
    async def documents() -> list[dict[str, object]]:
        """The documents the user may see, each with what they may do to it (for the page's buttons)."""
        async with Session() as s:
            rows = (await s.execute(select(Document.id, Document.title).order_by(Document.id))).all()
            can = await queries.perms_of(s, "document", [r.id for r in rows])
            return [{"id": r.id, "title": r.title, "can": can.get(str(r.id), [])} for r in rows]

    @app.post("/documents", status_code=201)
    async def create(new: NewDocument) -> dict[str, int]:
        async with Session.begin() as s:
            doc = Document(owner_id=signed_in(), title=new.title, body=new.body)
            s.add(doc)
            await s.flush()
            return {"id": doc.id}

    @app.get("/documents/{doc_id}")
    async def read(doc_id: int) -> dict[str, object]:
        async with Session() as s:
            doc = await s.get(Document, doc_id)
            if doc is None:
                raise NotFound("app.documents", doc_id)
            return {"id": doc.id, "title": doc.title, "body": doc.body, "owner_id": doc.owner_id}

    @app.patch("/documents/{doc_id}")
    async def change(doc_id: int, changes: Changes) -> dict[str, int]:
        async with Session.begin() as s:
            doc = await s.get(Document, doc_id)
            if doc is None:
                raise NotFound("app.documents", doc_id)
            if changes.title is not None:
                doc.title = changes.title
            if changes.body is not None:
                doc.body = changes.body
            # no check: an update the rules refuse comes back as 403, with the rule and what was missing
        return {"id": doc_id}

    @app.delete("/documents/{doc_id}", status_code=204)
    async def remove(doc_id: int) -> None:
        async with Session.begin() as s:
            result = await s.execute(delete(Document).where(Document.id == doc_id))
            await authz_sa.expect(s, result, "app.documents", "delete", doc_id)

    @app.get("/documents/{doc_id}/shares")
    async def shares(doc_id: int) -> list[dict[str, object]]:
        """Whom the document is shared with. For whoever may share it."""
        async with Session() as s:
            rows = await s.execute(text("SELECT * FROM authz.list_shares('document', :id)"), {"id": str(doc_id)})
            return [
                {"relation": r["relation"], "type": r["subject_type"], "id": r["subject_id"]} for r in rows.mappings()
            ]

    @app.post("/documents/{doc_id}/shares", status_code=201)
    async def share(doc_id: int, to: Share) -> dict[str, bool]:
        kind, who, members = to.subject()
        async with Session.begin() as s:
            await s.execute(
                text("SELECT authz.share('document', :id, :relation, :kind, :who, :members)"),
                {"id": str(doc_id), "relation": to.relation, "kind": kind, "who": who, "members": members},
            )
        return {"shared": True}

    @app.delete("/documents/{doc_id}/shares", status_code=204)
    async def unshare(doc_id: int, to: Share) -> None:
        kind, who, members = to.subject()
        async with Session.begin() as s:
            await s.execute(
                text("SELECT authz.unshare('document', :id, :relation, :kind, :who, :members)"),
                {"id": str(doc_id), "relation": to.relation, "kind": kind, "who": who, "members": members},
            )

    @app.get("/documents/{doc_id}/access")
    async def access(doc_id: int) -> dict[str, list[str]]:
        """Who can view the document, and who can edit it: the users' ids. For whoever may share it."""
        async with Session() as s:
            out: dict[str, list[str]] = {}
            for perm in ("view", "edit"):
                rows = await s.execute(
                    text("SELECT x FROM authz.who('document', :id, :perm) x"), {"id": str(doc_id), "perm": perm}
                )
                out[perm] = sorted(rows.scalars().all())
            return out

    return app


app = make_app() if "ROWSTILE_APP_URL" in os.environ else None
