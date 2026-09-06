# Dungeon Master

`SHALL WE PLAY A GAME`

Pick a world. Play a character. Tell your dungeon master what you try.

Dungeon Master turns your coding agent into a game master for text adventures. Ask for sword and sorcery, street-level cyberpunk, survival horror, or something stranger. The agent asks a few setup questions and creates an adventure for you. “Surprise me” works too.

Then play in your own words. Bluff a guard. Pry up the floorboards. Time your attack to the butcher’s next swing. Try something the GM didn't anticipate.

## A moment at the table

An excerpt from an actual session in a buried fortress:

> **Player:** steady with the shield, prepare for and meet his blow, then thrust my sword into his abdomen
>
> **GM:** The falchion crashes against your shield. You hold your footing, but the impact drives pain through your shoulder.
>
> Before he can lift the blade again, you thrust beneath his breastplate.
>
> Your sword sinks into his abdomen. His roar breaks into a choking gasp. You wrench the blade free, and he folds forward, spilling blood across the threshold.

## What will you play?

New adventures are generated for you. These are possible premises, not bundled campaigns:

- **The buried fortress.** An earthquake opens a way into a stronghold swallowed by the earth centuries ago. Goblins butcher their captives in its halls; kobolds have filled the old defenses with traps. Descend with sword and shield, take what you came for, and find your way back into daylight.
- **Drugz, codez, and warez.** You're a hacker trading contraband software, stolen hardware, and things best kept off a shipping manifest. A shadowy client offers a job that puts you between street gangs, federal agents, corporate thugs, and other hackers who might sell you out—or need your help.
- **Dead end of town.** Zombie survival with a crowbar, or anything else you can find. You're alone in a house at the edge of town. The screaming outside stopped an hour ago. The scratching at the door hasn't. Scavenge what you can, pick your fights, and work your way out of the quarantine zone to safety. Shoot 'em in the head, beat 'em, burn 'em—just don't let them corner you.
- **Global Thermonuclear War.** The targets look real. So do the launch orders. Find out who—or what—is on the other end before somebody mistakes the game for a war.

## A world that remembers

The GM prepares the world, its secrets, and the stakes of risky actions before resolving them. Your choices determine what happens. Unexpected plans can become part of the adventure, but they must fit what has already been established.

Game files and helper scripts keep track of places, equipment, discoveries, and consequences. The game checks that a winning path exists under its recorded rules. Whether you survive it is another matter. A failed gamble can hurt; a harmless task that just takes patience doesn't demand twenty tedious retries.

Stop and continue later—even with a different model reading the same files. Or replay the original adventure from the beginning, with fresh rolls and another plan. But there's no rewinding a bad outcome or reloading a checkpoint.

The GM also keeps a transcript you can reread or share. When you're done, ask for the Dungeon Master's notebook to see the rolls, hidden preparation, and what you missed. The files are yours to inspect for debugging and postmortems; they contain spoilers.

## Start playing

Open this repository in Codex with Python 3.9+ available in a local POSIX environment, then paste this prompt. The helpers require no additional Python packages.

```text
Use the skill at ./SKILL.md to start a new adventure.
```

The skill handles setup and game rules. Optionally add a premise or preferences, such as: “Make it a short, tense science-fiction adventure focused on exploration and engineering, with a real risk of death.”

For a later session, name the actual run directory:

```text
Use ./SKILL.md to resume my game in ./games/lantern-vault/runs/run-001.
```

To replay:

```text
Use ./SKILL.md to replay the adventure from ./games/lantern-vault/runs/run-001 from the beginning.
```

## Repository contents

Each adventure belongs in `games/<adventure-name>/`, with its own `adventure.json`, `review.md`, `runs/run-001/`, and exported `notebooks/run-001/`. Replays add runs to the same adventure; a new scenario gets a new adventure directory. Substitute your actual adventure and run names in the prompts above. Older saved paths remain valid.

| Path | Purpose |
| --- | --- |
| [SKILL.md](SKILL.md) | Skill entrypoint and GM workflow. |
| [references/format.md](references/format.md) | Game schema, save layout, helper commands, and amendments. |
| [references/adjudication.md](references/adjudication.md) | Improvisation, time, failure, proof boundaries, and debugging. |
| [references/scenario-review.md](references/scenario-review.md) | Required review of failure paths, resources, alternatives, and player clues before play. |
| [scripts/dm.py](scripts/dm.py) | Validation, progression checking, turns, recovery, replay, and export. |
| [scripts/test_dm.py](scripts/test_dm.py) | Behavioral tests for progression and persistence. |
| [assets/lantern-vault.json](assets/lantern-vault.json) | Small working example adventure; contains spoilers. |
| [dungeon-master-skill-idea.md](dungeon-master-skill-idea.md) | Original concept and agreed design requirements. |

To check the example and run the tests from the repository root:

```bash
python3 scripts/dm.py prove assets/lantern-vault.json
python3 scripts/dm.py audit assets/lantern-vault.json
python3 -m unittest discover -s scripts -v
```

Proof and audit output are GM/debugging material. The audit flags suspicious transitions for review; it does not certify narrative quality or replace the progression proof.

## License

Licensed under the [MIT License](LICENSE). Copyright (c) 2026 Nate Roe.
