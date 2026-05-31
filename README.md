# ha-traefik-gate

Home Assistant custom integration that replaces the `traefik-gate` Docker service with native HA entities and a built-in ForwardAuth HTTP listener.

## What it does

Exposes two timer-based access profiles — **Protected** and **Plex** — as HA switch entities. When a switch is toggled on, Traefik allows external traffic through for the configured duration. When the timer expires (or the switch is turned off), traffic is blocked. LAN and Tailscale CGNAT addresses bypass the gate automatically.

A standalone aiohttp HTTP server listens on a configurable port (default `8082`) and responds to Traefik ForwardAuth calls at `/auth/protected` and `/auth/plex`.

## Entities

| Entity | Type | Description |
|---|---|---|
| Protected External Access | Switch | Toggle protected-profile external access |
| Plex External Access | Switch | Toggle Plex-profile external access |
| Protected Default Duration | Number | Default session length when switch is turned on (hours) |
| Plex Default Duration | Number | Default session length when switch is turned on (hours) |
| Protected Time Remaining | Sensor | Minutes until protected session expires |
| Plex Time Remaining | Sensor | Minutes until Plex session expires |

## Installation via HACS

1. Add this repository as a custom HACS repository (Integrations category):
   `https://github.com/gromlab/ha-traefik-gate`
2. Install **Traefik Gate** from HACS.
3. Restart Home Assistant.
4. Add the integration via **Settings → Integrations → Add Integration → Traefik Gate**.

## Configuration

| Field | Default | Description |
|---|---|---|
| ForwardAuth listen port | `8082` | Port the ForwardAuth HTTP server binds to |
| Protected default hours | `1` | Session length for the protected profile |
| Protected min/max/step | `1` / `24` / `1` | Bounds for the duration number entity |
| Plex default hours | `24` | Session length for the Plex profile |
| Plex min/max/step | `24` / `168` / `24` | Bounds for the duration number entity |

## Traefik middleware

Update your ForwardAuth middleware URLs from the old Docker service to the HA host:

```yaml
http:
  middlewares:
    protected-gate:
      forwardAuth:
        address: "http://<HA_HOST>:8082/auth/protected"
        trustForwardHeader: true

    plex-gate:
      forwardAuth:
        address: "http://<HA_HOST>:8082/auth/plex"
        trustForwardHeader: true
```

Replace `<HA_HOST>` with your Home Assistant VM's hostname or IP address.

## Migrating from Docker traefik-gate

1. Install and configure this integration.
2. Verify ForwardAuth is working via the `/healthz` endpoint: `curl http://<HA_HOST>:8082/healthz`
3. Update Traefik middleware config to point to the new address.
4. Remove the `traefik-gate` Docker service from FROST.
