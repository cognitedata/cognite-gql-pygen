import pytest

from cognite.dm_clients.domain_modeling import DomainModel, Schema
from examples.cinematography_domain.schema import cine_schema
from tests.constants import CINEMATOGRAPHY


def generate_graphql_from_pydantic_data():
    expected = (CINEMATOGRAPHY / "schema.graphql").read_text()
    yield pytest.param(cine_schema, expected, id="Cinematography example")


@pytest.mark.parametrize("schema, expected_graphql", list(generate_graphql_from_pydantic_data()))
def test_generate_graphql_from_pydantic(schema: Schema[DomainModel], expected_graphql: str):
    assert schema.as_str() == expected_graphql
