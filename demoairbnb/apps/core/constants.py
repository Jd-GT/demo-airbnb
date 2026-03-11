from __future__ import annotations

from enum import StrEnum


class PermissionLevel(StrEnum):
    NONE = "none"
    READ = "read"
    WRITE = "write"
    ADMIN = "admin"


class ModuleKey(StrEnum):
    CORE = "core"
    USERS = "users"
    INVENTORY = "inventory"
    CRM = "crm"
    BOOKING = "booking"
    FINANCE = "finance"


class SystemRole(StrEnum):
    OWNER = "OWNER"
    MEMBER = "MEMBER"
    CLEANER = "CLEANER"


PERMISSION_HIERARCHY = {
    PermissionLevel.NONE: 0,
    PermissionLevel.READ: 1,
    PermissionLevel.WRITE: 2,
    PermissionLevel.ADMIN: 3,
}


def modules_default_permissions(level: PermissionLevel) -> dict[str, str]:
    return {module.value: level.value for module in ModuleKey}


def validate_permissions_map(permissions: dict) -> dict[str, str]:
    if not isinstance(permissions, dict):
        raise ValueError("permissions must be a JSON object")

    normalized: dict[str, str] = {}
    allowed_modules = {module.value for module in ModuleKey}
    allowed_levels = {level.value for level in PermissionLevel}

    for module, level in permissions.items():
        if module not in allowed_modules:
            raise ValueError(f"Unsupported module '{module}'")
        if level not in allowed_levels:
            raise ValueError(
                f"Unsupported level '{level}' for module '{module}'. "
                f"Valid values: {sorted(allowed_levels)}"
            )
        normalized[module] = level

    # Fill unspecified modules with the safest default.
    for module in ModuleKey:
        normalized.setdefault(module.value, PermissionLevel.NONE.value)

    return normalized
