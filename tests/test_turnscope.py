from pathlib import Path
import tempfile
import unittest
import wave
from turnscope import analyze, fixture, inspect, segments


class TimingTest(unittest.TestCase):
    def test_fixture_end_to_end(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'call.wav'
            fixture(path)
            report = inspect(path)
        self.assertEqual([(x['event'], x['duration_ms']) for x in report['events']],
                         [('response_gap', 360), ('caller_barge_in', 360),
                          ('response_gap', 200), ('agent_cut_in', 280)])
        self.assertEqual(report['response_p95_ms'], 360)

    def test_agent_continues_through_two_barge_ins(self):
        events = analyze([(10, 20), (30, 40)], [(0, 50)])
        self.assertEqual([e['event'] for e in events], ['caller_barge_in'] * 2)

    def test_gap_belongs_to_last_caller(self):
        events = analyze([(10, 20), (30, 40)], [(50, 60)])
        self.assertEqual([e['event'] for e in events], ['unanswered_turn', 'response_gap'])

    def test_merge_before_duration_filter(self):
        self.assertEqual(segments([(0, 20), (40, 60), (200, 220)], 20, 50), [(0, 60)])

    def test_mono_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'mono.wav'
            with wave.open(str(path), 'wb') as out:
                out.setparams((1, 2, 8000, 0, 'NONE', 'PCM'))
                out.writeframes(bytes(16))
            with self.assertRaisesRegex(ValueError, 'stereo'):
                inspect(path)
