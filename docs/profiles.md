# Zenith Profiles

Zenith supports two profiles on the same engine.

## `safe`

- conservative defaults
- no alias overrides for `ls`, `cat`, or `cd`
- best fit for shared systems, CI, and containerized work
- same rollback, uninstall, and manifest protections as every other profile

## `personal`

- enables alias overrides in the generated Zenith bash fragment
- keeps the same lifecycle protections and AI policy model
- better fit for a single-user interactive shell

## Shared behavior

Both profiles share:

- the same config format
- the same manifest and backup system
- the same container detection and mode rules
- the same AI command classification and execution policy
