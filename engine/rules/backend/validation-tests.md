# Backend Validation And Tests

- For BE service/API changes, run `dotnet build` when feasible.
- Add or run targeted tests/repro requests for changed workflow/state/data-access behavior.
- Full suite failures need attribution by error signature; do not summarize as generic failure.
- If live SQL is unavailable, run the targeted InMemory-runnable subset when possible and record SQL-dependent skips.
- For FE+BE contract work: BE build -> DTO/client regen -> FE typecheck.
- Verification claims require actual command/request evidence and the user path or API path tested.
