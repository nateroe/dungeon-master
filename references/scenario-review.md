# Scenario review before play

Read this before starting a new adventure or replay. Review the exact origin to be played, including inherited scenarios. Repeat affected checks after a progression amendment; review current state when resuming reveals a rules discrepancy. A replay is not permission to silently rewrite its origin.

## Evidence and stopping condition

Run `validate`, `audit`, and `prove` as described in `format.md`. For a saved run, `audit RUN --origin` examines its replay source; `audit RUN` examines current rules and state. Export supplies an `adventure.json` for validating and proving the origin. Audit output is GM information.

Record a short `review.md` beside the adventure/run, identifying the origin hash, commands/results, reviewed warnings, and the conclusions below with concrete action/fact references. Record intentional exceptions and their fictional explanations. This is an authoring note, not another gameplay state store or an approval request to the player. For a replay, copy or reference a still-applicable review only after checking the exact origin and current guidance.

Do not start play with an inconclusive proof/audit, an unresolved rules contradiction, or a winning path that uses actions forbidden in actual play. Repair the model and rerun checks. For an existing immutable origin, use the disclosed correction procedure in `adjudication.md`; retain the old run. Audit findings are prompts for judgment, not automatic defects, and zero findings does not replace this review.

## Review the game, not just its connectivity

- **Failure branches:** For each consequential check, inspect every nonterminal failure. Identify an actual remaining winning approach and how the character can discover it. Check the proof against the no-retry rule, consumed supplies, and NPC knowledge. A corridor loop, a renamed check, or another purchase of identical equipment is not a distinct solution. Explicit terminal losses are valid when the established consequences justify them; don't relabel a softlock merely to pass proof. Recovery is not mandatory after every setback.
- **Equivalent attempts:** Group variants by fictional approach, target, and materially relevant circumstances. All resource-level or naming variants of the same attempt share one flag. Review the entire action set, including old actions left by amendments. Different tools or acquired information can justify a new approach only when their acquisition and relevance are modeled. Run-local additions do not disable old aliases. If those need rewriting, use a corrected version, not an additive wrapper that leaves the proof loophole intact.
- **Resources and trade:** For each resource, document its fictional meaning, increases, decreases, bounds, whether/how recovery works, and a source through which the player learns those rules. Compare reachable before/after values with the ruling: `set: 1` assigns one, it does not add one. Review reacquiring owned items, restocking consumed items, free or repeated transactions, and incidental resource resets. If payment matters, model it; otherwise define abstract trade explicitly rather than inventing balances in narration. Exact-value prerequisites need a reason when a higher resource would normally help.
- **Alternatives and clues:** Identify materially different solutions to major obstacles, not merely different paths to the same mandatory roll. Document optional locations' purposes: information, supplies, safer travel, story, or other intentional value. A dead end is fine; an unadvertised mandatory shopping circuit is not. Ensure clues and prerequisites can be learned before commitment without GM spoilers. Don't force a fixed number of solutions on every small obstacle.
- **Promises versus rules:** Match descriptions of patrols, clocks, surveillance, NPC memory, and equipment to actual consequences. Lack of a global countdown doesn't make a dangerous sprint harmless; safe observation may reveal a guaranteed opportunity only if the established geometry and timing support it. Conversely, don't invent moving hazards solely to create a roll.
- **Distinct adventures:** When asked for a new scenario rather than a replay, compare the proposed obstacles, topology, encounters, and objective structure with recent games. Reusing a fixture's graph with renamed rooms and loot does not satisfy a request for new encounters and a new scenario.

## Helper boundaries

`audit` flags random actions without declared attempt metadata, reachable acquisitions of already-carried items, and actions that can both increase and decrease the same resource. It lists reachable resource-change examples so even a one-direction change can be compared with its prose. These are bounded observations, not semantic conclusions: deliberate replenishment or gambling may be legitimate. Review such cases explicitly.

The helper cannot infer that two differently named exploits are equivalent, that a character knows a route, that a cost is fair, or that a scene is interesting. The GM must check those. Grouped attempt validation and the graph proof must describe the same legal moves used during play.
