from enum import Enum
from ez_lib.postgres import PgSessionSingleton, mapping_result_to_list
from ez_lib.types import json_types, json_ser
from frank_libs.db.models import (
    UserModel,
    DialogueTreeModel,
    CompanyModel,
    SlackUserModel, DialogueModel
)
from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.functions import now


class UserRole(Enum):
    # Can view dialogue trees but not create / edit them, and can not publish
    # them to Slack users
    VIEWER = "viewer"
    # Can create / edit / publish dialogue trees but can not add new users
    PUBLISHER = "publisher"
    # Can do everything as publisher, and also can create new users (via email
    # invite links)
    ADMIN = "admin"


async def mk_user(
        session: AsyncSession,
        first_name: str,
        second_name: str,
        email: str,
        role: UserRole,
        passwd_hash: str
) -> UserModel:
    user = UserModel(
        first_name=first_name,
        second_name=second_name,
        email=email,
        passwd_hash=passwd_hash,
        role=role.value,
    )
    session.add(user)
    await session.commit()

    return user


async def fetch_user(session: AsyncSession, email: str) -> UserModel:
    stmt = select(UserModel).where(UserModel.email == email)
    return await session.scalar(stmt)


async def update_user_last_login(session: AsyncSession, id_: int):
    stmt = update(UserModel).where(UserModel.id == id_).values(last_login=now())
    await session.execute(stmt)
    await session.commit()


async def save_dialogue_tree(
        session: AsyncSession,
        user_id: int,
        table_id: int | None,
        title: str,
        tree_json: dict
) -> DialogueTreeModel | None:
    if table_id is not None:
        stmt = update(DialogueTreeModel).where(
            DialogueTreeModel.id == table_id
        ).values(
            data=tree_json,
            title=title,
            last_update_at=now(),
            update_count=DialogueTreeModel.update_count + 1,
            published=False
        )
        # todo return TreeModel as well ?
        await session.execute(stmt)
        await session.commit()
    else:
        tree = DialogueTreeModel(
            publisher_id=user_id,
            title=title,
            published=False,
            data=tree_json,
            created_at=now(),
            last_update_at=now(),
            update_count=0
        )
        session.add(tree)
        await session.commit()

        return tree


async def fetch_user_trees(session: AsyncSession, user_id: int):
    stmt = select(DialogueTreeModel).where(
        DialogueTreeModel.publisher_id == user_id
    ).where(DialogueTreeModel.deleted_at == None)
    result = await session.execute(stmt)
    return result.mappings().all()


async def fetch_user_tree(tree_id: int) -> DialogueTreeModel | None:
    async with PgSessionSingleton.get_session() as session:
        stmt = select(DialogueTreeModel).where(DialogueTreeModel.id == tree_id)
        return await session.scalar(stmt)


async def set_user_tree_published(session: AsyncSession, tree_id: int):
    stmt = update(DialogueTreeModel).where(
        DialogueTreeModel.id == tree_id
    ).values(
        published=True
    )
    await session.execute(stmt)
    await session.commit()


async def set_user_tree_deleted(session: AsyncSession, tree_id: int) -> bool:
    stmt = update(DialogueTreeModel).where(
        DialogueTreeModel.id == tree_id
    ).values(deleted_at=now())

    ex = await session.execute(stmt)
    await session.commit()

    return ex.rowcount == 1


async def fetch_companies() -> list[CompanyModel]:
    async with PgSessionSingleton.get_session() as session:
        stmt = select(CompanyModel).where(CompanyModel.is_active == True)
        result = await session.execute(stmt)

        return mapping_result_to_list(result, 'CompanyModel')


async def create_company_users(
        company_id: int,
        cache_timestamp: int,
        users_dict: dict
) -> list[SlackUserModel]:
    async with PgSessionSingleton.get_session() as session:
        slack_users = []
        for user_def in users_dict:
            # if not user_def['is_bot'] and not user_def['deleted']:
            if not user_def['deleted']:
                slack_user = SlackUserModel(company_id=company_id)
                slack_user.from_dict(user_def)
                slack_users.append(slack_user)

        stmt = update(CompanyModel).where(CompanyModel.id == company_id).values(
            last_update=cache_timestamp
        )
        await session.execute(stmt)
        session.add_all(slack_users)
        await session.commit()

        return slack_users


async def fetch_company_users(company_id: int) -> list[SlackUserModel]:
    async with PgSessionSingleton.get_session() as session:
        stmt = select(SlackUserModel).where(
            SlackUserModel.company_id == company_id)
        result = await session.execute(stmt)

        # noinspection PyTypeChecker
        return mapping_result_to_list(result, 'SlackUserModel')


async def update_company_users(
        company_id: int,
        current_users: dict[str, SlackUserModel],
        users_dict: list[dict[str, json_types]],
) -> (list[SlackUserModel], list[SlackUserModel]):
    async with PgSessionSingleton.get_session() as session:
        updated_users = []
        new_users = []
        for user_def in users_dict:
            if not user_def['is_bot'] and not user_def['deleted']:
                if user_def['id'] not in current_users.keys():
                    slack_user = SlackUserModel(company_id=company_id)
                    slack_user.from_dict(user_def)
                    new_users.append(slack_user)
                else:
                    slack_user = SlackUserModel(date_updated=now())
                    slack_user.from_dict(user_def)
                    updated_users.append(slack_user)

                stmt = insert(SlackUserModel).values(
                    slack_user.to_values_dict(("company_id",))
                )

                do_update_stmt = stmt.on_conflict_do_update(
                    index_elements=['slack_id'],
                    set_=slack_user.to_values_dict(("date_updated",)),
                )
                await session.execute(do_update_stmt)

        # Update Company.last_update = now()
        await session.execute(
            update(CompanyModel).where(
                CompanyModel.id == company_id
            ).values(users_update_ts=now())
        )

        await session.commit()

        return new_users, updated_users


async def create_dialogues(
        user_ids: list[str],
        tree_id: int,
):
    async with PgSessionSingleton.get_session() as session:
        dms = []
        for uid in user_ids:
            d = DialogueModel(
                tree_id=tree_id,
                user_id=uid,
                date_started=now(),
            )
            dms.append(d)
            session.add(d)

        await session.commit()

        return dms


async def set_dialogue_finished(dialogue_db_id: int, tree_id, answers: json_ser):
    async with PgSessionSingleton.get_session() as session:
        stmt = update(
            DialogueModel
        ).where(DialogueModel.id == dialogue_db_id).values(
            answers=answers,
            date_finished=now()
        )

        await session.execute(stmt)
        await session.commit()
