# R13 Phase B4 — forced-command wrapper accepted independently

## Status

Phase B4 wrapper harness принят архитектором после последнего R2 edit. Это acceptance только для:

- `infra/production/solarsage-github-deploy`;
- `scripts/tests/test-prod-github-wrapper.sh`.

Production apply/deploy, real target scripts, network, SSH, GitHub API, commit и push не выполнялись.

## Independent execution

Из свежего shell после последнего изменения:

```text
bash -n wrapper + harness                         rc 0
timeout 120 harness, run 1                       rc 0
timeout 120 harness, run 2                       rc 0
product manifest                                 56/56
self-test manifest                               10/10
stdout summary                                   PASS
captured stderr                                  0 bytes / 0 bytes
git diff --check                                 rc 0
remaining /tmp/solarsage-r13-wrapper-test.*      0
```

Fingerprints reviewed:

```text
production wrapper  5c0d014c0d363e787a9eeb59f76b1180907d149a218e8b45c494f7f79e0cb42b
harness             1242382bdd018278bd1bc19f9c9004c899178ef1cce342b7e7466eca965092bf
```

## Contract evidence

- executable-only pre/post target extraction fail-closed до первого valid case;
- deploy/access targets различаются;
- append invocation record + byte-exact `cmp -s` доказывает ровно один target call и exact argv boundaries/order;
- target rc `1`, `42`, `126` сохраняется;
- symmetric hostile matrix для обоих verbs;
- non-hex fixture имеет exact length 40 и не совпадает с lowercase-hex regex;
- literal backticks, `$()`, `|`, `&&`, CR/LF/tab/edge spaces и arbitrary commands дают rc 126 без target call;
- stdout/stderr contract byte-exact, raw command/SHA/sentinel rejected;
- sentinel payload не выполняется;
- exact product/self-test ID manifests и duplicate guards;
- cleanup trap покрывает `EXIT INT TERM HUP`.

External sandbox mutation audit дополнительно подтвердил, что harness краснеет при double target invocation, executable target path substitution, raw command leak, backtick acceptance и `&&` acceptance. Последний false-green 41-byte nonhex исправлен и независимо измерен.

`66_HANDOFF_R13_PHASE_B4_WRAPPER_CONTRACT.md` остаётся историческим coder handoff старой версии (48+9) и не является acceptance evidence. Канонический результат — этот документ.
