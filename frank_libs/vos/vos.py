from ez_lib.types import json_ser


class AbstractVo:
    """
    Abstract Value Object, this is a base class used for conversion from a
    dictionary received from Slack Bot API to a typed object for further
    convenient usage.
    """

    @classmethod
    def from_dict(cls, d: json_ser, check_exists: bool = False):
        instance = cls()
        if not check_exists:
            for field_name, field_value in d.items():
                setattr(instance, field_name, field_value)
        else:
            for field_name, field_value in d.items():
                if hasattr(instance, field_value):
                    setattr(instance, field_name, field_value)
                else:
                    raise AttributeError(
                        f"While deserializing {cls.__name__} from the "
                        f"dictionary, expected attribute {field_name} was not "
                        f"found."
                    )

        return instance

    def __str__(self):
        items = self.__dict__.items()
        lmo = len(items) - 1
        s = f'{self.__class__.__name__}:\n'
        for i, (field_name, field_value) in enumerate(items):
            if i < lmo:
                s += f'    {field_name}: {field_value}\n'
            else:
                s += f'    {field_name}: {field_value}'

        return s


class SlackUserVo(AbstractVo):
    """
    Slack User Value Object
    """

    def __init__(self):
        self.slack_id: str | None = None
        self.team_id: str | None = None
        self.name: str | None = None
        self.color: str | None = None
        self.real_name: str | None = None
        self.tz: str | None = None
        self.tz_label: str | None = None
        self.tz_offset: int | None = None

        self.profile__first_name: str | None = None
        self.profile__last_name: str | None = None
        self.profile__title: str | None = None
        self.profile__phone: str | None = None
        self.profile__skype: str | None = None
        self.profile__real_name: str | None = None
        self.profile__display_name: str | None = None
        self.profile__avatar_hash: str | None = None
        self.profile__image_original: str | None = None

        self.is_admin: bool | None = None
        self.is_owner: bool | None = None
        self.is_primary_owner: bool | None = None
        self.is_restricted: bool | None = None
        self.is_ultra_restricted: bool | None = None
        self.is_app_user: bool | None = None
        self.updated: bool | None = None
        self.is_email_confirmed: str | None = None
        self.who_can_share_contact_card: str | None = None
