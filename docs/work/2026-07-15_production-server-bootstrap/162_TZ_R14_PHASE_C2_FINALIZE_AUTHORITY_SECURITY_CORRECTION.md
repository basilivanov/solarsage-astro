# TZ R14 Phase C2 — finalize authority security correction

Read `159`, `160`, and `161` in full. Correct only the current builder/finalize slice; do not begin GC or promotion transaction integration.

## Allowed files

- `scripts/prod-release-authority.py`
- `scripts/tests/test-prod-release-authority.sh`
- `scripts/lib/prod-release-build.sh` and its harness only if the corrected finalized-mode contract requires a narrow adjustment
- `scripts/lib/prod-release-manifest.py` and pinning harness only if isolated invocation or strict mode validation requires a narrow adjustment

Do not modify promotion/pointer production code or accepted promotion/pointer harnesses.

## Required corrections

### Canonical root and finalized proof

1. Make `root:astro 1770` the single releases-parent contract for finalize, switch, remove and every fixture.
2. Add one reusable finalized-release proof. It must require exact SHA path, real root:astro `0750` root, marker absent, valid root-owned manifest, and a complete no-follow tree audit.
3. `switch-pointer` must call that proof before creating a pointer. Direct helper invocation must reject incomplete, mutable, malformed or unfinalized releases.
4. Idempotent `finalize-release` must run the same complete proof (plus canonical Git binding if retained by the design), not manifest-only validation.

### Descriptor-relative transition

Replace pathname collection/second-pass mutation with a descriptor-relative no-follow algorithm:

- open candidate and child directories with `O_DIRECTORY|O_NOFOLLOW`;
- compare opened descriptor metadata to the directory entry metadata;
- freeze each directory to root:astro and remove astro write permission before enumerating/mutating its children;
- use `dir_fd` and `follow_symlinks=False` for stat/chown/chmod/readlink operations;
- reject special files, unsafe hardlinks, external/dangling symlinks and any entry-set/inode swap;
- perform a complete descriptor-relative post-audit before marker removal and again as finalized proof after marker removal;
- no path-based recursive `os.scandir(dirpath)` that can follow a swapped directory.

Safe partial failure may leave the marker and a root-owned partially frozen tree for manual recovery; it must never report success or remove the marker before the complete pre-removal proof.

### Runtime-readable normalized modes

Use a deterministic finalized mode contract:

- directories `0750`;
- regular files with any executable bit `0750`;
- other regular files `0640`;
- symlinks root:astro, never followed, internal and non-dangling.

The full post-audit must prove these exact modes and ownerships. Manifest files therefore normalize to an allowed root:astro mode accepted by the validator.

### Isolated privileged subprocesses

- Add fixed `/usr/bin/python3.12`; validate its root ownership/type/mode as appropriate.
- Invoke installed manifest validator as `/usr/bin/python3.12 -I -S /usr/local/libexec/solarsage/release-manifest ...` with fixed minimal environment and cwd.
- Invoke `/usr/bin/git` with fixed minimal environment/cwd and exact `-c safe.directory=/opt/solarsage-astro -C /opt/solarsage-astro worktree list --porcelain` (or a stricter NUL-safe equivalent).
- The installed authority entrypoint must run Python isolated from caller environment; update shebang/launcher contract and test it.
- No raw exception/path output; fixed one-line rc78 remains.

## Harness requirements

Add honest named cases and mutation proofs for:

- pointer success on canonical `1770` parent and finalized release;
- pointer rejection of incomplete astro-owned candidate and root-owned tree with invalid manifest/rogue entry;
- remove-pointer on canonical `1770` parent;
- idempotent retry rejection after adding each of: astro-owned/writable file, external symlink, unsafe hardlink, special file, wrong nested mode;
- nested `0600` file and `0700` directory normalize to runtime-readable modes; real-root oracle proves `sudo -u astro test -r/-x` succeeds after finalize;
- full post-audit removal mutation flips the same oracle;
- Git argv includes fixed safe.directory and validator argv includes `/usr/bin/python3.12 -I -S` under a clean environment;
- no hidden dependency on root global Git config or caller `PYTHONPATH`/Git environment;
- exact pre/post substitution counts, execution ledger, two deterministic runs, no production paths/actions.

Retain all existing relevant cases; fix fixtures so pointer and finalize tests share the same canonical parent metadata.

## Verification

Run every command from 160 twice where applicable, plus:

```bash
bash -n scripts/tests/test-prod-release-authority.sh scripts/lib/prod-release-build.sh scripts/tests/test-prod-release-build.sh
python3.12 -I -S -m py_compile scripts/prod-release-authority.py scripts/lib/prod-release-manifest.py
timeout 180 bash scripts/tests/test-prod-release-authority.sh
timeout 180 bash scripts/tests/test-prod-release-build.sh
timeout 180 bash scripts/tests/test-prod-release-pinning.sh
timeout 180 bash scripts/tests/test-prod-release-promotion.sh
timeout 180 bash scripts/tests/test-prod-release-pointer-contract.sh
```

Outputs of each changed focused suite must be byte-identical across two runs. No real runtime/source metadata change, install, sudoers application, service/nginx/database action, commit or push. Stop for independent review.
