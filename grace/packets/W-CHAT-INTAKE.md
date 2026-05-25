---
id: W-CHAT-INTAKE
phase: PHASE-CHAT
kind: spec-only
status: planned
wave: W-CHAT-INTAKE
last_review: 2026-05-25
modules: [M-CHAT-INTAKE]
depends-on: [W-1.1B]
blocks: [W-2.4, W-CHAT-1, W-CHAT-3, W-CHAT-4]
controller-decision-required: false
decision: B
decided-at: 2026-05-25
---

# W-CHAT-INTAKE — AI assistant chat intake (spec-only)

## Purpose

The legacy frontend already ships a working AI-assistant chat. It currently lives
read-only under `legacy/frontend/**` and is **not** scheduled by Phase-2 port
waves. Without this intake packet, the chat domain would be either:

1. silently portforwarded by a Phase-2 worker (violates `INV-CONTRACT-STABLE`,
   `INV-LEGACY-CHAT-DEFERRED`, marker gate, and §8.5 events registry), or
2. silently dropped from the product when legacy/** is eventually retired.

This packet does **not** ship code. It:

- inventories the legacy chat module file-by-file,
- drafts the Pydantic contract that `W-CHAT-1` will land,
- reserves the `chat.*` event namespace in `grace/canon/observability.xml` §8.5
  with `emitted=false` and `owner-wave="W-CHAT-3"`,
- forces a controller Decision (A port-1:1 / B rewrite-on-AI-SDK / C drop).

## Decision required

Choose exactly one. The choice gates `W-2.4` (frontend port, fixture-backed)
and the backend waves `W-CHAT-1`, `W-CHAT-3`, `W-CHAT-4`.

- **Option A — Port 1:1.** Re-implement the legacy chat behaviourally identical
  in the active tree. Backend stub becomes a real provider call; persistence
  moves from `localStorage` to server-side `chat_threads` / `chat_messages`.
  Pros: smallest UX delta, smallest scope. Cons: keeps legacy reducer model and
  zod-shaped types as a porting target instead of a clean Pydantic-first design.
- **Option B — Rewrite on AI SDK + Server Actions.** Drop the legacy hook /
  reducer. Use `streamText` from `ai` with a server route, contract-first
  Pydantic schema, no client-side history reducer.   Pros: matches Option B of
  W-1.1B (Pydantic source of truth) and removes localStorage. Cons: bigger
  `W-2.4` (UI is rewritten under `app/(grace)/chat/**`, not ported);
  marker gate file count grows.
- **Option C — Drop chat from the product.** Leave `legacy/**` inert forever.
  PHASE-CHAT is closed without merging W-CHAT-1..4. `chat.*` events stay
  reserved with `emitted=false` indefinitely.

**Default recommendation: Option B**, because (a) Phase-1 has already chosen
Pydantic as the single source of truth in W-1.1B, (b) localStorage persistence
contradicts `INV-CONTRACT-STABLE` once auth lands in W-1.2 (multi-device
divergence), and (c) AI SDK gives `streamText` + abort + token accounting that
the legacy stub explicitly leaves as TODO. Option A is acceptable if the
controller wants minimum UX delta in the first cut. Option C is acceptable only
if product scope is being reduced.

Note on ownership split: regardless of A vs B, the **frontend port** of chat
(screen, hook, reducer, fixture-backed `lib/api/chat.ts`) is owned by
**`W-2.4`** in `PHASE-2-FRONTEND-PORT`. The **backend** (POST /api/chat/messages,
storage, rate-limit, real streaming, contract regeneration) is owned by
**`W-CHAT-1`** in `PHASE-CHAT`. Observability flip (`chat.*` events emitted=true)
is owned by **`W-CHAT-3`**. There is no separate `W-CHAT-2` wave — that slot
was collapsed into `W-2.4` when `PHASE-2-FRONTEND-PORT` absorbed the legacy
frontend port.

## Allowed write scope (this packet only)

- `grace/packets/W-CHAT-INTAKE.md` (this file).
- `grace/canon/observability.xml` — **only** the §8.5 reserved block for
  `chat.*` events with `emitted=false`. No other section.
- `grace/development-plan.xml` — **only** the PHASE-CHAT block and the
  `INV-LEGACY-CHAT-DEFERRED` drift rule. Already landed alongside this packet.

## Frozen scope

- All of `apps/`, `lib/`, `app/`, `components/`, `packages/contracts/`.
- All of `legacy/**` — read-only inventory only, no edits.
- `grace/requirements.xml`, `grace/technology.xml`, `grace/knowledge-graph.xml`.
- Every other §8.x section of `observability.xml` outside the reserved
  `chat.*` block.

## Must preserve

- `INV-LEGACY-INERT`: legacy/** is not imported by active code.
- `INV-LEGACY-CHAT-DEFERRED`: chat is owned by PHASE-CHAT, not Phase-2.
- `INV-CONTRACT-STABLE`: no public contract shape changes in this packet.
- W-1.6 gate-11: any event listed in §8.5 that is not `emitted=false` must be
  asserted in tests. We add `emitted=false` so gate-11 stays green without
  emissions.

## Inventory of the legacy chat module

Verified via filesystem read on the current archive. Total: 12 files,
~888 LOC.

| Path                                                    | LOC | Role                                                       |
|---------------------------------------------------------|----:|------------------------------------------------------------|
| `legacy/frontend/app/(app)/chat/page.tsx`               |  17 | Route entry. Composes `<ChatScreen>`.                      |
| `legacy/frontend/components/chat/chat-screen.tsx`       | 178 | Main chat view: list, composer, suggested prompts wiring.  |
| `legacy/frontend/components/chat/composer.tsx`          |  91 | Input box, send button, abort.                             |
| `legacy/frontend/components/chat/message-bubble.tsx`    |  42 | Renders one user/assistant message.                        |
| `legacy/frontend/components/chat/chat-empty.tsx`        |  37 | Empty-state with suggested prompts.                        |
| `legacy/frontend/components/chat/suggested-prompts.tsx` |  35 | Static prompt chips.                                       |
| `legacy/frontend/components/chat/context-pill.tsx`      |  19 | Small "context: profile" pill above the chat.              |
| `legacy/frontend/hooks/use-chat.ts`                     | 177 | Side-effects: localStorage hydration/persist, stream, abort. Wraps `chatReducer`. |
| `legacy/frontend/lib/reducers/chat-reducer.ts`          | 148 | Pure reducer. All chat business logic; testable without jsdom. |
| `legacy/frontend/lib/api/chat.ts`                       |  ~80| Facade `sendMessage()` async generator. Switches fixtures vs production by `USE_FIXTURES`. Production branch throws "AI SDK not implemented". |
| `legacy/frontend/lib/api/chat.fixtures.ts`              |  17 | Streaming mock generator for `USE_FIXTURES=true`.           |
| `legacy/frontend/lib/contracts/chat.ts`                 |  ~50| Zod: `ChatRoleSchema`, `ChatMessageSchema`, `ChatHistorySchema`, `ChatContextSchema` (depends on `ProfileSchema`). |
| `legacy/frontend/lib/mocks/chat.ts`                     |  84 | Fixture history + suggested prompts.                       |
| `legacy/frontend/lib/chat.ts`                           |  43 | Re-export shim for `ChatContext`/`ChatMessage` types.       |

Worker filling this packet MUST keep this table in sync with the actual
filesystem (run `wc -l` and update if the legacy archive is regenerated).

### Behavioural notes (read-only)

- **Persistence**: history is stored in `window.localStorage` under
  `STORAGE_KEYS.chat`, hydrated on mount, persisted on every state change after
  hydration. This is incompatible with multi-device sessions from W-1.2 and
  must be replaced by server-side `chat_threads` / `chat_messages` in
  `W-CHAT-1`.
- **Streaming**: `sendMessage` is an `AsyncGenerator<string>`; the hook drives
  it via `AbortController`. Production branch is a stub that throws unless
  `NEXT_PUBLIC_USE_FIXTURES=true`. The TODO comment in the file documents the
  intended `streamText` integration and is the contract `W-CHAT-1` must satisfy.
- **Context**: `ChatContext` carries the user's `Profile`. Today this is read
  from local profile state; after W-1.2 it must come from authenticated
  session.
- **Roles**: only `user` and `assistant`. No `system` / `tool` roles in legacy.
  If Option B is chosen, decide whether to extend roles or keep parity.

## Draft Pydantic contract (target for W-CHAT-1, not landed here)

The intent is to lift the existing zod shape into Pydantic 1:1, then let
`packages/contracts` regenerate the TS types so the active tree never imports
zod directly (matches W-1.1B Option B).

```python
# apps/api/app/contracts/chat.py  — DRAFT, NOT TO BE WRITTEN BY THIS PACKET
from typing import Literal
from pydantic import BaseModel, Field, PositiveInt

ChatRole = Literal["user", "assistant"]

class ChatMessage(BaseModel):
    id: str = Field(min_length=1)
    role: ChatRole
    content: str
    created_at: PositiveInt  # unix ms, mirrors legacy createdAt

class ChatThread(BaseModel):
    id: str = Field(min_length=1)
    user_id: str
    created_at: PositiveInt
    title: str | None = None

class ChatContext(BaseModel):
    profile_id: str  # was full Profile in legacy; reduce to id, fetch server-side

class ChatSendRequest(BaseModel):
    thread_id: str | None = None  # None => create new thread
    message: str = Field(min_length=1, max_length=4000)
    context: ChatContext

class ChatSendChunk(BaseModel):
    """One streamed chunk over SSE / chunked transfer."""
    delta: str
    finished: bool = False
    request_id: str  # correlates with W-1.6 logging spine
```

Open questions for the controller (answer in `## Decision`):

1. Streaming transport: SSE vs chunked-transfer vs WebSocket. Default: SSE.
2. Thread model: single implicit thread per user (legacy behaviour) vs explicit
   multi-thread. Default: single implicit, with `thread_id` reserved for
   future multi-thread without contract break.
3. Token / cost accounting: surfaced to client (`chat.tokens.spent` payload) or
   server-only. Default: server-only; client never sees raw token counts.
4. History retention: indefinite vs N most recent. Default: indefinite,
   pagination added in W-CHAT-1 if needed.
5. Moderation / safety: out-of-scope for W-CHAT-1; revisit before public
   launch.

## Reserved business events (for §8.5)

All events below land in `grace/canon/observability.xml` §8.5 with
`emitted=false` and `owner-wave="W-CHAT-3"`. Gate-11 will tolerate
`emitted=false` entries. Any wave that emits one of these before W-CHAT-3
merges fails gate-11.

| Event                  | Owner    | Payload (draft)                                    | Privacy notes                            |
|------------------------|----------|----------------------------------------------------|------------------------------------------|
| `chat.message.sent`    | W-CHAT-3 | `{thread_id, message_id, length, request_id}`      | `content` MUST be redacted by §8.4.      |
| `chat.message.received`| W-CHAT-3 | `{thread_id, message_id, length, request_id}`      | `content` MUST be redacted.              |
| `chat.stream.started`  | W-CHAT-3 | `{thread_id, request_id}`                          | none                                     |
| `chat.stream.finished` | W-CHAT-3 | `{thread_id, request_id, duration_ms, chunk_count}`| none                                     |
| `chat.stream.failed`   | W-CHAT-3 | `{thread_id, request_id, error_class, retriable}`  | `error.message` redacted to class only.  |
| `chat.rate_limited`    | W-CHAT-3 | `{user_id, request_id, limit, window_s}`           | `user_id` redacted per §8.4 user policy. |
| `chat.tokens.spent`    | W-CHAT-3 | `{thread_id, request_id, prompt_tokens, completion_tokens, model}` | model name allowed; counts allowed; never log raw text. |

## Verification (before merging this packet)

1. `legacy/**` is unchanged on disk (`git diff --stat legacy/` is empty).
2. `apps/`, `lib/`, `app/`, `components/`, `packages/contracts/` are unchanged
   (`git diff --stat -- apps lib app components packages/contracts` is empty).
3. `grace/canon/observability.xml` diff contains **only** the reserved
   `chat.*` block in §8.5 with `emitted=false`. No other section is touched.
4. `grace/development-plan.xml` diff contains **only** the PHASE-CHAT block,
   the `INV-LEGACY-CHAT-DEFERRED` rule, and the two `phase-deps` entries.
5. `pnpm lint` and `pnpm contracts:check` are green (no contract drift; no
   active code imports anything from `legacy/**`).
6. Gate-11 (events registry) passes: every reserved `chat.*` entry has
   `emitted=false` and `owner-wave="W-CHAT-3"`.
7. Inventory table above matches `wc -l` of the listed files.
8. Controller has filled `## Decision` with exactly one of A / B / C and a
   one-paragraph rationale.

## Negative tests (specification level)

These are not test files (this is a spec-only packet) but the conditions a
worker MUST be able to demonstrate by inspection:

- Adding any file under `app/(grace)/chat/**` or `components/chat/**` in this
  PR fails the marker gate from W-2.0.
- Adding `chat_threads` / `chat_messages` migration in this PR fails the
  freeze-scope check (those land in W-CHAT-1).
- Setting `emitted=true` on any reserved `chat.*` event in §8.5 fails gate-11
  (no emit sites exist yet).
- Importing `legacy/frontend/lib/api/chat` from active code fails the
  `INV-LEGACY-INERT` check.

## Escalation triggers

Stop and escalate to the controller before continuing if:

- The legacy file inventory diverges from this table by more than two files
  (legacy archive may have been regenerated; intake must be re-run).
- A new `chat.*` event needs to be reserved that is not listed above.
- Decision A is chosen but the legacy reducer relies on browser-only APIs that
  cannot be re-implemented under SSR/streaming server actions without behaviour
  change.
- Decision B is chosen and the AI SDK provider list does not cover the
  streaming + abort + token-accounting requirements at zero-config in the AI
  Gateway (re-scope W-CHAT-1).

## Decision

**Option B — Rewrite on AI SDK + Server Actions.** Decided 2026-05-25.

Rationale: W-1.1B already locked Pydantic as the single source of truth, so
porting the legacy zod reducer 1:1 (Option A) would re-introduce the
zod-shaped client contract that W-1.1B explicitly removed and would force a
second migration once W-1.2 lands server-side auth (localStorage history
diverges across devices). Option B aligns the chat domain with the rest of
Phase-1: contracts originate in `apps/api/app/contracts/chat.py`, TS types
are regenerated by `packages/contracts`, the client owns no business state,
and `streamText` from `ai` covers streaming + abort + token accounting at
zero config in the AI Gateway. Option C is rejected because the product
brief retains the AI assistant. The split between `W-2.4` (UI rebuild under
`app/(grace)/chat/**`, fixture-backed) and `W-CHAT-1` (real backend, contract
regen, storage) is preserved as already encoded in `development-plan.xml`.

Consequences locked by this decision:

- `W-2.4` rebuilds the chat UI from scratch against the Pydantic-derived TS
  types; the legacy reducer/hook are **not** ported. `legacy/**` stays inert.
- `W-CHAT-1` lands the Pydantic contract drafted above, the
  `chat_threads` / `chat_messages` migration, the SSE streaming route
  (transport answer to open question 1), single implicit thread per user
  with reserved `thread_id` (answer to open question 2), and server-only
  token accounting (answer to open question 3).
- `W-CHAT-3` flips the §8.5 `chat.*` events from `emitted=false` to
  `emitted=true` and adds the gate-11 emit-site assertions.
- `W-CHAT-4` owns rate-limit / quota policy on top of the W-CHAT-1 route.
- History retention stays indefinite for the first cut (answer to open
  question 4); pagination is deferred to W-CHAT-1 only if the route needs it.
- Moderation / safety remains out of scope for W-CHAT-1 (answer to open
  question 5); revisit before public launch.

## Evidence

- Inventory table above verified against current `legacy/frontend/**` tree;
  no regeneration since intake was drafted.
- `grace/canon/observability.xml` §8.5 reserved block lands all seven
  `chat.*` events with `emitted=false` and `owner-wave="W-CHAT-3"` (verified
  by gate-11 in the W-2.0 bootstrap run: ALL GREEN).
- `grace/development-plan.xml`: PHASE-CHAT block, `INV-LEGACY-CHAT-DEFERRED`
  rule (split-ownership form), and `phase-deps` `W-CHAT-3 requires W-2.4`
  already landed during the alignment pass.
- No diffs under `apps/`, `lib/`, `app/`, `components/`, `packages/contracts/`
  in this packet (Decision is metadata-only).
- Controller selection recorded above; Option B chosen, A and C rejected.
