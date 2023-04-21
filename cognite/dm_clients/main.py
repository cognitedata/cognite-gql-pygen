import os
import subprocess
import sys
from importlib import import_module
from pathlib import Path
from typing import Optional

import typer

app = typer.Typer()


def _run(bash_script):
    return subprocess.call(str(bash_script), shell=True)


@app.command()
def signin():
    """
    Sign in to a CDF project.
    Takes configuration from config.yaml.
    """
    _run(Path(__file__).parent / "bin/cdf_signin.sh")


schema_app = typer.Typer()


_schema_name_option = typer.Option("schema", help="Variable name for Schema instance inside the package")


@schema_app.command()
def render(schema_name: Optional[str] = _schema_name_option):
    """
    Writes the GraphQL schema from Python code.
    Takes configuration from config.yaml.
    """

    from cognite.dm_clients.config import settings

    schema_module = import_module(settings.local['schema_module'])

    try:
        schema = getattr(schema_module, schema_name)
    except AttributeError as exc:
        msg = "Schema not found. Did you need to set --schema-name option (default is \"schema\")?"
        raise ValueError(msg) from exc

    sys.stdout.write(schema.as_str())


@schema_app.command()
def publish():
    """
    Uploads the GraphQL schema file to DM.
    Takes configuration from config.yaml.
    """
    _run(Path(__file__).parent / "bin/schema_publish.sh")


app.add_typer(schema_app, name="schema")


def main():
    sys.path.append(os.getcwd())
    app()


if __name__ == "__main__":
    main()
