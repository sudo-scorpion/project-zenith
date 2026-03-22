# Rollback

Zenith writes one manifest per install transaction under `~/.local/share/zenith/manifests/` and stores file backups under `~/.local/share/zenith/backups/`.

## `zen rollback`

Rollback operates on the latest manifest transaction.

It will:

- restore backed-up files from that transaction
- remove Zenith-created files from that transaction
- move the `latest.json` pointer to the previous manifest when one exists
- warn and exit cleanly when there is nothing to roll back

## `zen uninstall`

Uninstall replays rollback across all manifest transactions and then removes the Zenith config/share directories.

That means it removes:

- Zenith-managed launchers
- Zenith config, prompt, log, cache, and state files
- manifest and backup state under Zenith-owned directories
