from __future__ import annotations

from typing import Optional

from cognite.dm_clients.domain_modeling import DomainModel


class Case(DomainModel):
    __root_model__ = True
    scenario: Optional[Scenario]
    start_time: str
    end_time: str


class Scenario(DomainModel):
    name: str


expected = """
type Case {
  scenario: Scenario
  start_time: String!
  end_time: String!
}

type Scenario {
  name: String!
}
"""