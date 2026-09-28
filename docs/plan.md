# Project Plan
## Overview

This document outlines the project plan for the Localis project, detailing the objectives, scope, timeline, and key milestones.

## Objectives

- Bring API, data merging/validation and automated data fetching to release v1.0

## MVP Features

~~- Update cities registry to lazy load for faster initialization/import.~~
~~- Implement resolve-subdivisions skill & MCP for locally automated data reconciliation when merging ISO and geonames datasets.~~
~~- Add checksums to data fetching to skip unnecessary downloads~~
- Implement cron job in GHA ci for automated data fetching, updating the dataset and drafting a PR if the merging of the new data succeeds. If it cannot be merged automatically, notify the team for manual intervention.


## Backlog
- Implement autocomplete for registries and/or global interface.
- Patch missing flags for countries
- Implement native languages in countries?