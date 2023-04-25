import importlib
import importlib.util
import inspect
import os
import subprocess
import sys
from pathlib import Path

import click
import typer

from cognite.dm_clients.config import settings
from cognite.dm_clients.domain_modeling.schema import Schema
from cognite.gqlpygen.generator import to_client_sdk
from cognite.gqlpygen.misc import to_client_name, to_schema_name

app = typer.Typer()


_settings_cognite = settings.get("cognite", {})
_cdf_cluster = _settings_cognite.get("cdf_cluster")
_tenant_id = _settings_cognite.get("tenant_id")
_client_id = _settings_cognite.get("client_id")
_client_secret = _settings_cognite.get("client_secret")
_project = _settings_cognite.get("project")

_settings_dm_clients = settings.get("dm_clients", {})
_space = _settings_dm_clients.get("space")
_datamodel = _settings_dm_clients.get("datamodel")
_schema_version = _settings_dm_clients.get("schema_version")

_settings_local = settings.get("local", {})
_prefix = _settings_local.get("prefix", "")
_graphql_schema = _settings_local.get("graphql_schema")
_schema_module = _settings_local.get("schema_module")

_schema_dir = Path(_graphql_schema).parent if _graphql_schema else None

_client_secret_none = "None (use device flow)"
if _client_secret:
    _client_secret_hidden = f"{_client_secret[:3]}{'*' * (len(_client_secret) - 3)}"
else:
    _client_secret_hidden = _client_secret_none


@app.command("topython", help="Create pydantic schema and Python DM client from a .graphql schema.")
def to_python(
    graphql_schema: Path = typer.Argument(_graphql_schema or ..., help="GraphQL schema to convert"),
    output_dir: Path = typer.Option(_schema_dir or os.getcwd(), help="Directory to write schema.py and client.py to."),
    prefix: str = typer.Option(_prefix, help="Name prefix for the domain."),
):
    schema_raw = graphql_schema.read_text()
    client_name = to_client_name(prefix)
    schema_name = to_schema_name(prefix)
    sdk = to_client_sdk(schema_raw, client_name, schema_name)
    output_dir = (output_dir or graphql_schema.parent).absolute()
    output_dir.mkdir(exist_ok=True)

    for name, content in sdk.items():
        output = output_dir / name
        output.write_text(content)
        click.echo(f"Wrote file {output.relative_to(Path.cwd())}")


@app.command("togql", help="Input a pydantic schema to create .graphql schema")
def to_gql(
    schema_module: Path = typer.Argument(
        _schema_module or ..., help="Pydantic schema to convert. Path to a .py file or Python dot notation "
    ),
    graphql_schema: Path = typer.Option(_graphql_schema or ..., help="File path for the output."),
    prefix: str = typer.Option(_prefix, help="Name prefix for the domain."),
):
    if str(schema_module).endswith(".py"):
        click.echo(f"Got file {schema_module}, trying to import it...")
        module_name = schema_module.stem
        spec = importlib.util.spec_from_file_location(module_name, schema_module)
        module = importlib.util.module_from_spec(spec)  # type:ignore[arg-type]
        sys.modules[module_name] = module
        spec.loader.exec_module(module)  # type:ignore[union-attr]
    else:
        module_name = settings.local.get("schema_module", default=schema_module.stem)
        click.echo(f"Got module {schema_module}, trying to import it...")
        module = importlib.import_module(module_name)
    click.echo("Import successful")

    if not _prefix:
        click.echo("Searching for a schema...")
        for schema_name, instance in inspect.getmembers(module):
            if isinstance(instance, Schema):
                click.echo(f"Found schema {schema_name!r}")
                break
        else:
            click.echo("Failed to find schema, exiting..")
            exit(1)
    else:
        schema_name = to_schema_name(prefix)
        click.echo(f"Got schema name {schema_name}")
        instance = getattr(module, schema_name)

    graphql_schema.write_text(instance.as_str())
    click.echo(f"Wrote file {graphql_schema}")


@app.command("signin", help="Upload a GQL schema to CDF DM data model.")
def signin(
    cdf_cluster: str = typer.Option(_cdf_cluster or ..., help="CDF cluster name."),
    tenant_id: str = typer.Option(_tenant_id or ..., help="AD tenant ID."),
    client_id: str = typer.Option(_client_id or ..., help="AD client ID."),
    client_secret: str = typer.Option(
        _client_secret_hidden or None, prompt=True, hide_input=True, help="AD client secret."
    ),
    project: str = typer.Option(_project or ..., help="Name of CDF project."),
):
    if client_secret == _client_secret_hidden:
        client_secret = _client_secret
    if client_secret == _client_secret_none:
        auth_option = "--device-code"
        auth_option_hidden = None
    else:
        auth_option = f"--client-secret='{client_secret}'"
        auth_option_hidden = f"--client-secret='{client_secret[:3]}{'*' * (len(client_secret) - 3)}'"

    command = [
        "cdf",
        "signin",
        f"'{project}'",
        f"--cluster='{cdf_cluster}'",
        f"--tenant='{tenant_id}'",
        f"--client-id='{client_id}'",
        auth_option,
    ]
    msg = f"Executing:\n{' '.join(command)}"
    if auth_option_hidden:
        msg = msg.replace(auth_option, auth_option_hidden)
    typer.echo(f"Executing:\n{msg}")
    subprocess.call(command)


@app.command("upload", help="Upload a GQL schema to CDF DM data model.")
def upload(
    graphql_schema: Path = typer.Argument(_graphql_schema or ..., help="GraphQL schema to upload."),
    space: str = typer.Option(_space or ..., help="Space ID in CDF Domain Modeling"),
    data_model: str = typer.Option(_datamodel or ..., help="ID of Data Model in CDF Domain Modeling"),
    schema_version: int = typer.Option(_schema_version or ..., help="Version of the schema to app or update."),
):
    command = [
        "cdf",
        "data-models",
        "publish",
        f"--file='{graphql_schema}'",
        f"--space='{space}'",
        f"--external-id='{data_model}'",
        f"--version='{schema_version}'",
    ]
    typer.echo(f"Executing:\n{' '.join(command)}")
    subprocess.call(command)


def main():
    sys.path.append(os.getcwd())
    app()


if __name__ == "__main__":
    main()
