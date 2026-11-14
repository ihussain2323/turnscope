import unittest
from asr_eval import has_phrase, tokens, word_errors


class ASRScoringTest(unittest.TestCase):
    def test_wer_insertion_deletion_substitution(self):
        self.assertEqual(word_errors('freeze the card now'.split(), 'please freeze my card'.split()), 3)
        self.assertEqual(word_errors([], ['extra']), 1)
        self.assertEqual(word_errors(['word'], []), 1)

    def test_phrase_boundaries(self):
        self.assertTrue(has_phrase(tokens('A duplicate charge.'), tokens('duplicate charge')))
        self.assertFalse(has_phrase(tokens('Deduplicate charges'), tokens('duplicate charge')))
