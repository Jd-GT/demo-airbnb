from __future__ import annotations

from enum import StrEnum


class PermissionLevel(StrEnum):
    NONE = 'none'
    READ = 'read'
    WRITE = 'write'
    ADMIN = 'admin'


class ModuleKey(StrEnum):
    CORE = 'core'
    USERS = 'users'
    INVENTORY = 'inventory'
    CRM = 'crm'
    BOOKING = 'booking'
    FINANCE = 'finance'


class SystemRole(StrEnum):
    OWNER = 'OWNER'
    MEMBER = 'MEMBER'
    CLEANER = 'CLEANER'


PERMISSION_HIERARCHY = {
    PermissionLevel.NONE: 0,
    PermissionLevel.READ: 1,
    PermissionLevel.WRITE: 2,
    PermissionLevel.ADMIN: 3,
}


def modules_default_permissions(level: PermissionLevel) -> dict[str, str]:
    return {module.value: level.value for module in ModuleKey}


# Modules that are sensitive enough to be `none` by default in the seeded
# "Solo Lectura" role. Only users with USERS=admin (typically the OWNER or
# someone explicitly granted) can see other people's data or finance numbers.
PRIVATE_MODULES_FOR_READONLY_ROLE = {ModuleKey.USERS.value, ModuleKey.FINANCE.value}


def safe_readonly_permissions() -> dict[str, str]:
    """Default for the seeded 'Solo Lectura' role.

    Read access on operational modules (inventory, crm, booking, core) but
    no access to user lists or financial data. Owners can explicitly grant
    those modules by editing the role.
    """
    return {
        module.value: (
            PermissionLevel.NONE.value
            if module.value in PRIVATE_MODULES_FOR_READONLY_ROLE
            else PermissionLevel.READ.value
        )
        for module in ModuleKey
    }


def validate_permissions_map(permissions: dict) -> dict[str, str]:
    if not isinstance(permissions, dict):
        raise ValueError('permissions must be a JSON object')

    normalized: dict[str, str] = {}
    allowed_modules = {module.value for module in ModuleKey}
    allowed_levels = {level.value for level in PermissionLevel}

    for module, level in permissions.items():
        if module not in allowed_modules:
            raise ValueError(f"Unsupported module '{module}'")
        if level not in allowed_levels:
            raise ValueError(
                f"Unsupported level '{level}' for module '{module}'. "
                f'Valid values: {sorted(allowed_levels)}'
            )
        normalized[module] = level

    # Fill unspecified modules with the safest default.
    for module in ModuleKey:
        normalized.setdefault(module.value, PermissionLevel.NONE.value)

    return normalized
