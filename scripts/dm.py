#!/usr/bin/env python3
"""Dungeon Master: finite progression checking and recoverable local runs (stdlib)."""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import random
import secrets
import sys
import tempfile
from collections import deque
from contextlib import contextmanager

VERSION = 1


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False)


def require(test, message):
    if not test:
        raise ValueError(message)


def keys(obj, allowed, required=()):
    require(isinstance(obj, dict), 'Expected an object')
    require(set(obj) <= set(allowed), f'Unsupported fields: {set(obj) - set(allowed)}')
    require(set(required) <= set(obj), f'Missing fields: {set(required) - set(obj)}')


def read(path):
    return json.loads(Path(path).read_text())


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def atomic(path, value):
    path = Path(path)
    fd, tmp = tempfile.mkstemp(prefix='.dm-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w') as out:
            json.dump(value, out, indent=2, ensure_ascii=False)
            out.write('\n')
            out.flush()
            os.fsync(out.fileno())
        os.replace(tmp, path)
        # Directory syncing is supported by the intended Linux/Codex environment.
        fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


@contextmanager
def locked(run):
    import fcntl
    with open(Path(run) / '.lock', 'a') as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        yield


def expression(expr, variables):
    require(isinstance(expr, dict) and len(expr) == 1, 'Condition must have one operator')
    op, arg = next(iter(expr.items()))
    if op in ('all', 'any'):
        require(isinstance(arg, list), 'all/any require a list')
        for part in arg:
            expression(part, variables)
    elif op == 'not':
        expression(arg, variables)
    elif op == 'eq':
        require(isinstance(arg, list) and len(arg) == 2, 'eq requires [variable, value]')
        name, value = arg
        require(name in variables, f'Unknown variable {name}')
        require(canonical(value) in [canonical(x) for x in variables[name]['domain']],
                f'Value outside domain for {name}')
    else:
        raise ValueError(f'Unsupported condition operator {op}')


def holds(expr, state):
    op, arg = next(iter(expr.items()))
    if op == 'all':
        return all(holds(x, state) for x in arg)
    if op == 'any':
        return any(holds(x, state) for x in arg)
    if op == 'not':
        return not holds(arg, state)
    return canonical(state[arg[0]]) == canonical(arg[1])


def assignments(values, variables, complete=False):
    require(isinstance(values, dict), 'State/effects must be an object')
    if complete:
        require(set(values) == set(variables), 'State must contain exactly all declared variables')
    for name, value in values.items():
        require(name in variables, f'Unknown variable {name}')
        require(canonical(value) in [canonical(x) for x in variables[name]['domain']],
                f'Value outside domain for {name}')


def requires_value(expr, name, value):
    """Conservative structural check: equality must be an unconditional conjunct."""
    return expr == {'eq': [name, value]} or (
        'all' in expr and any(requires_value(p, name, value) for p in expr['all']))


def validate(bundle):
    keys(bundle, ['schema_version', 'world', 'plot', 'state'],
         ['schema_version', 'world', 'plot', 'state'])
    require(bundle['schema_version'] == VERSION, 'Unsupported schema version')
    world, plot, state = bundle['world'], bundle['plot'], bundle['state']
    keys(world, ['title', 'preferences', 'locations', 'edges', 'items', 'npcs', 'facts', 'notes'],
         ['title', 'preferences', 'locations', 'edges', 'items', 'npcs', 'facts'])
    for group in ('locations', 'items', 'npcs', 'facts'):
        require(isinstance(world[group], dict), f'{group} must map IDs to descriptions')
        require(all(isinstance(k, str) and k and isinstance(v, str) for k, v in world[group].items()),
                f'{group} requires nonempty IDs and text descriptions')
    require(bool(world['locations']), 'Need locations')
    reserved = {'inventory', 'consumed', 'destroyed', 'absent', 'dead'}
    require(not (set(world['locations']) & reserved) and
            all(not name.startswith('npc:') for name in world['locations']),
            'Location ID collides with a reserved ownership/status value')
    require('player' not in world['npcs'], 'NPC ID player is reserved for character knowledge')
    keys(plot, ['variables', 'actions', 'invariants', 'time_policy', 'assumptions'],
         ['variables', 'actions', 'invariants', 'time_policy', 'assumptions'])
    require(isinstance(plot['assumptions'], list) and bool(plot['assumptions']), 'Document proof assumptions')
    keys(plot['time_policy'], ['mode', 'rule'], ['mode', 'rule'])
    require(plot['time_policy']['mode'] in ('none', 'explicit'), 'Time mode must be none or explicit')
    require(bool(plot['time_policy']['rule']), 'Document time policy')
    variables = plot['variables']
    require(isinstance(variables, dict), 'variables must be an object')
    require('location' in variables and 'status' in variables, 'Need location and status variables')
    require(set(variables['location']['domain']) == set(world['locations']), 'Location domain must match map')
    require(variables['status']['domain'] == ['playing', 'won', 'lost'], 'Invalid status domain')
    item_owners, npc_locations = set(), set()
    for name, var in variables.items():
        keys(var, ['domain', 'role', 'ref', 'owner'], ['domain', 'role'])
        domain = var['domain']
        require(isinstance(domain, list) and bool(domain), f'Empty domain {name}')
        require(all(x is None or type(x) in (str, int, bool) for x in domain), 'Domains use scalar strings, ints, bools, null')
        require(len(set(map(canonical, domain))) == len(domain), f'Duplicate domain value {name}')
        role = var['role']
        require(role in ('location', 'status', 'item', 'npc_location', 'knowledge', 'flag', 'resource'), 'Unknown variable role')
        if role == 'location':
            require(name == 'location', 'Only location may use location role')
        if role == 'status':
            require(name == 'status', 'Only status may use status role')
        if role == 'item':
            ref = var.get('ref')
            require(ref in world['items'] and ref not in item_owners, 'Item needs exactly one ownership variable')
            item_owners.add(ref)
            places = set(world['locations']) | {'inventory', 'consumed', 'destroyed'} | {'npc:' + n for n in world['npcs']}
            require(set(domain) <= places, f'Invalid item location {name}')
        if role == 'npc_location':
            ref = var.get('ref')
            require(ref in world['npcs'] and ref not in npc_locations, 'NPC needs one location variable')
            npc_locations.add(ref)
            require(set(domain) <= set(world['locations']) | {'absent', 'dead'}, 'Invalid NPC location')
        if role == 'knowledge':
            require(var.get('ref') in world['facts'], 'Unknown knowledge fact')
            require(var.get('owner') in ['player'] + list(world['npcs']), 'Unknown knowledge owner')
            require(domain == [False, True], 'Knowledge uses [false, true]')
        if role == 'resource':
            require(all(type(x) is int and x >= 0 for x in domain), 'Resources use nonnegative integers')
    require(variables['location']['role'] == 'location' and variables['status']['role'] == 'status', 'Wrong core roles')
    require(item_owners == set(world['items']), 'Missing item ownership variable')
    require(npc_locations == set(world['npcs']), 'Missing NPC location variable')
    assignments(state, variables, True)
    for expr in plot['invariants']:
        expression(expr, variables)
        require(holds(expr, state), 'State violates an invariant')
    actions = plot['actions']
    require(isinstance(actions, dict), 'actions must be an object')
    for aid, action in actions.items():
        keys(action, ['requires', 'outcomes', 'ruling', 'attempt'], ['requires', 'outcomes', 'ruling'])
        require(isinstance(aid, str) and aid and bool(action['ruling']), 'Action needs ID and ruling/stakes')
        expression(action['requires'], variables)
        outcomes = action['outcomes']
        require(isinstance(outcomes, list) and outcomes, 'Action needs outcomes')
        labels = set()
        for outcome in outcomes:
            keys(outcome, ['id', 'weight', 'set'], ['id', 'weight', 'set'])
            require(isinstance(outcome['id'], str) and outcome['id'] not in labels, 'Duplicate/invalid outcome ID')
            labels.add(outcome['id'])
            require(type(outcome['weight']) is int and outcome['weight'] > 0, 'Weights must be positive integers')
            assignments(outcome['set'], variables)
        if 'attempt' in action:
            flag = action['attempt']
            require(isinstance(flag, str) and flag in variables, f'Unknown attempt flag for {aid}')
            require(variables[flag]['role'] == 'flag' and canonical(variables[flag]['domain']) == '[false,true]',
                    f'Attempt {flag} must be a boolean flag')
            require(requires_value(action['requires'], flag, False),
                    f'Attempt {aid} must require {flag}=false as a conjunct')
            require(all(o['set'].get(flag) is True for o in outcomes),
                    f'Every outcome of {aid} must consume attempt {flag}')
    attempt_flags = {a['attempt'] for a in actions.values() if 'attempt' in a}
    for aid, action in actions.items():
        for outcome in action['outcomes']:
            require(not any(outcome['set'].get(flag) is False for flag in attempt_flags),
                    f'Action {aid} cannot reset an attempt flag; model a distinct approach')
    edges = world['edges']
    require(isinstance(edges, list), 'edges must be a list')
    edge_actions = set()
    for edge in edges:
        keys(edge, ['from', 'to', 'action'], ['from', 'to', 'action'])
        require(edge['from'] in world['locations'] and edge['to'] in world['locations'], 'Dangling map connection')
        require(edge['action'] in actions and edge['action'] not in edge_actions, 'Each directed edge needs a distinct action')
        edge_actions.add(edge['action'])
        for outcome in actions[edge['action']]['outcomes']:
            require(outcome['set'].get('location', edge['from']) in (edge['from'], edge['to']), 'Edge has contradictory destination')
        require(any(o['set'].get('location') == edge['to'] for o in actions[edge['action']]['outcomes']), 'Edge never reaches destination')
    for aid, action in actions.items():
        require(aid in edge_actions or all('location' not in o['set'] for o in action['outcomes']),
                f'Location-changing action {aid} needs a map edge')
    # Weak connectivity checks the authored geography; directed and gated reachability is checked below.
    seen = {next(iter(world['locations']))}
    while True:
        new = seen | {e['to'] for e in edges if e['from'] in seen} | {e['from'] for e in edges if e['to'] in seen}
        if new == seen:
            break
        seen = new
    require(seen == set(world['locations']), 'Disconnected geography')
    return bundle


def enabled(bundle, aid, state):
    if state['status'] != 'playing':
        return False
    for edge in bundle['world']['edges']:
        if edge['action'] == aid and state['location'] != edge['from']:
            return False
    return holds(bundle['plot']['actions'][aid]['requires'], state)


def transition(bundle, state, outcome):
    result = dict(state)
    result.update(outcome['set'])
    require(all(holds(x, result) for x in bundle['plot']['invariants']), 'Transition violates invariant')
    return result


def prove(bundle, limit=50000):
    validate(bundle)
    start = bundle['state']
    root = canonical(start)
    states, parents, reverse = {root: start}, {root: None}, {}
    queue, wins = deque([root]), set()
    def trace(key):
        steps = []
        while parents[key] is not None:
            previous, aid, oid = parents[key]
            steps.append({'action': aid, 'outcome': oid})
            key = previous
        return list(reversed(steps))
    while queue:
        key = queue.popleft()
        state = states[key]
        if state['status'] == 'won':
            wins.add(key)
        for aid, action in bundle['plot']['actions'].items():
            if not enabled(bundle, aid, state):
                continue
            for outcome in action['outcomes']:
                try:
                    nxt = transition(bundle, state, outcome)
                except ValueError as exc:
                    return {'status': 'invalid', 'reason': str(exc), 'trace': trace(key) + [{'action': aid, 'outcome': outcome['id']}]}
                dest = canonical(nxt)
                reverse.setdefault(dest, set()).add(key)
                if dest not in states:
                    if len(states) >= limit:
                        return {'status': 'inconclusive', 'reason': 'State search limit reached', 'states': len(states)}
                    states[dest] = nxt
                    parents[dest] = (key, aid, outcome['id'])
                    queue.append(dest)
    good, queue = set(wins), deque(wins)
    while queue:
        for previous in reverse.get(queue.popleft(), ()):
            if previous not in good:
                good.add(previous)
                queue.append(previous)
    bad = next((k for k, s in states.items() if s['status'] == 'playing' and k not in good), None)
    if bad is not None:
        return {'status': 'unwinnable', 'states': len(states), 'state': states[bad], 'trace': trace(bad)}
    if start['status'] == 'lost':
        return {'status': 'terminal_loss', 'states': len(states)}
    return {'status': 'proven', 'states': len(states), 'winning_path': trace(sorted(wins)[0]),
            'assumptions': bundle['plot']['assumptions'],
            'scope': 'All reachable nonterminal states have a possible winning path under the recorded finite model; not guaranteed victory.'}


def checked(bundle, limit):
    proof = prove(bundle, limit)
    require(proof['status'] in ('proven', 'terminal_loss'), f'Progression rejected: {canonical(proof)}')
    return proof


def audit(bundle, limit=50000):
    """GM review evidence, not a proof of narrative quality or semantic equivalence."""
    validate(bundle)
    actions, variables = bundle['plot']['actions'], bundle['plot']['variables']
    findings, resources = {}, {}

    def flag(code, aid, detail, state=None):
        findings.setdefault((code, aid, detail), dict(code=code, action=aid, detail=detail,
                                                      **({'state': state} if state is not None else {})))

    for aid, action in actions.items():
        if len(action['outcomes']) > 1 and 'attempt' not in action:
            flag('missing-attempt', aid, 'Random action has no declared shared attempt flag; review retries and aliases.')

    start = bundle['state']
    seen, queue = {canonical(start)}, deque([start])
    complete = True
    while queue and complete:
        state = queue.popleft()
        for aid, action in actions.items():
            if not enabled(bundle, aid, state):
                continue
            for outcome in action['outcomes']:
                for name, value in outcome['set'].items():
                    role, before = variables[name]['role'], state[name]
                    if role == 'resource' and before != value:
                        direction = 'increase' if value > before else 'decrease'
                        resources.setdefault((aid, name), {}).setdefault(direction, {
                            'outcome': outcome['id'], 'before': before, 'after': value})
                    if role == 'item' and before == value == 'inventory':
                        flag('owned-item-acquisition', aid,
                             f'Can acquire {name} while already carrying it; review repeat purchases and side effects.', state)
                try:
                    nxt = transition(bundle, state, outcome)
                except ValueError as exc:
                    return {'status': 'invalid', 'reason': str(exc), 'action': aid, 'outcome': outcome['id']}
                key = canonical(nxt)
                if key not in seen:
                    if len(seen) >= limit:
                        complete = False
                        break
                    seen.add(key)
                    queue.append(nxt)
            if not complete:
                break
    for (aid, name), directions in resources.items():
        if len(directions) > 1:
            flag('resource-direction', aid,
                 f'{name} can both increase and decrease under this action; check fixed assignments against its ruling.')
    return {'status': 'review_required' if complete else 'inconclusive',
            'states': len(seen), 'findings': list(findings.values()),
            'resource_changes': [dict(action=aid, resource=name, examples=directions)
                                 for (aid, name), directions in resources.items()],
            'scope': 'Reachable-state audit. Findings need GM review; absence of findings is not approval. Run prove separately.'}


def create_run(source, destination, limit=50000):
    origin = validate(read(source))
    require(origin['state']['status'] == 'playing', 'Original adventure must start in play')
    proof = checked(origin, limit)
    path = Path(destination)
    path.mkdir(parents=True, exist_ok=False)
    save = {'engine_version': VERSION, 'origin_hash': digest(origin), 'origin': origin,
            'revision': 0, 'current': copy.deepcopy(origin), 'history': [], 'transcript': [], 'initial_proof': proof}
    atomic(path / 'run.json', save)
    return {'revision': 0, 'run': str(path), 'proof': proof['status']}


def load_run(path):
    save = read(Path(path) / 'run.json')
    require(save['engine_version'] == VERSION, 'Unsupported engine version')
    require(digest(save['origin']) == save['origin_hash'], 'Original adventure was modified')
    require(save['revision'] == len(save['history']), 'Revision/history mismatch')
    return save


def amended(bundle, amendment):
    result = copy.deepcopy(bundle)
    if not amendment:
        return result
    keys(amendment, ['reason', 'world', 'variables', 'actions', 'values'], ['reason'])
    require(bool(amendment['reason']), 'Amendment needs a reason')
    # Additive only: existing truth and rules cannot be silently rewritten.
    for group, additions in amendment.get('world', {}).items():
        require(group in ('locations', 'edges', 'items', 'npcs', 'facts'), 'Unsupported world amendment')
        if group == 'edges':
            result['world']['edges'].extend(additions)
        else:
            require(not (set(additions) & set(result['world'][group])), 'Cannot overwrite established world facts')
            result['world'][group].update(additions)
    # Location domain expansion follows explicitly added locations.
    result['plot']['variables']['location']['domain'] = list(result['world']['locations'])
    for group in ('variables', 'actions'):
        additions = amendment.get(group, {})
        require(not (set(additions) & set(result['plot'][group])), 'Cannot overwrite established rules')
        result['plot'][group].update(additions)
    require(set(amendment.get('values', {})) == set(amendment.get('variables', {})), 'Supply initial values for exactly the added variables')
    result['state'].update(amendment.get('values', {}))
    return validate(result)


def prepare(save, proposal, limit):
    keys(proposal, ['id', 'expected_revision', 'action', 'intent', 'player_prompt',
                   'player_message_id', 'amendment', 'notes'],
         ['id', 'expected_revision', 'action', 'intent', 'player_prompt', 'player_message_id'])
    message = next((m for m in save.get('transcript', [])
                    if m['id'] == proposal['player_message_id']), None)
    require(message is not None and message['role'] == 'player', 'Record the player message before its turn')
    require(proposal['player_prompt'] == message['text'], 'player_prompt must match the verbatim player message')
    require(isinstance(proposal['id'], str) and bool(proposal['id']), 'Turn ID required')
    require(proposal['expected_revision'] == save['revision'], 'Stale state revision')
    require(save['current']['state']['status'] == 'playing', 'Run ended; restart from origin')
    bundle = amended(save['current'], proposal.get('amendment'))
    aid = proposal['action']
    require(aid in bundle['plot']['actions'], 'Unknown action')
    require(enabled(bundle, aid, bundle['state']), 'Action prerequisites not met')
    proof = checked(bundle, limit)
    # A new extraordinary action may explicitly end the run. All its branches are still checked.
    return bundle, proof


def finish(run, save, pending):
    proposal = pending['proposal']
    old = next((h for h in save['history'] if h['id'] == proposal['id']), None)
    if old:
        require(old['proposal'] == proposal, 'Turn ID reused with different proposal')
        return old
    require(save['revision'] == pending['base_revision'], 'Pending turn does not match current revision')
    bundle = pending['bundle']
    outcomes = bundle['plot']['actions'][proposal['action']]['outcomes']
    total = sum(o['weight'] for o in outcomes)
    roll = random.Random(pending['ticket']).randrange(1, total + 1) if len(outcomes) > 1 else None
    selected = outcomes[0]
    if roll is not None:
        cursor = roll
        for selected in outcomes:
            cursor -= selected['weight']
            if cursor <= 0:
                break
    before = save['current']['state']
    bundle = copy.deepcopy(bundle)
    bundle['state'] = transition(bundle, bundle['state'], selected)
    event = {'id': proposal['id'], 'revision': save['revision'] + 1, 'proposal': proposal,
             'ruling': bundle['plot']['actions'][proposal['action']]['ruling'],
             'ticket': pending['ticket'], 'roll': roll, 'range': total if roll is not None else None,
             'outcome': selected['id'], 'changes': {k: {'before': before.get(k), 'after': v}
              for k, v in bundle['state'].items() if k not in before or canonical(before[k]) != canonical(v)},
             'proof': pending['proof']}
    save['current'] = bundle
    save['revision'] += 1
    save['history'].append(event)
    atomic(Path(run) / 'run.json', save)
    return event


def recover_locked(run):
    save = load_run(run)
    pending = Path(run) / 'pending.json'
    if pending.exists():
        finish(run, save, read(pending))
        pending.unlink()
        save = load_run(run)
    return save


def commit(run, proposal, limit=50000):
    with locked(run):
        save = recover_locked(run)
        old = next((h for h in save['history'] if h['id'] == proposal.get('id')), None)
        if old:
            require(old['proposal'] == proposal, 'Turn ID reused with different proposal')
            return old
        bundle, proof = prepare(save, proposal, limit)
        # Persist fixed rules and entropy BEFORE resolving; recovery reuses this ticket.
        pending = {'base_revision': save['revision'], 'proposal': proposal, 'bundle': bundle,
                   'proof': proof, 'ticket': secrets.token_hex(32)}
        atomic(Path(run) / 'pending.json', pending)
        event = finish(run, save, pending)
        (Path(run) / 'pending.json').unlink()
        return event


def player_view(save):
    bundle, state = save['current'], save['current']['state']
    variables, world = bundle['plot']['variables'], bundle['world']
    return {'revision': save['revision'], 'location': state['location'], 'status': state['status'],
            'inventory': {v['ref']: world['items'][v['ref']] for k, v in variables.items()
                          if v['role'] == 'item' and state[k] == 'inventory'},
            'discovered_facts': {v['ref']: world['facts'][v['ref']] for k, v in variables.items()
                                 if v['role'] == 'knowledge' and v['owner'] == 'player' and state[k]}}


def record_message(run, message):
    """Append dialogue without advancing game time/state; IDs make retries idempotent."""
    keys(message, ['id', 'role', 'text', 'kind', 'source', 'turn_ids'],
         ['id', 'role', 'text', 'kind', 'source'])
    require(isinstance(message['id'], str) and bool(message['id']), 'Message ID required')
    require(message['role'] in ('player', 'gm'), 'Message role must be player or gm')
    require(isinstance(message['text'], str) and bool(message['text']), 'Verbatim message text required')
    require(message['kind'] in ('setup', 'gameplay', 'clarification', 'commentary'), 'Invalid message kind')
    require(message['source'] in ('live', 'reconstructed'), 'Invalid message provenance')
    require(isinstance(message.get('turn_ids', []), list), 'turn_ids must be a list')
    with locked(run):
        save = recover_locked(run)
        messages = save.setdefault('transcript', [])
        old = next((m for m in messages if m['id'] == message['id']), None)
        if old:
            require({k: v for k, v in old.items() if k != 'recorded_at_revision'} == message,
                    'Message ID reused with different content')
            return old
        valid_turns = {h['id'] for h in save['history']}
        require(all(t in valid_turns for t in message.get('turn_ids', [])), 'Unknown linked turn')
        entry = dict(message, recorded_at_revision=save['revision'])
        messages.append(entry)
        atomic(Path(run) / 'run.json', save)
        return entry


def render_transcript(save):
    lines = ['# Session transcript', '',
             'Player prompts and GM dialogue. Tool output is omitted. Recorded GM text is not proof of delivery.', '']
    messages = save.get('transcript', [])
    if any(m['source'] == 'reconstructed' for m in messages):
        lines += ['Entries marked reconstructed were copied retrospectively from available conversation. '
                  'This backfill covers the main player/GM dialogue; progress commentary is omitted.', '']
    if not messages:
        return '\n'.join(lines + ['No dialogue was recorded for this run. Mechanical history is in log.md.', ''])
    for index, message in enumerate(messages, 1):
        linked = set(message.get('turn_ids', []))
        linked.update(h['id'] for h in save['history']
                      if h['proposal'].get('player_message_id') == message['id'])
        lines += [f"## {index}. {'Player' if message['role'] == 'player' else 'GM'}", '']
        metadata = [message['kind'], message['source']]
        if linked:
            metadata.append('turns: ' + ', '.join(sorted(linked)))
        lines += ['*' + ' · '.join(metadata) + '*', '', message['text'], '']
    return '\n'.join(lines)


def export_run(run, destination):
    with locked(run):
        save = recover_locked(run)
        path = Path(destination)
        path.mkdir(parents=True, exist_ok=False)
        atomic(path / 'adventure.json', save['origin'])
        atomic(path / 'run.json', save)
        (path / 'transcript.md').write_text(render_transcript(save))
        for name in ('world', 'plot', 'state'):
            atomic(path / (name + '.json'), save['current'][name])
        (path / 'log.md').write_text('# Dungeon Master notebook\n\n' + '\n\n'.join(
            '## Turn ' + str(h['revision']) + '\n\n```json\n' + json.dumps(h, indent=2) + '\n```'
            for h in save['history']))
        import shutil
        shutil.copyfile(__file__, path / 'dm.py')
        ref = Path(__file__).resolve().parent.parent / 'references' / 'format.md'
        if ref.exists():
            shutil.copyfile(ref, path / 'format.md')
        return {'export': str(path)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    for cmd in ('validate', 'prove', 'audit'):
        p = sub.add_parser(cmd)
        p.add_argument('adventure')
        p.add_argument('--limit', type=int, default=50000)
        if cmd == 'audit':
            p.add_argument('--origin', action='store_true', help='For a run directory, audit its immutable replay origin')
    p = sub.add_parser('start')
    p.add_argument('adventure'); p.add_argument('run'); p.add_argument('--limit', type=int, default=50000)
    p = sub.add_parser('turn')
    p.add_argument('run'); p.add_argument('proposal'); p.add_argument('--limit', type=int, default=50000)
    p = sub.add_parser('message')
    p.add_argument('run'); p.add_argument('message')
    for cmd in ('resume', 'inspect', 'map'):
        p = sub.add_parser(cmd); p.add_argument('run')
        if cmd == 'inspect':
            p.add_argument('--gm', action='store_true')
    p = sub.add_parser('restart'); p.add_argument('run'); p.add_argument('new_run')
    p = sub.add_parser('export'); p.add_argument('run'); p.add_argument('destination')
    args = parser.parse_args()
    try:
        if args.command == 'validate':
            validate(read(args.adventure)); result = {'status': 'valid'}
        elif args.command == 'prove':
            result = prove(read(args.adventure), args.limit)
        elif args.command == 'audit':
            source = Path(args.adventure)
            if source.is_dir():
                with locked(source):
                    save = recover_locked(source)
                bundle = save['origin' if args.origin else 'current']
            else:
                bundle = read(source)
            result = audit(bundle, args.limit)
        elif args.command == 'start':
            result = create_run(args.adventure, args.run, args.limit)
        elif args.command == 'turn':
            result = commit(args.run, read(args.proposal), args.limit)
        elif args.command == 'message':
            result = record_message(args.run, read(args.message))
        elif args.command == 'export':
            result = export_run(args.run, args.destination)
        else:
            with locked(args.run):
                save = recover_locked(args.run)
            if args.command == 'restart':
                dest = Path(args.new_run)
                # create_run validates before creating the destination; temporary origin is not a new source of truth.
                with tempfile.TemporaryDirectory() as tmp:
                    src = Path(tmp) / 'adventure.json'; atomic(src, save['origin'])
                    result = create_run(src, dest)
            elif args.command == 'map':
                result = {'locations': save['current']['world']['locations'], 'edges': save['current']['world']['edges']}
            elif args.command == 'inspect' and args.gm:
                result = save
            else:
                result = player_view(save)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        if isinstance(result, dict) and result.get('status') in ('unwinnable', 'invalid', 'inconclusive'):
            return 2
        return 0
    except (ValueError, KeyError, TypeError, OSError) as exc:
        print(json.dumps({'error': str(exc)}), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
