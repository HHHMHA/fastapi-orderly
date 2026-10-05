from fastapi_orderly.modules.auth.models import RefreshToken, UserAccount, UserPermissions
from fastapi_orderly.shared.mixins.reposotories import RepositoryBase


class UserRepository(RepositoryBase[UserAccount]):
    Model: type[UserAccount] = UserAccount

    async def get_by_username(
        self,
        username: str,
    ) -> UserAccount | None:
        return await self.first(
            self.Model.username == username,
        )

    async def get_by_email(
        self,
        email: str,
    ) -> UserAccount | None:
        return await self.first(
            self.Model.email == email,
        )

    async def get_by_username_or_email(
        self,
        identifier: str,
    ) -> UserAccount | None:
        return await self.first(
            (self.Model.username == identifier) | (self.Model.email == identifier),
        )

    async def username_exists(
        self,
        username: str,
    ) -> bool:
        return await self.exists(
            self.Model.username == username,
        )

    async def email_exists(
        self,
        email: str,
    ) -> bool:
        return await self.exists(
            self.Model.email == email,
        )


class UserPermissionsRepository(RepositoryBase[UserPermissions]):
    Model: type[UserPermissions] = UserPermissions

    async def get_by_user_and_permission(
        self,
        user_id: int,
        perm_code: str,
    ) -> UserPermissions | None:
        return await self.first(
            self.Model.user_id == user_id,
            self.Model.perm_code == perm_code,
        )

    async def get_user_permissions(
        self,
        user_id: int,
    ) -> list[UserPermissions]:
        result = await self.filter(
            self.Model.user_id == user_id,
            order_by=self.Model.perm_code,
        )
        return result

    async def has_permission(
        self,
        user: UserAccount,
        perm_code: str,
    ) -> bool:
        if user.is_admin:
            return True

        return any(permission.perm_code == perm_code for permission in user.permissions)

    async def has_non_admin_permission(
        self,
        user_id: int,
        perm_code: str,
    ) -> bool:
        return await self.exists(
            self.Model.user_id == user_id,
            self.Model.perm_code == perm_code,
        )

    async def delete_permission(
        self,
        user_id: int,
        perm_code: str,
    ) -> bool:
        permission = await self.get_by_user_and_permission(
            user_id,
            perm_code,
        )

        if permission is None:
            return False

        await self.delete(permission)
        return True


class RefreshTokenRepository(RepositoryBase[RefreshToken]):
    Model: type[RefreshToken] = RefreshToken

    async def get_by_hash(
        self,
        token_hash: bytes,
    ) -> RefreshToken | None:
        return await self.first(self.Model.token_hash == token_hash)

    async def exists_by_hash(
        self,
        token_hash: bytes,
    ) -> bool:
        return await self.exists(
            self.Model.token_hash == token_hash,
        )

    async def delete_by_hash(
        self,
        token_hash: bytes,
    ) -> bool:
        token = await self.get_by_hash(token_hash)

        if token is None:
            return False

        await self.delete(token)
        return True

    async def get_user_tokens(
        self,
        user_id: int,
    ) -> list[RefreshToken]:
        result = await self.filter(self.Model.user_id == user_id)
        return result

    async def delete_user_tokens(
        self,
        user_id: int,
    ) -> int:
        return await self.delete_where(
            self.Model.user_id == user_id,
        )
