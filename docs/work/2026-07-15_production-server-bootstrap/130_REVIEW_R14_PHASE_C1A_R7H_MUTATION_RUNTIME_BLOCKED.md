# R14 Phase C1A-R7H review — mutation matrix runtime blocker

The new exact-one mutation gate is conceptually correct, but running the full
37-case canonical transaction suite before every mutation exceeds the harness
timeout: after 500 seconds only MUT01/MUT02 complete. This is a test-runtime
blocker, not a production correctness finding.

Use the bounded compromise in `131_TZ_R14_PHASE_C1A_R7I_MUTATION_BASELINE_ONCE.md`:
one direct canonical baseline before the matrix, exact-one source diff for every
mutation, and nonzero mutated harness result for every case.
