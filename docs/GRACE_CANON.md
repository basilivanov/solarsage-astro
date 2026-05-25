---
id: doc-grace-canon
status: active
wave: none
last_review: 2026-05-25
---
# GRACE-COMMON

## 1. Назначение документа

Этот документ фиксирует portable baseline для strict GRACE как transferable operating model.

Он предназначен для:

- запуска нового проекта под strict GRACE;
- выравнивания нескольких агентов или команды вокруг одного канона;
- передачи другой модели как few-shot baseline;
- подготовки execution без раннего дрейфа в кодинг.

Это не обзорная статья и не набор пожеланий. Это policy-level baseline: что должно быть определено до начала реализации, как должны выглядеть артефакты, как должны работать contracts, logs, verification и multi-agent execution.

## 2. Источники и правило конфликта

Порядок силы источников:

1. Канонический strict-GRACE source: методологический repo/skills/templates, принятый проектом как эталон.
2. Локальный project-level GRACE document, если он явно наследует strict GRACE, а не заменяет его.
3. Supporting materials: авторские посты, notes, internal methodology docs.

Правило конфликта:

- если локальная практика противоречит strict-GRACE канону, канон выигрывает;
- если в каноне нет точного ответа, локальная адаптация допустима, но должна быть явно помечена как `local adaptation`;
- best practice не может ослаблять hard requirement.

## 3. Нормативные слова

- `MUST`: обязательное требование.
- `SHOULD`: сильная рекомендация, которую можно нарушать только осознанно и письменно.
- `MAY`: допустимая опция.

## 4. Что strict GRACE означает на практике

strict GRACE это artifact-driven operating model.

Его базовая последовательность:

1. зафиксировать требования;
2. зафиксировать технологические границы;
3. разложить систему на модули, интерфейсы, data flow и phases;
4. собрать knowledge graph;
5. только после этого писать или менять код;
6. проверять изменения не только тестами, но и trace evidence;
7. вести execution через controller/worker/reviewer loop.

Смысл подхода:

- код становится адресуемым по semantic coordinates;
- архитектурные решения не живут только в голове агента;
- verification опирается на контракты и traces, а не на интуицию;
- multi-agent execution перестаёт быть хаотичным.

## 5. Обязательные артефакты до начала кодинга

Ниже минимальный artifact pack, без которого strict-GRACE execution не считается ready.

### 5.1 `requirements.xml`

MUST содержать:

- system goal;
- use cases с уникальными IDs;
- in-scope / out-of-scope;
- business invariants;
- expected failure handling;
- known defects against intended behavior;
- success criteria.

`requirements.xml` фиксирует intended behavior. Известный дефект должен быть записан как defect against intended behavior, а не как молчаливый scope cut.

### 5.2 `technology.xml`

MUST содержать:

- runtime stack;
- critical dependencies и external systems;
- operational constraints;
- environment assumptions;
- toolchain for verification;
- если принят отдельный business verification mechanism, он тоже должен быть зафиксирован здесь.

### 5.3 `development-plan.xml`

MUST содержать:

- module IDs;
- module responsibilities;
- public interfaces / entrypoints;
- data flows;
- execution phases;
- module dependencies;
- write scopes;
- sequencing rules;
- explicit deferred work.

План должен отвечать не на вопрос "что вообще есть в проекте", а на вопрос "как мы безопасно исполняем изменения".

`development-plan.xml` это execution artifact, а не inventory-файл и не список желаний.

Он должен связывать intended behavior из `requirements.xml` с реальным execution порядком:

- какие phases существуют;
- какие waves входят в phase;
- какие modules входят в wave;
- какие interfaces и data flows эта wave затрагивает;
- что разрешено менять;
- что явно frozen;
- как выглядит gate этой wave.

Нормальный порядок построения `development-plan.xml`:

1. взять use cases и success criteria из `requirements.xml`;
2. взять runtime limits и external boundaries из `technology.xml`;
3. выделить bounded modules;
4. сгруппировать modules в phases;
5. разрезать phases на маленькие waves;
6. для каждой wave заранее зафиксировать write scope, verification и acceptance;
7. явно вынести deferred work, чтобы он не превращался в silent scope drift.

Минимальный skeleton:

```xml
<DevelopmentPlan>
  <Phase id="PHASE-1">
    <Goal>Stabilize bounded execution slice.</Goal>

    <Wave id="WAVE-1">
      <Goal>Prepare stable core before adjacent runtime changes.</Goal>

      <ModuleRef id="M-ENTRY" />
      <ModuleRef id="M-PIPELINE" />

      <AllowedWriteScope>
        <File>path/to/entry.py</File>
        <File>path/to/pipeline.py</File>
        <File>tests/test_pipeline.py</File>
      </AllowedWriteScope>

      <FrozenScope>
        <File>path/to/publisher.py</File>
        <File>infra/docker-compose.yml</File>
      </FrozenScope>

      <Verification>
        <Command>python3 tests/test_pipeline.py</Command>
      </Verification>

      <AcceptanceCriteria>
        <Criterion>Module contracts are in place.</Criterion>
        <Criterion>Wave gate is green.</Criterion>
        <Criterion>Out-of-scope files remain untouched.</Criterion>
      </AcceptanceCriteria>

      <DeferredWork>
        <Item>Publisher repair moves to a later wave.</Item>
      </DeferredWork>
    </Wave>
  </Phase>
</DevelopmentPlan>
```

Хороший `development-plan.xml` позволяет без гадания ответить на три вопроса:

- что делаем сейчас;
- что можно и нельзя трогать;
- по каким evidence и gates wave считается завершенной.

### 5.4 `knowledge-graph.xml`

MUST содержать:

- modules;
- functions/exports, если они важны для reasoning;
- external systems;
- use-case links;
- defect nodes;
- cross-links между требованиями, модулями, flows и verification.

Knowledge graph это рабочий артефакт для reasoning и navigation, а не декоративная диаграмма.

### 5.5 `verification-matrix.md`

MUST содержать:

- mapping use cases -> module gates -> scenario checks -> phase gates;
- deterministic checks;
- trace assertions;
- business verification layer, если он требуется;
- known blockers;
- criteria for pass/fail evidence.

### 5.6 Git snapshot

MUST существовать фиксированная repo boundary и воспроизводимый snapshot состояния перед execution wave.

Если нет репозитория или неясна граница коммитов, strict-GRACE execution будет неполным.

## 6. Уникальные IDs и semantic coordinates

Каждый артефакт должен иметь стабильные coordinates.

MUST:

- module IDs: `M-...`
- phase IDs: `PHASE-...`
- use case IDs: `UC-...`
- scenario IDs: `SCN-...`
- verification IDs: `VM-...`
- defect IDs: `DEFECT-...`

Semantic coordinates нужны для:

- точной навигации;
- trace-based verification;
- failure packets;
- safe multi-agent handoff;
- sparse-attention-friendly execution.

### 6.1 Graph layers

В зависимости от сложности проекта graph layer MUST включать столько слоёв, сколько нужно для безопасного reasoning:

- module graph;
- export/function graph;
- business-flow graph;
- data-flow graph;
- critical call-path sketch.

Hard requirement: хотя бы module graph и business/data-flow representation.

Best practice: добавлять export/function graph и critical call-path sketch для orchestration-heavy или legacy-heavy slices.

## 7. Contracts, maps, summaries и semantic blocks

strict GRACE требует, чтобы код был не просто "читаемым", а формально адресуемым.

### 7.1 Module contract

Каждый модуль, который входит в active slice или write scope, SHOULD иметь module contract.

Module contract фиксирует:

- purpose;
- ownership boundary;
- inputs;
- outputs;
- dependencies;
- side effects;
- invariants;
- failure policy;
- non-goals.

Пример шаблона:

```text
START_MODULE_CONTRACT: M-EXAMPLE
purpose: <what this module exists to do>
owns:
  - <owned file or unit>
inputs:
  - <input>
outputs:
  - <output>
dependencies:
  - <module or external system>
side_effects:
  - <effect>
invariants:
  - <must remain true>
failure_policy:
  - <how failures are surfaced or contained>
non_goals:
  - <what this module must not try to do>
END_MODULE_CONTRACT: M-EXAMPLE
```

### 7.2 Module map

Каждый модуль в active slice SHOULD иметь module map.

Module map фиксирует:

- public entrypoints;
- queues/interfaces/topics/endpoints, если они есть;
- owned tests;
- adjacent modules.

### 7.3 Change summary

Каждый meaningful change packet SHOULD оставлять compact change summary:

- reason;
- scope;
- verification commands;
- open risks.

Это не changelog для истории проекта, а локальный summary для reviewer и следующего агента.

### 7.4 Function contract

Функции, которые:

- экспортируются наружу;
- являются orchestration entrypoints;
- имеют сильные side effects;
- участвуют в active verification path,

SHOULD иметь function contract.

Он фиксирует:

- purpose;
- inputs;
- returns;
- side effects;
- emitted logs;
- error behavior.

### 7.5 Semantic blocks

Крупные или критичные участки функции SHOULD быть размечены paired blocks:

- `START_BLOCK: <NAME>`
- `END_BLOCK: <NAME>`

Правило naming:

- имя блока описывает `WHAT`, а не `HOW`;
- блок должен быть устойчивой semantic unit;
- блок должен быть достаточно мал для targeted reasoning.

### 7.6 Size guardrails

Strict repo обычно жёстко подтверждает granular blocks, но не всегда задаёт глобальные пределы функции и файла.

Поэтому:

- hard requirement: oversized semantic units MUST быть декомпозированы;
- best practice: блоки держать компактными и адресуемыми;
- local adaptation option: можно принять явные guardrails по размеру функции/файла, если проект работает с long-context agents и legacy-heavy codebase.

Если такие guardrails приняты локально, они должны быть явно записаны как `local strict adaptation`, а не выдаваться за универсальный hard canon.

## 8. Structured logs и log-driven development

strict GRACE считает логи не побочным продуктом, а verification evidence.

### 8.1 Обязательный log envelope

Для critical path logs MUST быть structured enough to answer:

- какой модуль;
- какая функция;
- какой semantic block;
- какое событие произошло;
- какой результат;
- какой trace/scenario/use case это обслуживает.

Минимальный envelope:

```json
{
  "module": "M-EXAMPLE",
  "fn": "function_name",
  "block": "BLOCK_NAME",
  "event": "descriptive_event_name",
  "result": "ok|fail|retry|skip",
  "trace_id": "TRACE-...",
  "scenario_id": "SCN-...",
  "timestamp": "ISO-8601"
}
```

### 8.2 Где structured logs обязательны

MUST логировать:

- external calls;
- queue or task handoff;
- retries;
- branching decisions;
- failure conversion;
- completion of major business steps.

### 8.3 Что такое log-driven development

Log-driven development в strict GRACE означает:

- важные transitions проектируются вместе с logs;
- traces используются как first-class evidence;
- failure packet строится на реальных логах и контрактах;
- reviewer может восстановить business path без гадания по коду.

### 8.4 Business verification layer

Для orchestration-heavy flows SHOULD существовать отдельный business verification layer.

Его роль:

- исполнять сценарии уровня business flow;
- собирать structured traces;
- доказывать инварианты на уровне slice, а не только на уровне функции.

Канонический механизм может быть разным:

- internal CLI;
- scenario runner;
- другой thin execution harness.

Если проект выбирает конкретный механизм, это должно быть оформлено в `technology.xml`, `development-plan.xml` и `verification-matrix.md`.

## 9. Verification: deterministic asserts, trace assertions, gates

### 9.1 Общий принцип

Verification в strict GRACE строится сверху вниз:

1. contract-level expectations;
2. deterministic asserts;
3. trace assertions;
4. module gates;
5. wave gates;
6. phase gates.

### 9.2 Deterministic asserts

MUST быть первой линией проверки там, где результат можно выразить точно.

Это включает:

- return values;
- state changes;
- artifact creation;
- payload shape;
- error classification.

### 9.3 Trace assertions

MUST использоваться там, где business path важнее отдельного return value.

Они проверяют:

- порядок событий;
- факт прохождения через обязательные blocks;
- retry/failure semantics;
- presence of evidence for business invariants.

### 9.4 Module gate

Каждый модуль active slice SHOULD иметь свой module gate.

Module gate отвечает на вопрос:

"Можно ли считать этот модуль безопасным для участия в следующей wave?"

### 9.5 Wave gate

Wave gate подтверждает, что весь пакет текущей волны консистентен:

- scope не расширился;
- нужные module gates зелёные;
- traces и artifacts соответствуют packet;
- out-of-scope areas не задеты.

### 9.6 Phase gate

Phase gate подтверждает, что можно переходить к следующей фазе работ.

Phase gate MUST опираться не на ощущение "вроде работает", а на зафиксированную evidence model.

### 9.7 Failure packet

При провале verification SHOULD формироваться compact failure packet:

- failing scenario or gate;
- first divergent module/function/block;
- observed evidence;
- expected evidence;
- probable next repair scope.

## 10. Controller / Worker / Reviewer operating model

### 10.1 Controller

Controller MUST:

- владеть shared artifacts;
- фиксировать packet scope;
- назначать allowed write scope;
- принимать решение о переходе между waves/phases;
- не делегировать архитектурную правду worker'у.

### 10.2 Worker

Worker SHOULD:

- работать только внутри назначенного scope;
- следовать packet буквально;
- возвращать evidence, а не только "сделано";
- не менять архитектурные assumptions без явного escalation.

### 10.3 Worker запрещено

Worker MUST NOT:

- менять shared XML artifacts без явного разрешения controller;
- расширять write scope молча;
- менять module boundaries без отдельного packet;
- объявлять phase complete по собственной оценке;
- скрывать test/verification failures.

### 10.4 Reviewer

Reviewer MUST:

- проверять соответствие packet и scope;
- искать regressions, contract drift, verification gaps;
- возвращать findings по severity;
- отделять hard failure от acceptable follow-up.

### 10.5 Multi-agent / wave execution

Parallel execution допустим только если:

- write scopes не конфликтуют;
- module boundaries уже определены;
- shared artifacts стабилизированы;
- wave packet описывает merge semantics и gate policy.

Иначе execution SHOULD идти последовательно.

### 10.6 How tasks are set via controller packets

В strict GRACE задача для worker SHOULD ставиться через controller-owned execution packet, а не через свободный текст без границ.

Packet — это bounded execution contract, который выводится из shared artifacts и фиксирует, как именно исполняется одна wave или один repair slice.

Packet MUST опираться на:

- `requirements.xml`
- `technology.xml`
- `development-plan.xml`
- `knowledge-graph.xml`
- `verification-matrix.md`

Нормальная granularity packet:

- одна bounded wave;
- один bounded slice внутри wave;
- один repair packet для конкретного defect или failed gate.

Controller packet SHOULD фиксировать:

- честное текущее состояние;
- phase/wave/module IDs;
- goal packet;
- exact write scope;
- allowed files;
- explicitly frozen / out-of-scope surfaces;
- contracts and invariants that MUST be preserved;
- required verification commands;
- expected evidence and gate conditions;
- escalation rule на случай scope pressure.

Нормальный task-setting flow:

1. controller выбирает phase/wave из `development-plan.xml`;
2. controller вырезает bounded slice;
3. controller пишет packet с allowed write scope и verification;
4. worker исполняет packet буквально;
5. reviewer проверяет packet compliance и gate readiness;
6. controller либо закрывает wave, либо выпускает следующий packet, либо формирует failure packet.

Если worker в ходе выполнения понимает, что текущего scope недостаточно, он MUST не расширять его молча, а вернуть escalation для нового packet или packet update.

### 10.7 Canonical controller packet shape

Для нового execution packet SHOULD использоваться единый shape, а не произвольный prose-only format.

Минимальный controller packet MUST содержать:

- packet title;
- `Phase`, `Wave`, `Modules`;
- goal;
- exact write scope;
- allowed files;
- explicitly frozen / out-of-scope surfaces;
- must-preserve invariants;
- verification commands;
- expected evidence;
- escalation rule.

Recommended template:

```md
# Controller Packet — <slice / wave name>

## IDs
- Phase: PHASE-...
- Wave: WAVE-...
- Modules: M-..., M-...

## Goal
<one bounded business / execution goal>

## Allowed Write Scope
- path/to/file_a.py
- path/to/file_b.py
- tests/test_target.py

## Frozen / Out Of Scope
- path/to/neighbor.py
- frontend/*
- infra/*

## Must Preserve
- <runtime invariant>
- <API / DTO / queue invariant>
- <legacy behavior that must remain untouched>

## Verification
- <command 1>
- <command 2>

## Expected Evidence
- files changed
- commands run
- test results
- sample payload / trace / artifact
- residual risks

## Escalation
If <neighbor scope / schema / frontend / infra> change is required, stop and request a new packet.
```

Reviewer SHOULD считать packet неполным, если в нём отсутствуют `Frozen / Out Of Scope`, `Must Preserve`, `Verification` или `Escalation`.

## 11. Hard requirements, best practices, local adaptations

### 11.1 Hard requirements

- Артефакты должны существовать до кодинга.
- Кодинг без contracts и write scope запрещён.
- Shared architectural truth принадлежит controller.
- Verification должна включать deterministic checks и trace evidence.
- IDs и semantic coordinates должны быть стабильны.
- Defects against intended behavior должны быть зафиксированы явно.

### 11.2 Best practices

- держать packets маленькими и узкими;
- decomposing large functions/modules before risky edits;
- использовать compact semantic blocks;
- вести controller packets и reviewer packets в явной форме;
- строить business verification harness для orchestration-heavy slices;
- выбирать минимально достаточный pilot slice.

### 11.3 Local adaptations

Могут включать:

- размерные guardrails для функции/файла;
- конкретный canonical business verification mechanism;
- формат failure packet;
- дополнительные graph layers;
- специфические log fields.

Любая local adaptation MUST быть:

- явно помечена;
- мотивирована;
- непротиворечива hard requirements.

## 12. How to instantiate this in a new project

### 12.1 Принять канон

Нужно письменно зафиксировать:

- какой strict-GRACE source является каноном;
- какой local GRACE document наследует канон;
- что считается hard requirement, best practice, local adaptation.

### 12.2 Определить pilot slice

Pilot slice SHOULD:

- иметь ясный business outcome;
- иметь чёткий вход и наблюдаемый выход;
- проходить через несколько модулей, но оставаться bounded;
- быть достаточно важным, чтобы оправдать formal verification;
- не быть самым рискованным financial/core-domain path, если есть более безопасный orchestration slice.

### 12.3 Создать artifact pack

Нужно завести:

- `docs/requirements.xml`
- `docs/technology.xml`
- `docs/development-plan.xml`
- `docs/knowledge-graph.xml`
- `docs/verification-matrix.md`

Если нужен business verification harness, его spec SHOULD получить отдельный документ.

### 12.4 Принять обязательные decisions

До execution должны быть решены:

- repo boundary;
- pilot slice boundary;
- canonical IDs;
- write scopes;
- verification mechanism;
- fixture vs live-input policy;
- phase structure;
- escalation policy.

### 12.5 Разметить active slice

Нужно добавить или подготовить:

- module contracts;
- module maps;
- function contracts для critical entrypoints;
- semantic blocks;
- structured logging points.

### 12.6 Подготовить first controller packet

Packet должен зафиксировать:

- `Phase`, `Wave`, `Modules`;
- цель первой волны;
- exact write scope;
- allowed files;
- frozen / out-of-scope surfaces;
- must-preserve invariants;
- in-scope scenarios;
- deferred scenarios;
- fixture/live-input policy;
- required evidence;
- verification commands;
- gate conditions;
- out-of-scope risks;
- handoff format для worker.

## 13. Definition of Ready for execution

Execution READY только если одновременно верно следующее:

- выбран strict-GRACE канон;
- artifact pack существует и непротиворечив;
- pilot slice определён и bounded;
- known defects записаны как defects, а не скрытые scope cuts;
- verification matrix связана с use cases и scenarios;
- write scope первой волны зафиксирован;
- controller packet создан;
- reviewer criteria определены;
- repo boundary и snapshot понятны;
- team/agents знают, кто controller, кто worker, кто reviewer.

Если хотя бы один пункт отсутствует, проект ещё в pre-execution state.

## 14. Few-shot baseline для агентов

Этот документ можно давать агенту как baseline policy перед execution.

Минимальная инструкция агенту:

1. Прими этот document как strict-GRACE baseline.
2. Не начинай кодинг до проверки artifact pack и controller packet.
3. Не меняй scope без explicit controller decision.
4. Возвращай evidence, traces и verification result, а не только summary.
5. Если канон не покрывает конкретный случай, предложи local adaptation и пометь её явно.

## 15. Короткое правило

Сначала артефакты и границы.
Потом адресуемый код.
Потом evidence-driven verification.
Потом переход к следующей волне.
