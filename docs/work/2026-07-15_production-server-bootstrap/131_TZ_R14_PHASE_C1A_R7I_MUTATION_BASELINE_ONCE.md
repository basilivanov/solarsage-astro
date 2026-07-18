# R14 Phase C1A-R7I — finish mutation matrix within bounded runtime

## Scope

Read review 130. Only test harnesses; no production/C1B/C2/commit/push.

Run the unmodified transaction harness once directly before the mutation loop
and require rc 0. Then, for every mutation:

1. copy the original tool;
2. apply exactly one source replacement and require the unified diff to contain
   exactly one removed and one added source line;
3. compile the copy;
4. run the copied harness in the private sandbox/cwd and require nonzero;
5. verify repository-root `.profile.lock` snapshot unchanged.

Do not repeat the 37-case baseline inside every mutation; the direct baseline
plus exact-one gate keeps the matrix bounded and still prevents false green
mutation edits. Print all 12 true results.

Run final transaction twice directly, then mutation once directly, followed by
the remaining loader/profile/B6/offsite/fingerprint/diff commands. No outer
timeout/filter in final evidence. Stop after handoff.
