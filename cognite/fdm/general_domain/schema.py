from __future__ import annotations

import logging
from typing import Dict, Generic, List, Optional, Type, TypeVar, Union, cast, get_args

import strawberry
from strawberry import scalar
from strawberry.experimental.pydantic import UnregisteredTypeException
from strawberry.schema.config import StrawberryConfig

from cognite.fdm import scalars
from cognite.fdm.general_domain.domain_model import DomainModel
from cognite.fdm.misc import to_snake

DomainModelT = TypeVar("DomainModelT", bound=DomainModel)


logger = logging.getLogger(__name__)


class Schema(Generic[DomainModelT]):
    def __init__(self) -> None:
        self.types_map: Dict[str, Type[DomainModelT]] = {}
        self._root_type: Optional[type] = None
        self._root_type_cls: Optional[Type[DomainModelT]] = None
        self._processed_names: List[str] = []
        self._scalar_names: List[str] = []

    def _strawberry_schema(self) -> strawberry.Schema:
        if self._root_type is None:
            raise ValueError("define one of the schema types with @schema.register_type(root_type=True)")
        return strawberry.Schema(query=self._root_type, config=StrawberryConfig(auto_camel_case=False))

    def as_str(self) -> str:
        """
        Removing things that FDM does not need:
         * `schema { query: ... }`
         * `scalar ...`
        """
        raw_schema = self._strawberry_schema().as_str()
        raw_lines = raw_schema.splitlines()
        # Loop over all the lines *backwards* and remove what we don't need.
        fdm_lines: List[str] = []
        for line in raw_lines[::-1]:
            if line.startswith("scalar "):
                if fdm_lines:
                    fdm_lines.pop()
                continue
            if line.startswith("schema {"):
                fdm_lines.pop()
                fdm_lines.pop()
                fdm_lines.pop()
                continue
            fdm_lines.append(line)
        return "\n".join(fdm_lines[::-1])

    def register_type(
        self, lowercase_type_name: Optional[Union[str, Type[DomainModelT]]] = None, root_type: bool = False
    ):
        """Class decorator for schema types."""

        def _register_type(cls: Type[DomainModelT]) -> Type[DomainModelT]:
            if not issubclass(cls, DomainModel):
                raise ValueError(
                    f"Classes used with @register_type must inherit from DomainModel, this one does not: {cls}",
                )
            name = cast(str, lowercase_type_name or to_snake(cls.__name__))
            if name in self.types_map:
                raise ValueError(f"Duplicate type in types_map: {name}")
            self.types_map[name] = cls

            if root_type:
                if self._root_type_cls is not None:
                    raise ValueError(f"Multiple types registered with root_type=True: {self._root_type_cls}, {cls}")
                self._root_type_cls = cls

            return cls

        if isinstance(lowercase_type_name, type):
            # decorator was used without attributes, so lowercase_name is actually a DomainModel class
            cls_ = cast(Type[DomainModelT], lowercase_type_name)
            lowercase_type_name = to_snake(cls_.__name__)
            return _register_type(cls_)

        return _register_type

    def _do_register(self, name: str, cls: Type[DomainModelT]) -> None:
        # Register type with strawberry schema
        if name in self._processed_names:
            return
        self._processed_names.append(name)

        field_names = [key for key in cls.__fields__ if key not in {"externalId"}]

        scalar_fields = {}
        for field_name in field_names:
            field = cls.__fields__[field_name]
            field_type = field.annotation
            while type_args := get_args(field_type):
                field_type = type_args[0]
            type_name = field_type.__name__
            if type_name in scalars.__all__:
                scalar_name = f"{type_name}Scalar"
                if scalar_name not in self._scalar_names:
                    self._scalar_names.append(scalar_name)
                    globals().update({scalar_name: scalar(field_type)})
                scalar_fields[field_name] = cls.__annotations__[field_name].replace(type_name, scalar_name)

        cls_dict = {}
        if scalar_fields:
            cls_dict["__annotations__"] = scalar_fields
            for field_name in scalar_fields:
                field_names.remove(field_name)

        try:
            strawberry_type = strawberry.experimental.pydantic.type(model=cls, fields=field_names)(
                type(cls.__name__, (), cls_dict),
            )
        except UnregisteredTypeException:
            # Order matters when using `strawberry.experimental.pydantic.type` (unlike `strawberry.type`).
            # For reasons unknown.
            # So when types are out of order, just run one more `close()` to work on other types, then
            # try again when it returns. List of names in `self._processed_names` guards against duplicates.
            self.close()
            strawberry_type = strawberry.experimental.pydantic.type(model=cls, fields=field_names)(
                type(cls.__name__, (), cls_dict),
            )

        if self._root_type_cls == cls:
            self._root_type = strawberry_type

    def _update_forward_refs(self):
        """Resolve pydantic forward references."""
        for klass in self.types_map.values():
            klass.update_forward_refs()

    def close(self):
        self._update_forward_refs()
        for name, cls in self.types_map.items():
            self._do_register(name, cls)
