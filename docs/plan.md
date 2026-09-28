# Project Plan
## Overview

This document outlines the project plan for the Localis project, detailing the objectives, scope, timeline, and key milestones.

## Objectives

- Bring API, data merging/validation and automated data fetching to release v1.0

## Features

- Implement cron job in ci for automated data fetching, updating the dataset and drafting a PR if the merging of the new data succeeds. If it cannot be merged automatically, notify the team for manual intervention.
- Implement autocomplete for registries and/or global interface.
- Add checksums to data fetching to skip unecessary downloads