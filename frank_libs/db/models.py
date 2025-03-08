from datetime import datetime
from typing import Any, NewType

from ez_lib.postgres import AbstractModelHelper
from ez_lib.types import json_ser
from sqlalchemy import JSON, String, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.sql.functions import now

SlackIdStr_9 = NewType("SlackIdStr_9", str)
SlackStr_20 = NewType("SlackStr_20", str)
SlackStr_80 = NewType("SlackStr_80", str)
SlackStr_512 = NewType("SlackStr_512", str)
DbStr_32 = NewType("DbStr_32", str)
DbStr_64 = NewType("DbStr_64", str)


class AbstractModel(AbstractModelHelper, DeclarativeBase):
    type_annotation_map = {
        json_ser: JSON,
        SlackIdStr_9: String(9),
        SlackStr_20: String(20),
        DbStr_32: String(32),
        DbStr_64: String(64),
        SlackStr_80: String(80),
        SlackStr_512: String(512),
    }


class UserModel(AbstractModel):
    __tablename__ = 'users'

    id: Mapped[int] = mapped_column(primary_key=True)
    first_name: Mapped[str]
    second_name: Mapped[str]
    email: Mapped[str]
    passwd_hash: Mapped[str]
    role: Mapped[str]
    date_created: Mapped[datetime] = mapped_column(default=now())
    last_login: Mapped[datetime | None]

    def __str__(self):
        return (
            f"id={self.id}, first_name={self.first_name}, "
            f"last_name={self.last_login}, email={self.email}, "
            f"passwd_hash={self.passwd_hash}, role={self.role}, "
            f"date_created={self.date_created}, last_login={self.last_login}"
        )


class DialogueTreeModel(AbstractModel):
    __tablename__ = 'dialogue_trees'

    id: Mapped[int] = mapped_column(primary_key=True)
    publisher_id: Mapped[int]
    title: Mapped[str]
    published: Mapped[bool]
    data: Mapped[json_ser]
    # data: Mapped[dict[str, Any]]
    created_at: Mapped[datetime]
    last_update_at: Mapped[datetime]
    update_count: Mapped[int]
    deleted_at: Mapped[datetime | None]


class SlackUserModel(AbstractModel):
    def __init__(self, **kw: Any):
        super().__init__(**kw)

    __tablename__ = "slack_users"

    _serialize_map = {
        "slack_id": "id"
    }

    _except_fields = [
        "id",
        "date_created",
        'company_id',
        "date_updated"
    ]

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey('company.id'))
    date_created: Mapped[datetime] = mapped_column(default=now())
    date_updated: Mapped[datetime]
    deleted: Mapped[bool] = mapped_column(default=False)

    slack_id: Mapped[SlackStr_80]
    team_id: Mapped[SlackIdStr_9]
    name: Mapped[SlackStr_80]
    color: Mapped[SlackStr_80]
    real_name: Mapped[SlackStr_80]
    tz: Mapped[SlackStr_80]
    tz_label: Mapped[SlackStr_80]
    tz_offset: Mapped[int]

    profile__first_name: Mapped[SlackStr_80]
    profile__last_name: Mapped[SlackStr_80]
    profile__title: Mapped[SlackStr_80]
    profile__phone: Mapped[SlackStr_80]
    profile__skype: Mapped[SlackStr_80]
    profile__real_name: Mapped[SlackStr_80]
    profile__display_name: Mapped[SlackStr_80]
    profile__avatar_hash: Mapped[SlackStr_80]
    profile__image_original: Mapped[SlackStr_80]

    is_admin: Mapped[bool]
    is_owner: Mapped[bool]
    is_primary_owner: Mapped[bool]
    is_restricted: Mapped[bool]
    is_ultra_restricted: Mapped[bool]
    is_app_user: Mapped[bool]
    updated: Mapped[int]
    is_email_confirmed: Mapped[bool]
    who_can_share_contact_card: Mapped[SlackStr_80]


class CompanyModel(AbstractModel):
    __tablename__ = 'company'

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[DbStr_64]
    http_port: Mapped[int]
    slack_token: Mapped[DbStr_64]
    slack_user_token: Mapped[SlackStr_80]
    slack_secret: Mapped[DbStr_64]
    client_id: Mapped[DbStr_32]
    client_secret: Mapped[DbStr_32]
    is_active: Mapped[bool]
    users_update_ts: Mapped[int]
    slack_user_id:Mapped[SlackStr_80]


class DialogueModel(AbstractModel):
    __tablename__ = 'dialogues'

    id: Mapped[int] = mapped_column(primary_key=True)
    tree_id: Mapped[int]
    user_id: Mapped[str]
    date_started: Mapped[datetime]
    date_finished: Mapped[datetime]
    answers: Mapped[json_ser]
    