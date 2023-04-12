from __future__ import annotations

import logging
from typing import Dict, Optional, Type, get_args

import strawberry
from pydantic import Extra

from cognite.dm_clients.cdf.data_classes_dm_v3 import DataModelBase

__all__ = [
    "DomainModel",
]


logger = logging.getLogger(__name__)


class DomainModel(DataModelBase):
    """
    Base class for all models in schema_types.py

    A bit of nomenclature: instances of DomainModel we call "items".
    This is pretty much because all other words I can think of have been taken by DM >:]

    Even this is confusing... A data model in DM is a collection of domain models.
    """

    externalId: strawberry.Private[Optional[str]] = None
    # Private ^ means the field will not be exposed in GraphQL schema
    # Used here because actual objects (returned from the API) have these fields. These are "implicit" field.

    class Config:
        extra = Extra.forbid
        #  ^ raises exception if extra fields are passed to the constructor. Very useful for development.
        arbitrary_types_allowed = True

    @classmethod
    def get_one_to_many_attrs(cls) -> Dict[str, Type[DomainModel]]:
        """
        Get attributes which describe one-to-many relationships.
        These attributes usually require additional considerations with DM.
        """
        attrs = {}
        props: Dict[str, dict] = cls.schema()["properties"]
        for field_name, field_info in props.items():
            if field_info.get("type") != "array":
                continue  # one-to-many has to be an array
            if field_info.get("items", {}).get("$ref", "").startswith("#/definitions/"):
                # TODO assuming that the reference is local, probably ok.
                field_type = cls.get_type_for_attr(field_name)
                attrs[field_name] = field_type
        return attrs

    @classmethod
    def get_one_to_one_attrs(cls) -> Dict[str, Type[DomainModel]]:
        """Get attributes which describe one-to-one relationships."""
        attrs = {}
        props: Dict[str, dict] = cls.schema()["properties"]
        for field_name, field_info in props.items():
            if field_info.get("type") == "array":
                continue  # one-to-one cannot be an array
            if field_info.get("$ref", "").startswith("#/definitions/"):
                # TODO assuming that the reference is local, probably ok.
                field_type = cls.get_type_for_attr(field_name)
                attrs[field_name] = field_type
        return attrs

    @classmethod
    def get_type_for_attr(cls, attr: str) -> Type[DomainModel]:
        """Given an attribute, return a DomainModel subclass to which the attribute refers to."""
        field_type = cls.__fields__[attr].type_
        # strip annotations (like List[] and Optional[]):
        while type_args := get_args(field_type):
            field_type = type_args[0]
        if issubclass(field_type, DomainModel):
            return field_type
        raise ValueError(f"Attr {attr} not a reference to DomainModel.")