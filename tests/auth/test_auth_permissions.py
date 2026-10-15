import pytest

import fastapi_orderly.modules.auth.permissions as permissions_module


def test_get_all_permissions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class ModelA:
        @classmethod
        def get_permissions(cls) -> tuple[str, ...]:
            return ("a.read", "a.write")

    class ModelB:
        @classmethod
        def get_permissions(cls) -> tuple[str, ...]:
            return ("b.read",)

    permissions_module.get_permission_models.cache_clear()
    monkeypatch.setattr(
        permissions_module,
        "get_permission_models",
        lambda: (ModelA, ModelB),
    )

    permissions_module.get_all_permissions.cache_clear()

    assert permissions_module.get_all_permissions() == (
        "a.read",
        "a.write",
        "b.read",
    )
