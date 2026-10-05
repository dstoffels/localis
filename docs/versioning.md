# Versioning

localis follows [Semantic Versioning](https://semver.org/).

## Public API

The public API is everything `localis` exports at the top level (`localis.__all__`): the registries and their documented methods, `MISSING`, and the entity types with the fields documented under [Entities](../README.md#entities). Anything else, such as submodules like `localis.indexes` or names starting with `_`, can change in any release.

## What each release can change

| Release | Example | Contains |
|---|---|---|
| Patch | 3.0.1 | data refreshes and bug fixes |
| Minor | 3.1.0 | new, backward-compatible features |
| Major | 4.0.0 | changes that can break code written against the public API |

Records changing with their sources (added, removed or renamed) isn't a breaking change, and every monthly data refresh is a patch release. IDs are renumbered by every refresh, so store `key`, not `id`.

## Deprecation

Before anything in the public API is removed or changed incompatibly, a minor release deprecates it. It keeps working, raises a `DeprecationWarning`, and the [CHANGELOG](../CHANGELOG.md) names its replacement. It's removed in the next major release at the earliest.

## Pre-releases

A major release ships as betas first, then release candidates. pip installs these only with `--pre` or an exact pin (`localis==3.0.0b1`).

- **Beta** (`3.0.0b1`): the API can still change between betas, and the CHANGELOG lists every change.
- **Release candidate** (`3.0.0rc1`): the API is frozen and only fixes land. A beta becomes a release candidate after two weeks with no API changes.
- **Final** (`3.0.0`): a release candidate becomes final after one week with no blocking issue. Nothing else changes besides the version.

## Support

Only the latest release gets data refreshes and fixes, pre-releases included. 2.x is no longer maintained.
