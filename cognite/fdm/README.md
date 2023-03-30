# Non-GraphQL FDM API

This is an experimental module which wraps non-GraphQL API for FDM.

It provides a simplified set of features for interacting with FDM in an intuitive way and without needing to work with
the underlying data structures.

**[DISCLAIMER!]** This project is in a highly experimental no guarantees are made for consistency between versions. The
project may also become deprecated if the experimentation turns out to be a dead end.


## Motivation

Uploading some data into a FDM data model was cumbersome when interacting directly with the FDM API.


## Concepts

`fdm` package takes Python code as the "source of truth". So a normal workflow is like this:

1. Define use case models in Python (in a "schema" module).
2. Use CLI from this package to generate GraphQL schema.
3. Use CLI from this package to upload this schema to FDM.
4. Populate and manipulate data items / instances in FDM using a `DomainClient` provided in this package.


> Note: This might change in the future: as `gqlpygen` module evolves we should be able to dynamically create Python
> data types from existing GraphQL schemas in FDM.


## Future

Uncertain. No guarantees are made about maintenance of this project. Contributions, however, are very welcome!

With the (future) arrival of GraphQL mutations in FDM, this package might become obsolete.


## Glossary

 * FDM - Flexible Data Model, data service by Cognite. For our purposes, it is "the API".
 * `fdm` - this package
 * Space - FDM object, a high-level container for all things in FDM. Like a namespace. Subordinate only to CDF project.
 * Data Model - Often used interchangeably with "Schema", a set of Domain Models (a.k.a. schema types) that together
   help model a use case.
 * Domain - knowledge domain, similar to use case (though we can have multiple use cases that use a single Domain,
   like several clients in a very similar business)
 * Domain Model - an `fdm` term - often used interchangeably with "schema type" - a single class of objects with all
   its fields, e.g. "pump" or "generator".
 * Item - an `fdm` term - an instance of a Domain Model, e.g. generator "G42".
 * Instance - an FDM term - a data entity, either a Node or an Edge (see below).
 * Node - an FDM term - a data entity, can contain multiple fields.
 * Edge - an FDM term - a data entity that connects two nodes (directionally).
 * DomainAPI - an `fdm` term - a top-level Python class for a Domain. It provides easy access to various DomainModelAPIs
   (see below).
 * DomainModelAPI - an `fdm` term - a Python class (or class instance) which provides management over a single Domain
   Model, e.g. create new pumps, delete a pump, list all pumps...
 * DomainClient - an `fdm` term - a Python class (or class instance) which serves as a namespace for easy acces to all
   DomainModelAPIs in a use case.


## Installation

1. `pip install cognite-gql-pygen`
2. Create a `config.yaml` file (exact name not important), see [config.example.yaml](./config.example.yaml).
   - > TODO: Then need for `config.yaml` should be removed...
3. Define `FDM_CONFIG` env variable to contain the full path to `config.yaml` file.
4. Test if it works:
   ```
   $ python
   >>> from cognite.fdm.general_domain.domain_client import get_empty_domain_client
   >>> c = get_empty_domain_client()
   >>> c._client.spaces.list()
   [Space(space="...
   ```
5. Install CDF CLI client
   - [setup instructions](https://docs.cognite.com/cdf/cli/)
   - But basically:
     ```
     npm i -g @cognite/cdf-cli
     ```


## Usage

### Create Schema

To create a schema, see [examples/cinematography_domain/schema.py](../../examples/cinematography_domain/schema.py)
example.


Required features of a schema module:
 - Instantiates a `Schema`.
 - Defines at least one Model class.
   - Model classes need to inherit from `DomainModel`.
   - They need to be registered using `@my_schema.register_type`.
     - Exactly one Model class needs to be registered as "root type":
       - `@my_schema.register_type(root_type=True)`.
- After the last Model class definition, call `my_schema.close()`
- When the module is executed directly, output the GraphQL schema to stdout:
  - ```
    if __name__ == "__main__":
        print(my_schema.as_str())
    ```

#### Upload the schema

> Before proceeding, make sure that `config.yaml` is populated with credentials and configuration.


##### Step 1: Render Schema

GraphQL schema file is committed to this repo, so this step is not required, but it is here for completeness.

Execute `fdm schema render`. This will update the schema file (defined in `config.yaml`) according to Python code in
the schema module.


##### Step 2: Upload Schema

Authenticate against CDF by running `fdm signin`. The authentication data is cached on the filesystem
locally, so this is needed rarely (every few? days).

Execute `fdm schema publish`. This will upload the schema to CDF / FDM.

> Note: Depending on the changes made to the schema, you might be required to update the schema version in config.yaml.
> This happens when the changes are not backwards-compatible, e.g. deleting a field.


### Manipulate Items

See `_main()` in [examples/cinematography_domain/client.py](../../examples/cinematography_domain/client.py) for a simple
usage example.

A few general notes:

 * `DomainClient` dynamically instantiates a `DomainModelAPI` for every model in the schema.
   * These APIs are named after the model name.
     * e.g. if the model class is names `MyModel`, the API will be accessible at `my_domain_client.my_model`.
 * Most methods on `DomainModelAPI` take a list of items.
   * When creating a single item, remember to wrap it in a list!
 * To update an existing item, use `create()`.
   * But make sure that the `externalId` of the item is populated (otherwise the API will create a new item).
 * Items with missing `externalId` will get one randomly-generated when passed to `create()`.


### Low-level API

To manipulate nodes and edges directly, access this API via `_client`:

``` python
model1_instances = my_client._client.nodes.list(my_client.model1.view)
```

Note that `_client` is a subclass of `CogniteClient` and can be used to access "classic" data types (Assets,
Timeseries, etc.)

## Pros and Cons

Pros:

 * Simplifies interaction with FDM API
 * Uses Pydantic to validate the items before sending then to the API.

Drawbacks and Limitations:

 * Not all features of FDM are supported.
   * `fdm` is only tested to work within a single space.
     * Across-space relationships are in principle possible, but some work would be needed to implement it.
   * Nodes (and consequently items) work with properties from only one view.
     * No hard barriers to implementing this in the future.
 * Not terribly efficient.
   * Developed mostly as a tool for getting things done, rather than an optimal implementation.
 * Unpolished, possibly with some bugs.
   * External IDs are constructed, not safely considering the char limit.
   * ...


### TODO

 * Missing support for custom scalar types (`JSON` and `Timestamp`, others in the future)
    * priority, in progres
 * Better alternative to `config.yaml`.
 * Add support for retrieving items via graphql endpoint.
 * Expand unit test coverage
 * Lots of TODOs in the code


## Example: Cinematography Domain

Contained in `examples/cinematography_domain`, this is a minimal toy example of the basic features of this package.
`schema.py` shows implementation of a schema (a.k.a. data model), and `client.py` shows how to manipulate items
programmatically once the schema is in place.


## Contributing

Contributions welcome!

See [TODO](#todo) above.

### Project Structure

Important modules:
 * `cognite/fdm/cdf`
    * general-purpose FDM client (nothing specific to PowerOps in here)
    * inspired by https://github.com/cognitedata/tech-demo-powerops/ :]
 * `cognite/fdm/general_domain`
    * base classes for use cases, "boilerplate"
 * `examples/cinematography_domain`
    * a toy example use case with minimal code