# Chassis AirTag Pilot

Class8 accepts authenticated location observations at `POST /bot/chassis/locations`.
The bot client needs the existing `write:orders` scope. Each observation contains:

```json
{
  "chassis_id": "OSLM001",
  "airtag_name": "Chassis OSLM001",
  "latitude": 39.2904,
  "longitude": -76.6122,
  "observed_at": "2026-10-10T12:15:00Z"
}
```

For active `Vehicles` rows with `Type = Chassis`, `Unit` is the chassis ID and
`Title` is the assigned Find My item name. Class8 rejects a different AirTag
name when `Title` is populated.

## Mac setup

1. Copy `scripts/chassis_airtags.example.json` to
   `~/.config/class8/chassis_airtags.json` and enter the exact Find My item
   names.
2. Copy `scripts/airtag-collector.env.example` to
   `~/.config/class8/airtag-collector.env`, fill in the Class8 URL and bot
   credentials, and restrict it with `chmod 600`. The secret must not be
   committed.
3. Grant Full Disk Access to the Python executable used by the launch agent.
   macOS 26 protects `~/Library/Caches/com.apple.findmy.fmipcore/Items.data`.
4. Test locally:

   ```bash
   /Users/automation/shared/webapp-venv/bin/python scripts/airtag_chassis_collector.py --dry-run
   ```

5. Make `scripts/airtag_chassis_collector_worker.sh` executable. Install
   `scripts/com.class8.airtag-chassis-collector.plist` under
   `~/Library/LaunchAgents`, then bootstrap it with `launchctl`. It runs at load
   and every 900 seconds.

The Class8 page is `/ChassisLocations`. Green is under one hour old, amber is
one to four hours old, and red is over four hours old or missing.

## Apple limitation

Apple does not provide a public owner-location API for AirTags. This pilot reads
the cache written by Find My on this Mac and can require adjustment after macOS
updates. The collector fails closed when cache access or parsing is unavailable.
