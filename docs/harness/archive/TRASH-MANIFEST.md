# TRASH-MANIFEST.md
Staging area for review. Nothing here is referenced by the active harness (verified). Safe to delete after review; restore with `mv` if needed.

| # | Original path | New path | Reason | Date |
|---|---|---|---|---|
| 1 | `scripts/legacy-powershell` | `trash/scripts/legacy-powershell` | Legacy Windows PowerShell ports — deprecated on Linux | 2026-06-16 |
| 2 | `specs/legacy` | `trash/specs/legacy` | Superseded spec versions — replaced by specs/ipd-consultation/ and specs/vital-signs/ | 2026-06-16 |
| 3 | `~` (root-level dir literally named "~") | `trash/_stray-tilde-dir` | Accidental directory literally named "~" containing a stray fish config | 2026-06-16 |

## Restore instructions

To restore any item, run `mv` with the reversed paths. Example:

```fish
mv /home/dax/Documents/arabica/roast/trash/scripts/legacy-powershell /home/dax/Documents/arabica/roast/scripts/legacy-powershell
mv /home/dax/Documents/arabica/roast/trash/specs/legacy /home/dax/Documents/arabica/roast/specs/legacy
mv /home/dax/Documents/arabica/roast/trash/_stray-tilde-dir "/home/dax/Documents/arabica/roast/~"
```
