from ez_lib.types import json_ser
from typing import Iterable


class AbstractVo:
    """
    Abstract Value Object, this is a base class used for conversion from a
    dictionary received from Slack Bot API to a typed object for further
    convenient usage.
    """

    # Map fields with different names, e.g. { "my_id" : "id" }, where
    # "my_id" is property in our Model and "id" is defined in serialized
    # JSON dictionary.
    _serialize_map = {}
    # These fields do not occur in the serialized JSON dictionary but
    # rather are defined only by us e.g. [ "id", "date_created" ]
    _except_fields = []

    def from_dict(self, d: json_ser, strict: bool = False):
        """
        Serialize all fields with the same name from `d` dictionary to
        our defined Model. We can serialize fields with different names
        using the `self._serialized map`. Fields defined by field names
        in `self._except_fields` list will be skipped. Serializable
        Fields MAY NOT start with "_" - if they do, we need to use the
        _serialize_map property. If `d` contains sub-dictionaries,
        we can define them using double underscore,
        e.g. `d.properties.color.main` ~ d__properties__color__main.

        :param d: Dictionary to be serialized.
        :param strict: If True, throw KeyError when field is not found in
                       `d` dictionary.
        """
        for field_name in self.__dict__.keys():
            if (
                    not field_name.startswith('_')
                    and field_name not in self.__class__._except_fields
            ):
                if field_name in self.__class__._serialize_map.keys():
                    setattr(
                        self,
                        field_name,
                        d[self.__class__._serialize_map[field_name]]
                    )
                else:
                    if '__' not in field_name:
                        try:
                            setattr(self, field_name, d[field_name])
                        except KeyError as e:
                            self._log_field_not_found(field_name)
                            if strict:
                                raise e
                    else:
                        arr = field_name.split('__')
                        f = d
                        try:
                            for nested in arr:
                                f = f[nested]
                            setattr(self, field_name, f)
                        except KeyError as e:
                            self._log_field_not_found(field_name)
                            if strict:
                                raise e

    def to_values_dict(self, include: Iterable[str] = ()) -> dict:
        """
        Return dictionary containing all values set on concrete model
        except those set in `self._except_fields`. Exceptions can be
        overridden by `include` parameter. Useful for SqlAlchemy VALUES =
        ...

        :param include: Force to include also values which would be
        otherwise excluded by `self._except_fields`. :return:
        """

        return {
            c.key: getattr(self, c.key) for c in self.__table__.c
            if (c.key not in self._except_fields or c.key in include)
        }

    def _log_field_not_found(self, field_name: str):
        # print(
        #     f"SqlAlchemy Model '{self.__class__.__name__}' field "
        #     f"'{field_name}' not found."
        # )
        pass

    def __str__(self):
        s = f'{self.__class__.__name__}:\n'
        for k, v in self.__dict__.items():
            if not k.startswith('_'):
                s += f'    {k}={v}\n'

        return s


class SlackUserVo(AbstractVo):
    """
    Slack User Value Object
    """

    def __init__(self):
        self.id: str | None = None
        self.is_bot: bool | None = None
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

    def get_name(self):
        if self.profile__real_name:
            return self.profile__real_name
        elif self.profile__display_name:
            return self.profile__display_name
        elif self.profile__title:
            return self.profile__title
        elif self.profile__first_name and self.profile__last_name:
            return f'{self.profile__first_name} {self.profile__last_name}'
        elif self.profile__first_name:
            return self.profile__first_name
        elif self.profile__last_name:
            return self.profile__last_name
        elif self.name:
            return self.name
        else:
            return None
