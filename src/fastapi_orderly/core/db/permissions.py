from enum import StrEnum


class PermissionAction(StrEnum):
    READ = "read"
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"


def get_perm_code(resource: str, action: PermissionAction) -> str:
    return f"{resource}:{action.value}"
