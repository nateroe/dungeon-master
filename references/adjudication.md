# Adjudication, proof boundaries, and debugging

## Advance improvisation and player agency

Prepare the important dependencies and resolution rules before their content is played. Prefer multiple recorded solutions, including knowledge, items, negotiation, abilities, and environmental changes. The model is an adjudication aid, not a menu restricting player vocabulary.

When the player invents an approach, check established physical facts, available means, NPC knowledge, and downstream consequences. Add an action with documented stakes before rolling. Encode newly settled facts and discoveries alongside its consequences. If the action adds or bypasses a progression dependency, the turn's proof must pass before resolution. Never describe a successful action that has not been committed.

Example: the player burns a locked wooden door. If the door is established as wooden and fuel is available, add an action requiring those facts, with outcomes for opening the door and any plausible damage. Use the existing door-open variable so downstream gates see the result. Do not quietly transform a stone door into wood. Avoid introducing random danger just to punish an effective solution.

Pure flavor can differ between replays. A scratch pattern becomes mechanical the moment it supplies a critical code; establish and validate it as such before relying on it. Keep new details as additional facts rather than rewriting old descriptions.

## Failure, time, and take 20

No repeated roll for the same approach in unchanged circumstances. The action must require an unset attempt flag, and every outcome must set it. Another approach or a genuine change in tools/knowledge may justify a distinct action; changing the phrasing does not.

Declare that flag in each equivalent action's `attempt` field. Focus/health variants share the same flag. Validate the whole set of actions: adding a guarded wrapper does not retire an unguarded original. Attempt flags cannot be reset; model a materially different approach with its own prerequisites and flag. If a legacy rule must be replaced, use the correction procedure below. Review remaining failure paths using `scenario-review.md` before accepting an amendment.

If feasible success has no failure cost or time pressure, grant take 20 with a deterministic outcome. Do not simulate twenty rolls or assume it overcomes impossible tasks. Timed scenes must record time costs and meaningful NPC responses in every applicable action branch; use finite resource/clock states and explicit terminal outcomes. Do not add time pressure to defeat an already established take-20 situation.

## What the proof means

Location connectivity cannot prove progression. The checker explores the state graph of recorded prerequisites and effects, including consumed items, failed checks, mutually exclusive decisions, and every positive-weight outcome. It verifies a possible win from every reachable playing state, while allowing terminal loss.

All progression-critical facts need finite variables. Text descriptions and "assumptions" are not executable. A puzzle with an answer hidden in prose still requires modeled discovery/access conditions. Critical NPC knowledge must gate their informative actions. Environmental timers must be included in transitions. The finite model can prove these encoded mechanics, not the correctness of arbitrary natural-language rulings or the player's ability to solve a riddle.

Review each generated adventure for omitted mechanics before accepting the proof. Do not shrink the state space by deleting legitimate failure branches. Do not label a broken start a terminal loss to pass validation. A legitimate action that destroys the last chance of victory can end a run, but describe the actual loss when appropriate; do not conceal a dead game behind continued play. Preserve danger without contriving terminal losses to avoid fixing authoring defects.

A limit-exhausted search is inconclusive. Reduce the adventure to a smaller complete objective, compress redundant states, or deliberately increase the budget after assessing cost. Each bounded adventure must have its own fully modeled objective; do not claim an ungenerated campaign finale is proven.

## Recovery, correction, and postmortem

For interrupted turns, invoke `resume`, then inspect the last history entry. If the save committed but narration did not, use any recorded GM response or compose one from that committed result, record it, and send it once. The helper cannot prove that text was displayed to a player; consult the latest conversation to avoid repeating it. Recovery never authorizes a different random result.

Ordinary gameplay has no rollback. For an actual authoring/engine bug, stop game progression, explain the discrepancy plainly, preserve the original run, and record the correction rationale plus old/new facts in an external correction record. The additive API intentionally cannot rewrite established rules. For a correction it cannot express, produce a separately labeled corrected adventure/run artifact, retaining provenance and the original for inspection; do not pass it off as a normal replay or silently patch an immutable origin. Validate and prove the corrected model before using it. Follow the user's debugging direction if they choose to continue from a repaired state.

Review postmortems against original placements, unused actions and branches, rolls, amendments, and final state. Files are available to the player by design. Out-of-character inspection does not update character knowledge. Exported snapshots are for debugging; normal play still resumes only the latest run or restarts from origin.
