from __future__ import annotations

import logging
from typing import List, Optional, cast

from cachelib import BaseCache, SimpleCache
from cinematography_domain.schema import Movie, Person, cine_schema

from cognite.fdm.cdf.get_client import get_client_config
from cognite.fdm.general_domain import DomainClient, DomainModelAPI


class CineClient(DomainClient):
    """
    Domain-specific client class for the entire domain.
    This class can contain any domain-specific logic, but is entirely optional. The attributes below (`actor` and
    `movie`) are create in the base class, and here we have only added type annotations so that IntelliSense can work.
    """

    person: DomainModelAPI[Person]
    movie: DomainModelAPI[Movie]


def get_cine_client(
    cache: Optional[BaseCache] = None,
    space_id: Optional[str] = None,
    data_model: Optional[str] = None,
    schema_version: Optional[int] = None,
) -> CineClient:
    """Quick way of instantiating a CineClient with sensible defaults for development."""
    cache = SimpleCache() if cache is None else cache
    config = get_client_config()
    return CineClient(cine_schema, DomainModelAPI, cache, config, space_id, data_model, schema_version)


def _upload_data(client: CineClient) -> None:
    """Uploading some dummy instances (a.k.a. "items")."""
    client.person.delete(client.person.list(resolve_relationships=False))
    client.movie.delete(client.movie.list(resolve_relationships=False))

    movies = [
        Movie(
            externalId="movie1",
            title="Casablanca",
            director=Person(externalId="person1", name="Michael Curtiz"),
            actors=[
                Person(externalId="person2", name="Humphrey Bogart"),
                Person(externalId="person3", name="Ingrid Bergman"),
            ],
        ),
        Movie(
            externalId="movie2",
            title="Star Wars: Episode IV – A New Hope",
            director=Person(externalId="person4", name="George Lucas"),
            actors=[
                Person(externalId="person5", name="Mark Hamill"),
                Person(externalId="person6", name="Harrison Ford"),
                Person(externalId="person7", name="Carrie Fisher"),
            ],
        ),
    ]
    client.movie.create(movies)


def _main() -> None:
    logging.basicConfig()
    logging.getLogger("cognite.fdm").setLevel("DEBUG")

    client = get_cine_client()
    persons = client.person.list()

    if not persons:
        print("(first time only) Populating FDM with data.\n")
        _upload_data(client)

    movies = client.movie.list()
    for movie in movies:
        print(movie.title)
        print(f"  - directed by: {movie.director.name if movie.director else 'None'}")
        actors = cast(List[Person], movie.actors or [])  # to keep mypy happy *
        print("  * starring *")
        for actor in actors:
            print(f"  {actor.name}")
        print()

    # * in FDM we cannot do `actors: [Person!]` nor `[Person!]!`, we can only do `[Person]`


if __name__ == "__main__":
    _main()
