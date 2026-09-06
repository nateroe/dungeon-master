# File format and helper usage

## Storage

Use one directory per adventure. In this repository, `SKILL.md`, `scripts/`, `references/`, and `assets/` live at the root; generated games go in the ignored `games/` directory. With an installed skill, create `games/` in the player's writable workspace, not inside the installation:

```text
games/
  buried-fortress/
    adventure.json
    review.md
    runs/
      run-001/run.json
      run-002/run.json
    notebooks/
      run-001/transcript.md
      # Other exported notebook files also live here.
  ghost-stack/
    adventure.json
    review.md
    runs/run-001/run.json
    notebooks/run-001/transcript.md
```

Choose a short descriptive slug for the adventure, not a genre-wide dumping ground. A new cyberpunk scenario must not go inside an earlier fortress adventure's directory merely because it was the last active location. Before creating files, identify the adventure title, origin source (new authoring file or prior run), and destination. Use `games/<slug>/adventure.json` for the authored origin, `runs/run-NNN/` for each attempt, and `notebooks/run-NNN/` for its export. Create parent directories as needed; the helper creates run/export destinations, which must not already exist.

A replay uses `restart games/<slug>/runs/run-001 games/<slug>/runs/run-002`. A new adventure with the same premise gets a distinct slug, not another run of the old origin. For a corrected or expanded published origin, use a distinct version directory such as `games/ghost-stack-v2/`, with a provenance/correction note linking the source and explaining changes; never overwrite the old origin. Keep review notes next to the origin they assess. User-specified paths take precedence. Existing runs at older paths remain usable; do not move them or rewrite embedded history just to adopt this convention.

Python 3.9+ on a local POSIX filesystem, standard library only. One writer per run is enforced with `flock`. Atomic file replacement and fsync protect committed snapshots; network filesystems with weaker locking/rename semantics are outside this guarantee.

An authored `adventure.json` has `schema_version: 1`, `world`, `plot`, and `state`. `start` validates it and copies the full immutable original into `RUN/run.json`, with its SHA-256 hash. This copy is the replay source even if the external authoring file changes. Hashing detects accidental changes, not malicious editing.

`run.json` is the single authoritative snapshot: `origin`, `origin_hash`, `current` (world/plot/state), `revision`, `history`, `transcript`, and `initial_proof`. Separation is logical within one atomically replaced file, avoiding partial multi-file saves. Each history entry includes the exact proposal/amendment, ruling, random ticket and draw, outcome, state changes, and proof. History grows with significant turns; this initial implementation favors inspectability over large-campaign storage efficiency.

`pending.json` is a durable write-ahead record with fixed rules and entropy. Recovery deterministically resolves its ticket, or recognizes an already committed turn. A lock file is coordination metadata. Do not edit these files in normal play or create competing authoritative copies. Exported `world.json`, `plot.json`, `state.json`, and `log.md` are inspection views.

## Model

Read `../assets/lantern-vault.json` for a complete working example.

`world` fields:

- `title`: adventure title; `preferences`: recorded setup/character preferences.
- `locations`, `items`, `npcs`, `facts`: objects mapping stable IDs to text descriptions. Descriptions are GM truth and may contain secrets. Keep references unambiguous; reserve `inventory`, `consumed`, `destroyed`, `absent`, `dead`, and the `npc:` prefix for engine meanings.
- `edges`: directed `{ "from": "hall", "to": "vault", "action": "enter-vault" }` records. Return travel requires another edge/action. Edge actions automatically require the source location. Each has at least one outcome reaching its destination; failure may leave the player at the source. Other actions cannot change player location.
- Optional `notes`: authoring/generation metadata, including generation seed/version if used. Metadata and descriptions are not executable rules.

`plot` fields:

- `variables`: named finite-domain variables, each with `domain` and `role`.
- `actions`: stable IDs mapped to `{requires, outcomes, ruling}`. Ruling documents odds, stakes, meaning of failure, time accounting, and take-20 reasoning if applicable.
  Optional `attempt` names a shared boolean flag for a limited approach; see below. New risky checks must declare it. Legacy actions remain readable but are flagged by `audit` when random and undeclared.
- `invariants`: conditions that must hold initially and after every outcome. A violating outcome makes the proof invalid; it is not silently removed from the search.
- `time_policy`: `{ "mode": "none" | "explicit", "rule": "..." }`.
- `assumptions`: nonempty list documenting what the model includes and excludes. All progression-critical mechanics must be represented; prose assumptions cannot substitute for missing gates or effects.

`state` assigns exactly one allowed value to every variable. Domains contain distinct scalar strings, integers, booleans, or null. Conditions compare JSON types exactly.

| Role | Meaning |
| --- | --- |
| `location` | Required variable named `location`; domain is exactly location IDs. |
| `status` | Required variable named `status`; domain `["playing", "won", "lost"]`. Terminal states have no enabled actions. |
| `item` | One variable per physical item instance; `ref` is an item ID. Domain contains location IDs, `inventory`, `consumed`, `destroyed`, or `npc:ID`. Ownership has one value, preventing duplication. |
| `npc_location` | One variable per NPC; `ref` is its ID; domain contains location IDs, `absent`, or `dead`. |
| `knowledge` | `ref` is a fact ID, `owner` is `player` or an NPC ID; domain `[false, true]`. Record acquisition sources in rulings/turn notes. |
| `resource` | Finite nonnegative integer domain for counts, health, clock ticks, etc. |
| `flag` | Other finite state: quest phase, ability, attempted check, opened door, NPC disposition, event, character status. |

Represent stacks as a resource, or distinct physical instances with distinct item IDs. NPC life/status beyond location, character attributes, quests, environmental states, and events need explicit variables if mechanically relevant. Do not duplicate inventory lists elsewhere.

Conditions have exactly one operator:

```json
{"all": [{"eq": ["location", "hall"]}, {"any": [{"eq": ["key", "inventory"]}, {"eq": ["door_open", true]}]}]}
```

Supported operators: `eq: [variable, literal]`, `all: [conditions]`, `any: [conditions]`, `not: condition`. Empty `all` is true; empty `any` is false. Unknown operators/fields are errors.

Each outcome is `{ "id": "success", "weight": 3, "set": { "door_open": true } }`. Positive integer weights define relative probabilities: weights 3 and 1 mean 75% and 25%. All nonzero outcomes participate in the proof. One outcome is deterministic and draws no random number. Effects are simultaneous assignments; unspecified values persist. No arbitrary expressions or scripts execute inside the model.

### Shared attempts

Declare a variable such as `auth_attempted` with `role: "flag"`, `domain: [false, true]`, initially false. Every action representing the same approach, including variants for different resource levels, declares `"attempt": "auth_attempted"`. Its `requires` must contain `{"eq": ["auth_attempted", false]}` directly or as an unconditional `all` conjunct; every outcome explicitly sets `auth_attempted: true`. The validator rejects missing guards, omitted consumption, and any action resetting a declared attempt flag to false. Proof and live play use these same prerequisites and effects.

```json
{
  "attempt": "auth_attempted",
  "requires": {"all": [
    {"eq": ["location", "relay"]},
    {"eq": ["auth_attempted", false]}
  ]},
  "outcomes": [
    {"id": "opened", "weight": 3, "set": {"authorized": true, "auth_attempted": true}},
    {"id": "rejected", "weight": 1, "set": {"auth_attempted": true}}
  ],
  "ruling": "One exploit attempt; rejection leaves the separately modeled credential route available."
}
```

The example assumes its location, variables, and alternative are separately declared. The helper cannot infer equivalent approaches from prose: the GM must assign the shared flag and audit legacy aliases. A distinct approach uses another flag and concrete changed-circumstance prerequisites; do not restore the old flag through resting, shopping, or renaming. This optional schema addition preserves older saves; it does not silently repair them.

For bounded counters, author separate actions for each relevant current value, with explicit next values and terminal deadline outcomes. Include failed-action costs and NPC responses in those same outcomes. This makes live play and proof use identical rules. If this becomes too large, reduce the scenario's scope; do not leave timing to undocumented narration.

## Commands

Here `DM` stands for the absolute path to this skill's `scripts/dm.py` (substitute it in each command).

```bash
python3 DM validate games/lantern-vault/adventure.json
python3 DM audit games/lantern-vault/adventure.json --limit 50000
python3 DM prove games/lantern-vault/adventure.json --limit 50000
python3 DM start games/lantern-vault/adventure.json games/lantern-vault/runs/run-001
python3 DM inspect games/lantern-vault/runs/run-001 --gm
python3 DM message games/lantern-vault/runs/run-001 player-message.json
python3 DM turn games/lantern-vault/runs/run-001 proposal.json
python3 DM message games/lantern-vault/runs/run-001 gm-message.json
python3 DM resume games/lantern-vault/runs/run-001
python3 DM inspect games/lantern-vault/runs/run-001
python3 DM map games/lantern-vault/runs/run-001
python3 DM restart games/lantern-vault/runs/run-001 games/lantern-vault/runs/run-002
python3 DM audit games/lantern-vault/runs/run-001 --origin
python3 DM audit games/lantern-vault/runs/run-001
python3 DM export games/lantern-vault/runs/run-001 games/lantern-vault/notebooks/run-001
```

Destination directories must not already exist. `resume`, `inspect`, `map`, `restart`, and `export` first recover a pending turn. Map and `--gm` output are secret GM data. Default inspection exposes only location/status, inventory descriptions, and facts explicitly known to the player; the LLM supplies perceptible scenery after checking GM truth. Do not place secret properties in inventory descriptions; represent those as undiscovered facts.

`audit` accepts an adventure JSON file or a run directory (recovering pending work first). For runs, it examines current state by default, or the immutable origin with `--origin`. It reports bounded reachable resource changes, reacquisition of owned items, and undeclared random attempts. A complete audit returns `review_required` even with no findings: semantic review remains the GM's job. It returns exit status 0 for a complete report, 2 for invalid or inconclusive results. See `scenario-review.md` for handling warnings and recording the review. `start`/`restart` enforce structural validation and proof, not this human-language review; the skill requires both before narration.

`validate` checks structural consistency, not winnability. `prove` explores reachable states then traces backward from wins. It returns `proven`, `unwinnable` with a failure trace, `invalid`, `inconclusive` when its limit is exhausted, or `terminal_loss` for an already lost state. A proof includes a possible winning sequence and its assumptions. It does not require all optional content to be visited. `start` requires a playing origin and proof; every turn rechecks the relevant model. Exit status 2 indicates an error or failed/inconclusive proof.

Normal proposal:

```json
{
  "id": "turn-0001",
  "expected_revision": 0,
  "action": "search-hall",
  "intent": "Search the hall carefully.",
  "player_prompt": "i search the hall carefully",
  "player_message_id": "player-0001",
  "notes": "No time pressure or failure cost; take 20."
}
```

The engine checks the expected revision and prerequisites, proves the model, records a random ticket with the proposed rules, resolves, and atomically commits. Reusing the exact proposal ID is idempotent; reusing it for different content is an error. Use a fresh ID for each new significant action. Never rerun a failed action under a new ID to obtain a different roll; model its attempt flag.

## Additive improvisation

A proposal may include `amendment` with a required `reason` and optional:

- `world`: new mappings under `locations`, `items`, `npcs`, `facts`, and/or new `edges`.
- `variables`: new variable definitions, and `values`: exactly their starting values.
- `actions`: new action definitions.

The engine forbids overwriting established facts, variables, or actions. Location-domain expansion follows added locations automatically. Additional NPC/item domains must refer to valid owners/locations; existing domains remain fixed. An expansion that requires broader existing domains needs an explicitly authored new adventure version or a reviewed engine/schema extension, not an undocumented direct edit.

An improvised action may set existing variables. For example, add a burn-door action setting an existing `door_open` flag, with appropriate fuel consumption and danger outcomes. Express observed new details as facts; add a player knowledge variable set to true in the action outcome if discovered. New facts are persistent in that run but never contaminate its origin. The helper checks structure and reachability; the GM must still check semantic contradictions and plausible NPC knowledge.

An exported notebook contains the full original, current sections, history, script, and this reference. Replay with `python3 notebook/dm.py start notebook/adventure.json games/new-run`; inspect/resume an exported snapshot using its directory as RUN. Export is an explicit debugging/reveal action, not a gameplay checkpoint feature.


## Exact dialogue and transcript

`intent` is the GM’s interpretation. `player_prompt` is the player's actual message, verbatim, including typos, punctuation, and line breaks. Never substitute a summary. Before a new turn, record its player message:

```json
{"id":"player-0001","role":"player","text":"i search the hall carefully","kind":"gameplay","source":"live"}
```

Use `message RUN MESSAGE_FILE`. New proposals require both `player_prompt` and `player_message_id`; the helper checks an exact match against that recorded player message. One prompt may produce several turns; reuse its message ID and verbatim text for all of them. Separate messages, even with identical wording, get separate IDs.

After the state commits, compose and record the exact GM response before sending it:

```json
{"id":"gm-0001","role":"gm","text":"You find a key beneath the dust.","kind":"gameplay","source":"live","turn_ids":["turn-0001"]}
```

Kinds are `setup`, `gameplay`, `clarification`, or `commentary`. Capture setup, the opening scene, non-action questions and answers, and final narration; user-facing gameplay commentary may also be recorded. Tool output is omitted from the human transcript. Recording dialogue is atomic and idempotent by message ID, uses the same run lock, and does not advance the gameplay revision or time. GM messages can link committed turn IDs. Player links are derived from proposals automatically; `turn_ids` can also link reconstructed messages to old turns.

Notebook exports include `transcript.md` with Player/GM headings and original message text, separate from the mechanical `log.md`. Canonical exact strings remain in `run.json`. The transcript records authored responses, not proof of display: after interruption, compare saved GM text with conversation before sending it again. Missing replies remain missing until recovered from actual conversation; never invent them from state changes.

Older runs without transcripts remain readable and recoverable, and old committed proposal retries remain valid. New turns must meet the new prompt requirement. To backfill a historical session, copy actual available conversation messages with `source: "reconstructed"`; disclose omitted material or gaps. Preserve old proposals and history, using transcript links rather than rewriting their evidence. A fresh replay has an empty transcript. Exporting or recording dialogue after terminal victory/loss is permitted without changing the result.
