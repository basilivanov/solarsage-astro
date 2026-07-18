# R13 B5 implementation guidance — literal blocks and SSH argv

Это addendum к `65_TZ...`, чтобы не зациклиться на generic YAML/shell parsing.

## 1. Не тестировать backslash continuation через shell one-liner

Shell quoting легко превращает реальный `backslash + newline` в characters `\n`. Работать только с body, прочитанным из actual YAML fixture/canonical file, и проверять Python `repr(body)`.

## 2. Literal `run: |` capture

При строке `run: |`:

- запомнить indent key;
- захватить все последующие physical lines с indent строго больше key indent;
- остановиться до первой nonblank line с indent `<= key indent`;
- удалить только exact common block indent;
- сохранить content/comment lines и physical newlines;
- final body должен иметь deterministic string/line list;
- body child lines не должны попадать как YAML sibling keys/steps.

Если generic AST создаёт больше сложности, поддержать только exact canonical subset этих двух workflows. Не требуется общий YAML parser.

## 3. Logical shell lines

Не использовать regex через shell-escaped string. Надёжный algorithm:

```python
logical: list[str] = []
buffer = ""
for raw_line in body.splitlines():
    stripped = raw_line.strip()
    if not stripped or stripped.startswith("#"):
        continue
    if stripped.endswith("\\"):
        buffer += stripped[:-1].rstrip() + " "
        continue
    logical.append(buffer + stripped)
    buffer = ""
if buffer:
    fail("E_SSH_CONTINUATION")
```

SSH/cleanup/configure validators затем требуют expected number of logical commands.

## 4. Correct `shlex`

Default `shlex` может разбить `-T` на `-`, `T`. Использовать:

```python
lexer = shlex.shlex(command, posix=True, punctuation_chars=";&|<>")
lexer.whitespace_split = True
lexer.commenters = ""
argv = list(lexer)
```

Отклонить tokens/operators `;`, `&&`, `&`, `|`, `||`, `<`, `>`, `<<`, `>>`. После этого `-T`, `-i`, `~/.ssh/...` остаются цельными argv.

Raw command отдельно проверяет double quotes вокруг destination/remote arg, потому что `shlex` удаляет quoting.

## 5. Parser self-check before mutation harness

Сначала добиться:

```text
canonical source-readiness -> rc 0
canonical deploy before UserKnownHosts fix -> exact E_SSH_OPTION_SET
canonical deploy after fix -> rc 0
```

Только затем писать mutation matrix. Не подгонять parser под mutation parse errors; semantic mutation должна возвращать ожидаемый symbolic code.

Если текущий parser уже существенно больше необходимого и продолжает давать duplicate env/12 steps, проще заменить его узким indentation parser, чем латать generic state machine.
