import importlib
import importlib.util
import inspect
import os
import subprocess
import sys
from pathlib import Path
from typing import Optional

import click
import typer
from packaging import version

from cognite.dm_clients.config import settings
from cognite.dm_clients.domain_modeling.schema import Schema
from cognite.gqlpygen.generator import to_client_sdk
from cognite.gqlpygen.misc import to_client_name, to_schema_name

app = typer.Typer()


_client_secret = settings.get("cognite.client_secret")
_prefix = settings.get("local.prefix", "")


def _hide_pw(secret: str, value: Optional[str] = None) -> str:
    """
    Hide secret from value:

    >>> _hide_pw("SeCrEt", "Here is my SeCrEt password!")
    'Here is my SeC*****... password!'
    >>> _hide_pw("SeCrEtPeRsEcReT")
    'SeC*****...'
    >>> _hide_pw("SeCrEt", "No secret here.")
    'No secret here.'
    >>> _hide_pw("An", "An edge case.")
    'An*****... edge case.'
    >>> _hide_pw("", "Nothing changes.")
    'Nothing changes.'
    """
    return (secret if value is None else value).replace(secret, f"{secret[:3]}*****..." if secret else "")


_client_secret_none = "None (use device flow)"
_client_secret_hidden = _hide_pw(_client_secret) if _client_secret else ""


def _check_cdf_cli() -> None:
    try:
        cdf_version = subprocess.check_output(["cdf", "--version"])
    except FileNotFoundError:
        typer.echo(
            "Command 'cdf' not found, please see https://docs.cognite.com/cdf/cli/ for installation instructions.",
            err=True,
        )
        sys.exit(1)

    min_version = version.Version("2.0.0")
    installed_version = version.parse(cdf_version.decode().strip())
    if installed_version < min_version:
        typer.echo(
            f"Too old version of 'cdf' ({installed_version}), at least {min_version} is needed."
            f" Please see https://docs.cognite.com/cdf/cli/ for installation instructions.",
            err=True,
        )
        sys.exit(1)


@app.command("topython", help="Create pydantic schema and Python DM client from a .graphql schema.")
def to_python(
    graphql_schema: Path = typer.Argument(settings.get("local.graphql_schema", ...), help="GraphQL schema to convert"),
    output_dir: Path = typer.Option(
        Path(_graphql_schema).parent if (_graphql_schema := settings.get("local.graphql_schema")) else Path.cwd(),
        help="Directory to write schema.py and client.py to.",
    ),
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
        settings.get("local.schema_module", ...),
        help="Pydantic schema to convert. Path to a .py file or Python dot notation "
    ),
    graphql_schema: Path = typer.Option(settings.get("local.graphql_schema", ...), help="File path for the output."),
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
    cdf_cluster: str = typer.Option(settings.get("cognite.cdf_cluster", ...), help="CDF cluster name."),
    tenant_id: str = typer.Option(settings.get("cognite.tenant_id", ...), help="AD tenant ID."),
    client_id: str = typer.Option(settings.get("cognite.client_id", ...), help="AD client ID."),
    client_secret: str = typer.Option(
        _client_secret_hidden if _client_secret else _client_secret_none,
        prompt=True,
        prompt_required=not _client_secret,
        hide_input=True,
        help="AD client secret.",
    ),
    project: str = typer.Option(settings.get("cognite.project", ...), help="Name of CDF project."),
):
    if client_secret == _client_secret_none:
        client_secret = ""
    _check_cdf_cli()
    command = [
        "cdf",
        "signin",
        f"'{project}'",
        f"--cluster='{cdf_cluster}'",
        f"--tenant='{tenant_id}'",
        f"--client-id='{client_id}'",
        (f"--client-secret='{client_secret}'" if client_secret else "--device-code"),
    ]
    typer.echo(f"Executing:\n{_hide_pw(client_secret, ' '.join(command))}")
    subprocess.call(command)


@app.command("upload", help="Upload a GQL schema to CDF DM data model.")
def upload(
    graphql_schema: Path = typer.Argument(settings.get("local.graphql_schema", ...), help="GraphQL schema to upload."),
    space: str = typer.Option(settings.get("dm_clients.space", ...), help="Space ID in CDF Domain Modeling"),
    data_model: str = typer.Option(
        settings.get("dm_clients.datamodel", ...),
        help="ID of Data Model in CDF Domain Modeling",
    ),
    schema_version: int = typer.Option(
        settings.get("dm_clients.schema_version", ...),
        help="Version of the schema to app or update.",
    ),
):
    _check_cdf_cli()
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
