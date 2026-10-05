# Security Policy

## Supported versions

Only the latest release of localis receives security fixes, pre-releases included; 2.x is no longer maintained (see [docs/versioning.md](docs/versioning.md#support)). Upgrade to the latest release before reporting, to check the issue still exists.

## Reporting a vulnerability

Please report vulnerabilities privately, not in a public issue. Open the repository's **Security** tab and choose **Report a vulnerability**. Only the maintainer can see the report.

Include the localis version, a minimal reproduction, and what an attacker could do with it.

## Scope

localis runs offline and reads only the data files shipped inside the package. The issues most relevant to it are:

- a query or input that makes a lookup, filter or search take unreasonably long or use unreasonable memory, which matters to anyone running localis behind a public endpoint
- a problem with the published package itself, such as files on PyPI that don't match the release built from this repository
