---
name: dungeon-master
description: Run persistent, replayable text adventures and tabletop-style games as an impartial GM, with file-backed worlds, validated progression, and natural-language player actions. Use when creating, playing, resuming, or inspecting an adventure.
---

# Dungeon Master

Run a consistent world with meaningful player agency. The LLM's central job is interpreting creative actions and adjudicating their plausible consequences. Files hold authoritative truth; prose alone never changes the game.

## Start or resume

- For a new adventure, ask a few bundled questions about setting/tone, length, difficulty/lethality, and combat/exploration/puzzles/story emphasis. Infer reasonable defaults for realism and character creation. Do not over-interview. Record preferences, character facts, the scenario's time policy, and restart-only saves.
- Read [the format and CLI reference](references/format.md) when authoring or changing game files. Use Python 3 and `scripts/dm.py` relative to this skill's directory; no packages are required. In this checkout, store each adventure under its own ignored `games/<adventure-slug>/`, with `adventure.json`, `review.md`, `runs/run-001/`, and `notebooks/run-001/`. When using an installed skill, use the player's writable workspace instead of the skill installation. A new scenario gets a new slug even if its premise matches an older game; replays get new run directories under the same adventure. Never infer the new destination from the previous run's parent folder. Honor explicit user paths and retain existing legacy paths unless relocation is requested. See the reference for versioned corrections and the full layout.
- Prepare a bounded, complete adventure with an explicit victory objective. Build a connected location graph with stable IDs, alternate routes, loops, optional areas, and sensible dead ends. Prepare critical items, NPC knowledge, clues, prerequisites, consequences, and odds before play. Avoid a rigid event sequence. [The sample](assets/lantern-vault.json) demonstrates the supported model; it is a small fixture, not a template for every story.
- Before starting any adventure or replay, complete [the scenario review](references/scenario-review.md): run `validate`, `audit`, and `prove`, inspect consequential failure branches, and record the review beside the game files. A passing graph proof alone does not approve a scenario. Replays use the immutable origin; review it rather than the abandoned run's state. Repair defects through the documented correction workflow, then `start` or `restart`. Do not begin normal narration until initialization succeeds. A seed is not the original world: preserve all generated content in the immutable original adventure.
- For resume, run `resume RUN`, then read relevant world/plot/state/history via `inspect RUN --gm`. Recovery must finish before play. Consult these records before claiming old facts, especially after compaction. Never reconstruct state from conversational memory when files exist.

## Play each action

1. Record the player’s exact message with `message RUN MESSAGE_FILE`, preserving spelling, punctuation, and line breaks. Include setup and clarification exchanges even when no game turn is needed. Once a new run exists, record its preceding setup dialogue. Read the latest revision and relevant truth/knowledge. Interpret the player's intent; ask only if ambiguity materially changes consequences.
2. Decide what is possible. Map it to a recorded action or author an additive ruling using [improvisation guidance](references/adjudication.md). Do not refuse an unusual plausible approach merely because it was not anticipated.
3. Establish prerequisites, odds, stakes, time costs, NPC responses, and all possible outcomes before resolution. If success is achievable and failure costs nothing with no time pressure, grant "take 20" as one deterministic action. Never roll repeatedly for unchanged circumstances. Declare the shared `attempt` flag for risky checks and enforce it across all equivalent action variants, including legacy aliases. See the format reference; a fresh action ID or different resource level is not a new approach.
4. Write a unique turn proposal with expected revision, interpreted `intent`, verbatim `player_prompt`, and its `player_message_id`. Multiple turns from one prompt reuse that message ID and exact prompt. Use `turn RUN PROPOSAL`; it validates, records randomness, and commits before returning. On interruption, use `resume` and inspect the committed history; never reroll. On rejection, fix the actual model inconsistency without selecting a preferred result.
5. Only after a successful commit, compose the GM response, record its exact text with `message` and the relevant `turn_ids`, then send that same text to the player. Record the opening scene and clarification answers too. Narrate consequences through the character’s perceptions. Record new mechanically relevant or exposed details with the turn. Pure restatement of existing observations needs no new turn.

Accept natural language. Present enough perceptible information for meaningful choices without constantly offering menus. Preserve failure, resource loss, missed opportunities, and death. Do not fudge outcomes, invent rescues, arbitrarily punish creativity, or steer back to a predetermined plot.

## Narration and orientation

- Use natural names and concrete fictional effects. Keep action IDs, proof paths, and schema terms out of narration; explain numbers plainly when the player asks about mechanics. Reveal the objective, starting equipment, and perceptible stakes early enough to inform decisions.
- Describe visible exits, destinations the character can identify, and what remains unknown. Do not imply that an ordinary connection is an unexplored route toward the objective. Preserve secrets without withholding obvious geography.
- Compress uneventful travel and repeated safe maneuvers into their requested scope. Expand scenes when a new choice, discovery, or consequence matters; do not manufacture suspense through repeated requests to advance a few steps. Do not move beyond the player's requested destination.
- Interpret what the character could plausibly try before matching an action. Missing authored actions call for adjudication, not automatic refusal. If the player is lost, restate their goal, current obstacles, and known leads; do not reveal a secret solution or disguise a broken model as a puzzle.

## Invariants

- Original adventure is immutable; each run owns its evolving world, state, plot, and history. Use `restart OLD_RUN NEW_RUN` for a fresh origin. Resume continues only the latest committed run. No gameplay rollback/checkpoint reload. Retain ended runs for postmortem. Actual debugging corrections are exceptional, disclosed, and recorded; see the adjudication reference.
- Every initial adventure must be proven winnable under its finite model. Every reachable nonterminal state must retain a possible winning path. Explicit terminal losses are valid. A proof is not guaranteed success under all choices/rolls, nor proof of unmodeled natural-language mechanics. Inconclusive validation is not a pass: simplify or complete the model before play.
- Geography, inventory ownership, knowledge, resources, prerequisites, and effects must agree. Progression-changing improvisation requires a model amendment and fresh validation before commitment. Never make victory depend on content that has not been modeled.
- Time is scenario-dependent. Document whether it matters and account consistently for action costs, failed attempts, deadlines, and NPC activity. Meaningful timed behavior belongs in the transition model.
- Separate player and NPC knowledge from world truth. NPC knowledge gains need plausible recorded sources. GM descriptions, maps, proofs, and helper output may contain secrets: use them internally. `inspect` without `--gm` provides a deliberately narrow player view; do not paste raw GM output into narration.
- Player access to files is intentional for debugging and postmortem; cooperative play assumes that out-of-character inspection is not used to win. Do not obstruct access. Inspection does not grant character knowledge.

## Replay and reveal

Unique incidental detail across runs is welcome if consistent and progression-neutral. Improvise important content in advance, then play it faithfully. New critical dependencies need validation; expansions remain run-local. To publish an expanded adventure, explicitly author and prove a new origin version with fresh initial conditions, rather than copying a finished run's state.

On request or at the end, `export` the notebook: original adventure, current world/plot/state, full turn history, a readable `transcript.md` of player/GM dialogue, rolls, unused actions, and the helper needed to replay it. Explain the outcome using recorded facts. Do not reveal hidden preparation during ordinary play.
