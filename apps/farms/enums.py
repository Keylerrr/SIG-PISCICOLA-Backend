# enums.py
from enum import IntFlag


class FarmPermission(IntFlag):
    VIEW = 1 << 0  #  1
    EDIT = 1 << 1  #  2
    DELETE = 1 << 2  #  4
    MANAGE_USERS = 1 << 3  #  8
    MANAGE_ROLES = 1 << 4  # 16

    ALL = (1 << 5) - 1  # 31

    @classmethod
    def choices(cls):
        return [(p.name, p.name) for p in cls if p != cls.ALL]
