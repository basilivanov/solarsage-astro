# R14 Phase C1A-R7H — final marker positions and mutation gate

## Scope

Read review 128. Modify only test harnesses; preserve production code. No
production/C1B/C2/commit/push.

## Exact marker edits

Use unique multi-line snippets, not broad comments:

### SIG02

In the transaction profile loop, locate the unique sequence:

```text
os.fsync(fd)
os.close(fd)
```

Insert marker/pause after `os.close(fd)` for the first profile only. The marker
must be after the first profile's write, fchown, chmod, fsync and close.

### SIG05

Locate the unique post-switch sequence:

```text
ngfd = os.open(gen_name, ...)
for fname, fdata in profiles_data.items():
```

Insert marker/pause between the `ngfd` open and the first `vfd = os.open`/read.
Do not pause at or after `os.close(ngfd)`.

Add a source assertion that each insertion snippet is found exactly once and
that the generated copy compiles without warnings.

## Mutation exact-one gate

Before each mutation:

1. Run the unmodified canonical transaction harness directly and require rc 0.
2. Copy the tool and apply the edit with an exact old-snippet count of one.
3. Assert the unified diff has exactly one removed and one added source line.
4. Run the mutated harness in the private sandbox and require nonzero.

If count is zero or greater than one, fail the mutation suite. Keep the existing
repository-root lock snapshot and sandbox cwd.

## Signal postconditions to retain

Keep the existing no-artifact, generation metadata, check/retry and child-reap
assertions. On marker timeout kill/reap and fail with the sandbox path.

## Final direct handoff

Run transaction harness twice and mutation harness directly (no outer timeout,
grep, tail or PIPESTATUS), then loader/profiles/B6/offsite/fingerprint/diff.
Include marker-position and exact-one outputs. Stop after handoff.
