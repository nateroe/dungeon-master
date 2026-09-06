"""Behavioral checks: python3 -m unittest discover -s scripts -v"""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import dm

SAMPLE = Path(__file__).resolve().parent.parent / 'assets' / 'lantern-vault.json'


class DungeonMasterTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.run = self.root / 'run'
        self.bundle = dm.read(SAMPLE)
        dm.create_run(SAMPLE, self.run)

    def proposal(self, action='go-hall-study', revision=0, **extra):
        prompt = 'Player says: ' + action
        mid = f'player-{revision+1}'
        dm.record_message(self.run, {'id': mid, 'role': 'player', 'text': prompt,
                                    'kind': 'gameplay', 'source': 'live'})
        return dict(id=f'turn-{revision+1}', expected_revision=revision, action=action,
                    intent=action, player_prompt=prompt, player_message_id=mid, **extra)

    def test_proof_witness_reaches_victory_using_live_engine(self):
        proof = dm.prove(self.bundle)
        self.assertEqual(proof['status'], 'proven')
        for revision, step in enumerate(proof['winning_path']):
            dm.commit(self.run, self.proposal(step['action'], revision))
        self.assertEqual(dm.load_run(self.run)['current']['state']['status'], 'won')
        with self.assertRaisesRegex(ValueError, 'Run ended'):
            dm.commit(self.run, self.proposal(revision=len(proof['winning_path'])))

    def test_key_behind_its_own_door_is_rejected(self):
        b = self.bundle
        b['plot']['actions']['go-hall-study']['requires'] = {'eq': ['door_open', True]}
        b['plot']['actions']['go-gallery-study']['requires'] = {'eq': ['door_open', True]}
        b['plot']['actions']['read-inscription']['requires'] = {'any': []}
        b['plot']['actions']['pick-lock']['requires'] = {'all': [
            {'eq': ['pick_attempted', False]}, {'any': []}]}
        self.assertEqual(dm.prove(b)['status'], 'unwinnable')

    def test_irreversible_softlock_despite_initial_winning_path(self):
        b = self.bundle
        b['plot']['actions']['sabotage'] = {'requires': {'all': []},
            'outcomes': [{'id': 'done', 'weight': 1, 'set': {'key': 'consumed', 'guardian_at': 'dead', 'pick_attempted': True}}],
            'ruling': 'Destroy the routes before opening the door.'}
        proof = dm.prove(b)
        self.assertEqual(proof['status'], 'unwinnable')
        self.assertTrue(proof['trace'])

    def test_inconclusive_is_not_accepted(self):
        self.assertEqual(dm.prove(self.bundle, 1)['status'], 'inconclusive')
        with self.assertRaisesRegex(ValueError, 'inconclusive'):
            dm.create_run(SAMPLE, self.root / 'too-small', 1)
        self.assertFalse((self.root / 'too-small').exists())

    def test_unique_item_and_dangling_edge_rejected(self):
        b = copy.deepcopy(self.bundle)
        b['plot']['variables']['duplicate'] = copy.deepcopy(b['plot']['variables']['key'])
        b['state']['duplicate'] = 'study'
        with self.assertRaisesRegex(ValueError, 'exactly one'):
            dm.validate(b)
        b = copy.deepcopy(self.bundle)
        b['world']['edges'][0]['to'] = 'missing'
        with self.assertRaisesRegex(ValueError, 'Dangling'):
            dm.validate(b)

    def test_live_movement_obeys_edge_source(self):
        with self.assertRaisesRegex(ValueError, 'prerequisites'):
            dm.commit(self.run, self.proposal('go-study-gallery'))
        self.assertEqual(dm.load_run(self.run)['revision'], 0)

    def test_repeat_turn_id_is_idempotent_and_revision_is_enforced(self):
        p = self.proposal()
        first = dm.commit(self.run, p)
        self.assertEqual(first, dm.commit(self.run, p))
        self.assertEqual(len(dm.load_run(self.run)['history']), 1)
        with self.assertRaisesRegex(ValueError, 'reused'):
            dm.commit(self.run, dict(p, intent='changed'))
        with self.assertRaisesRegex(ValueError, 'Stale'):
            dm.commit(self.run, dict(p, id='new'))

    def test_take20_no_roll_and_replay_cleans_state(self):
        dm.commit(self.run, self.proposal())
        event = dm.commit(self.run, self.proposal('search-study', 1))
        self.assertIsNone(event['roll'])
        self.assertEqual(dm.load_run(self.run)['current']['state']['key'], 'inventory')
        origin = self.root / 'origin.json'
        dm.atomic(origin, dm.load_run(self.run)['origin'])
        other = self.root / 'other'
        dm.create_run(origin, other)
        self.assertEqual(dm.load_run(other)['current'], self.bundle)
        self.assertEqual(dm.load_run(other)['history'], [])

    def test_random_pending_recovery_reuses_ticket(self):
        p = self.proposal('pick-lock')
        original = dm.atomic
        def crash_at_save(path, data):
            if Path(path).name == 'run.json':
                raise OSError('simulated crash before snapshot replacement')
            original(path, data)
        with patch.object(dm, 'atomic', side_effect=crash_at_save):
            with self.assertRaises(OSError):
                dm.commit(self.run, p)
        pending = dm.read(self.run / 'pending.json')
        expected = dm.random.Random(pending['ticket']).randrange(1, 5)
        result = dm.commit(self.run, p)
        self.assertEqual(result['roll'], expected)
        self.assertEqual(result['ticket'], pending['ticket'])
        self.assertEqual(len(dm.load_run(self.run)['history']), 1)
        self.assertFalse((self.run / 'pending.json').exists())

    def test_crash_after_snapshot_before_pending_cleanup(self):
        p = self.proposal('pick-lock')
        original = dm.atomic
        def crash_after_save(path, data):
            original(path, data)
            if Path(path).name == 'run.json':
                raise OSError('simulated crash after snapshot replacement')
        with patch.object(dm, 'atomic', side_effect=crash_after_save):
            with self.assertRaises(OSError):
                dm.commit(self.run, p)
        first = dm.load_run(self.run)['history'][0]
        self.assertEqual(first, dm.commit(self.run, p))
        self.assertEqual(len(dm.load_run(self.run)['history']), 1)

    def test_unexpected_solution_and_fact_persist_only_in_run(self):
        amendment = {'reason': 'Traveler uses a plausible newly considered door bypass.',
          'world': {'facts': {'scorch': 'The door is scorched.'}},
          'variables': {'saw_scorch': {'domain': [False, True], 'role': 'knowledge', 'ref': 'scorch', 'owner': 'player'}},
          'values': {'saw_scorch': False},
          'actions': {'burn-door': {'requires': {'eq': ['location', 'hall']},
            'outcomes': [{'id': 'opened', 'weight': 1, 'set': {'door_open': True, 'saw_scorch': True}}],
            'ruling': 'Fixture assumes available fuel and a wooden door; deterministic bypass.'}}}
        dm.commit(self.run, self.proposal('burn-door', amendment=amendment))
        save = dm.load_run(self.run)
        self.assertTrue(save['current']['state']['door_open'])
        self.assertNotIn('scorch', save['origin']['world']['facts'])
        self.assertIn('scorch', dm.player_view(save)['discovered_facts'])
        with self.assertRaisesRegex(ValueError, 'overwrite'):
            dm.amended(save['current'], amendment)

    def test_hidden_knowledge_stays_out_of_player_view(self):
        view = dm.player_view(dm.load_run(self.run))
        self.assertEqual(view['discovered_facts'], {})
        self.assertNotIn('ember', json.dumps(view))
        self.assertNotIn('guardian', json.dumps(view))

    def test_invariant_violating_random_branch_not_silently_pruned(self):
        b = self.bundle
        b['plot']['invariants'] = [{'not': {'eq': ['status', 'lost']}}]
        self.assertEqual(dm.prove(b)['status'], 'invalid')

    def test_unsupported_mechanics_rejected(self):
        self.bundle['plot']['actions']['unlock']['requires'] = {'python': 'True'}
        with self.assertRaisesRegex(ValueError, 'Unsupported'):
            dm.prove(self.bundle)

    def test_export_contains_replay_and_history(self):
        dm.commit(self.run, self.proposal())
        dest = self.root / 'notebook'
        dm.export_run(self.run, dest)
        for name in ['adventure.json', 'run.json', 'world.json', 'plot.json', 'state.json', 'log.md', 'transcript.md', 'dm.py', 'format.md']:
            self.assertTrue((dest / name).exists(), name)
        dm.create_run(dest / 'adventure.json', self.root / 'export-replay')
        self.assertEqual(dm.load_run(self.root / 'export-replay')['current'], self.bundle)
        self.assertEqual(dm.load_run(self.root / 'export-replay')['transcript'], [])

    def test_exact_prompt_required_separately_from_intent(self):
        p = self.proposal()
        p['player_prompt'] = 'A paraphrase'
        with self.assertRaisesRegex(ValueError, 'verbatim'):
            dm.commit(self.run, p)
        del p['player_prompt']
        with self.assertRaisesRegex(ValueError, 'Missing'):
            dm.commit(self.run, p)

    def test_dialogue_preserves_text_and_does_not_advance_game(self):
        text = '  What is that?\n\nKeep my EXACT words!  '
        m = {'id': 'question', 'role': 'player', 'text': text,
             'kind': 'clarification', 'source': 'live'}
        first = dm.record_message(self.run, m)
        self.assertEqual(first, dm.record_message(self.run, m))
        save = dm.load_run(self.run)
        self.assertEqual(save['revision'], 0)
        self.assertEqual(save['current'], self.bundle)
        self.assertEqual(save['transcript'][0]['text'], text)
        self.assertIn(text, dm.render_transcript(save))
        with self.assertRaisesRegex(ValueError, 'reused'):
            dm.record_message(self.run, dict(m, text='Different'))

    def test_one_prompt_can_link_multiple_turns_and_gm_reply(self):
        p = self.proposal()
        dm.commit(self.run, p)
        dm.commit(self.run, dict(p, id='turn-2', expected_revision=1,
                                action='search-study', intent='Search after moving'))
        dm.record_message(self.run, {'id': 'reply', 'role': 'gm', 'text': 'You find the key.',
             'kind': 'gameplay', 'source': 'live', 'turn_ids': ['turn-1', 'turn-2']})
        save = dm.load_run(self.run)
        self.assertEqual(len(save['transcript']), 2)
        self.assertIn('turn-1, turn-2', dm.render_transcript(save))

    def test_legacy_run_can_accept_reconstructed_dialogue(self):
        save = dm.load_run(self.run)
        del save['transcript']
        dm.atomic(self.run / 'run.json', save)
        self.assertIn('No dialogue was recorded', dm.render_transcript(save))
        dm.record_message(self.run, {'id': 'old-opening', 'role': 'gm',
            'text': 'An opening copied from the conversation.', 'kind': 'gameplay', 'source': 'reconstructed'})
        self.assertIn('reconstructed', dm.render_transcript(dm.load_run(self.run)))

    def test_origin_hash_detects_accidental_mutation(self):
        save = dm.load_run(self.run)
        save['origin']['world']['title'] = 'changed'
        dm.atomic(self.run / 'run.json', save)
        with self.assertRaisesRegex(ValueError, 'modified'):
            dm.load_run(self.run)

    def test_shared_attempt_blocks_variants_in_proof_and_live_play(self):
        b = self.bundle
        action = b['plot']['actions']['pick-lock']
        action['outcomes'][1]['set'] = {'pick_attempted': True}
        b['plot']['actions']['pick-with-other-focus'] = copy.deepcopy(action)
        source = self.root / 'variants.json'
        dm.atomic(source, b)
        run = self.root / 'variants'
        dm.create_run(source, run)
        self.run = run
        # Ticket draw 4 chooses the nonfatal failure; do not rely on random luck.
        with patch.object(dm.random, 'Random') as rng:
            rng.return_value.randrange.return_value = 4
            event = dm.commit(run, self.proposal('pick-lock'))
        self.assertTrue(event['changes']['pick_attempted']['after'])
        current = dm.load_run(run)['current']
        self.assertFalse(dm.enabled(current, 'pick-with-other-focus', current['state']))
        with self.assertRaisesRegex(ValueError, 'prerequisites'):
            dm.commit(run, self.proposal('pick-with-other-focus', 1))
        self.assertEqual(dm.prove(current)['status'], 'proven')  # Key/password remain legitimate alternatives.

    def test_attempt_validation_rejects_bypass_and_reset(self):
        for mutation in ('optional-guard', 'missing-effect', 'reset', 'wrong-role'):
            with self.subTest(mutation=mutation):
                b = copy.deepcopy(self.bundle)
                a = b['plot']['actions']['pick-lock']
                if mutation == 'optional-guard':
                    a['requires'] = {'any': [a['requires'], {'all': []}]}
                elif mutation == 'missing-effect':
                    del a['outcomes'][1]['set']['pick_attempted']
                elif mutation == 'reset':
                    b['plot']['actions']['rest'] = {'requires': {'all': []},
                        'outcomes': [{'id': 'rested', 'weight': 1, 'set': {'pick_attempted': False}}],
                        'ruling': 'Attempt-reset exploit.'}
                else:
                    b['plot']['variables']['pick_attempted']['role'] = 'resource'
                with self.assertRaises(ValueError):
                    dm.validate(b)

    def test_no_retry_proof_rejects_nonfatal_failure_without_alternative(self):
        b = self.bundle
        b['plot']['actions']['unlock']['requires'] = {'any': []}
        b['plot']['actions']['read-inscription']['requires'] = {'any': []}
        b['plot']['actions']['pick-lock']['outcomes'][1]['set'] = {'pick_attempted': True}
        proof = dm.prove(b)
        self.assertEqual(proof['status'], 'unwinnable')
        self.assertTrue(proof['state']['pick_attempted'])

    def test_audit_flags_legacy_alias_without_breaking_legacy_reads(self):
        b = self.bundle
        a = copy.deepcopy(b['plot']['actions']['pick-lock'])
        del a['attempt']
        a['requires'] = {'eq': ['location', 'hall']}
        b['plot']['actions']['old-pick-alias'] = a
        dm.validate(b)
        findings = dm.audit(b)['findings']
        self.assertIn(('missing-attempt', 'old-pick-alias'),
                      [(f['code'], f['action']) for f in findings])

    def test_audit_exposes_repeat_purchase_and_resource_reset(self):
        b = self.bundle
        b['plot']['variables']['heat'] = {'role': 'resource', 'domain': [0, 1, 2]}
        b['state']['heat'] = 2
        b['plot']['actions']['buy'] = {'requires': {'all': []},
            'outcomes': [{'id': 'bought', 'weight': 1, 'set': {'pin': 'inventory', 'heat': 1}}],
            'ruling': 'Buying increases heat.'}
        b['plot']['actions']['cool'] = {'requires': {'all': []},
            'outcomes': [{'id': 'cooled', 'weight': 1, 'set': {'heat': 0}}], 'ruling': 'Cool off.'}
        original = copy.deepcopy(b)
        report = dm.audit(b)
        self.assertEqual(b, original)
        codes = {(f['code'], f['action']) for f in report['findings']}
        self.assertIn(('owned-item-acquisition', 'buy'), codes)
        self.assertIn(('resource-direction', 'buy'), codes)
        changes = next(r for r in report['resource_changes'] if r['action'] == 'buy')
        self.assertEqual(set(changes['examples']), {'increase', 'decrease'})

    def test_audit_limit_is_inconclusive_and_sample_has_no_findings(self):
        self.assertEqual(dm.audit(self.bundle, 1)['status'], 'inconclusive')
        report = dm.audit(self.bundle)
        self.assertEqual(report['status'], 'review_required')
        self.assertEqual(report['findings'], [])


if __name__ == '__main__':
    unittest.main()
