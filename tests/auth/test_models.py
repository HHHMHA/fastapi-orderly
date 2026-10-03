from fastapi_orderly.core.db.permissions import PermissionAction
from fastapi_orderly.core.db.registry import UserAccount


class TestUserAccount:
    def test_permissions(self) -> None:
        assert UserAccount.get_permissions() == (
            f"user_account:{PermissionAction.READ.value}",
            f"user_account:{PermissionAction.CREATE.value}",
            f"user_account:{PermissionAction.UPDATE.value}",
            f"user_account:{PermissionAction.DELETE.value}",
        )

    def test_extra_permissions(self) -> None:
        UserAccount.extra_permissions = ("extra_permission",)
        assert UserAccount.get_permissions() == (
            f"user_account:{PermissionAction.READ.value}",
            f"user_account:{PermissionAction.CREATE.value}",
            f"user_account:{PermissionAction.UPDATE.value}",
            f"user_account:{PermissionAction.DELETE.value}",
            "extra_permission",
        )
