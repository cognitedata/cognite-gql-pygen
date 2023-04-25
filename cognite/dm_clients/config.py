from typing import cast, TypedDict

from dynaconf import Dynaconf

__all__ = ["settings"]


settings = Dynaconf(
    envvar_prefix="DM_CLIENTS",
    ignore_unknown_envvars=True,
    settings_files=["settings.toml", ".secrets.toml"],
    merge_enabled=True,
)


# `envvar_prefix` = export envvars with `export DM_CLIENTS_FOO=bar`.
# `settings_files` = Load these files in the order.


# --- stuff below here is just for hype hints ---


class SettingsCogniteT(TypedDict):
    project: str
    tenant_id: str
    cdf_cluster: str
    client_id: str


class SettingsDMClientsT(TypedDict):
    space: str
    datamodel: str
    schema_version: int
    max_tries: int


class SettingsLocalT(TypedDict):
    prefix: str
    graphql_schema: str
    schema_module: str


class SettingT:
    cognite: SettingsCogniteT
    dm_clients: SettingsDMClientsT
    local: SettingsLocalT


settings = cast(SettingT, settings)
