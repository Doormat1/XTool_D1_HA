# xTool Laser Home Assistant integration (HACS)

This repository now includes a HACS-ready custom integration in:

- `custom_components/xtool_laser`

## What it provides

- Job progress sensor (`/progress`)
- Working state sensor (`/system?action=get_working_sta`)
- Machine event sensor (WebSocket on `:8081`)
- Machine type sensor (`/getmachinetype`)
- Safety/config binary sensors from `/peripherystatus`
- Services to control jobs: `xtool_laser.pause_job`, `xtool_laser.resume_job`, `xtool_laser.stop_job`
- Setup via manual host entry or UDP auto-discovery

## Install in Home Assistant via HACS

1. Put this repo on GitHub (or use your existing one).
2. In HACS, add this repo as a custom repository (category: Integration).
3. Install **xTool Laser**.
4. Restart Home Assistant.
5. Add integration: **Settings → Devices & Services → Add Integration → xTool Laser**.
6. Enter the local IP/host of your xTool.

## Notes

- The integration is local-only and uses xTool ports `8080` (HTTP) and `8081` (WebSocket).
- Keep your xTool and Home Assistant on the same network.
- Protocol compatibility depends on firmware/model behavior.

## Dashboard card example

- A ready-to-paste Lovelace example is included in `xtool_lovelace_example.yaml`.
- A compact phone-oriented variant is included in `xtool_lovelace_mobile.yaml`.
- Add a **Manual card** and paste the YAML.
- If your entity IDs differ, update the `sensor.xtool_laser_*` and `button.xtool_laser_*` names to match your installation.
