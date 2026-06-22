# Frontend Contracts And Generated Code

- Generated DTOs, constants, and generated API client are read-only.
- If FE contract disagrees with BE/API spec, stop and report the mismatch; do not patch around it with hand-written DTOs.
- Cross FE+BE changes run BE build/contract first, restart BE if needed, regenerate FE DTO/client, then FE typecheck.
- Do not add permission fallback logic when generated permission constants are missing.
- Use generated ServiceStack hooks/methods through the module adapter; no raw bearer-token auth or manual client wiring.
- For contract fixes, validate both the changed BE surface and the FE compile path consuming the regenerated contract.
