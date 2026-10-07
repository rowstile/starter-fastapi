"""The app's tables: people, teams, and the documents they share."""

from sqlalchemy import BigInteger, ForeignKey, Identity, MetaData, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    metadata = MetaData(schema="app")


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str] = mapped_column(Text)


class Team(Base):
    __tablename__ = "teams"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str] = mapped_column(Text)


class TeamMember(Base):
    __tablename__ = "team_members"
    team_id: Mapped[int] = mapped_column(ForeignKey("app.teams.id"), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("app.users.id"), primary_key=True, index=True)


class Document(Base):
    __tablename__ = "documents"
    # the database makes the ids: an app that chose them could learn which ones are taken
    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("app.users.id"), index=True)
    title: Mapped[str] = mapped_column(Text)
    body: Mapped[str] = mapped_column(Text, default="", server_default="")
