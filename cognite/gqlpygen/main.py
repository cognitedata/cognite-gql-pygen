import importlib
import importlib.util
import inspect
import os
import sys
from pathlib import Path

import click
import typer

from cognite.dm_clients.config import settings
from cognite.dm_clients.domain_modeling.schema import Schema
from cognite.gqlpygen.generator import to_client_sdk
from cognite.gqlpygen.misc import to_client_name, to_schema_name

app = typer.Typer()


_settings_local = settings.get("local", {})
_schema_file = _settings_local.get("schema_file")
_schema_dir = Path(_schema_file).parent if _schema_file else None
_prefix = _settings_local.get("prefix", "")

_schema_module = _settings_local.get("schema_module")


@app.command("topython", help="Create pydantic schema and Python DM client from a .graphql schema.")
def to_python(
    graphql_schema: Path = typer.Argument(_schema_file or ..., help="GraphQL schema to convert"),
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
    schema_module: Path = typer.Argument(_schema_module or ..., help="Pydantic schema to convert. Path to a .py file or Python dot notation "),
    schema_file: Path = typer.Option(_schema_file or None, help="File path for the output."),
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

    schema_file.write_text(instance.as_str())
    click.echo(f"Wrote file {schema_file}")


def main():
    sys.path.append(os.getcwd())
    app()


if __name__ == "__main__":
    main()
