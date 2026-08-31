"""
Unit tests for FlintParser: Levenshtein/sentence similarity, IDF
auto-weighting and template parsing, run against the real "termy"
NPC dataset (split across dataset_*.json / templates_*.json files).
"""
import glob
import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
for path in (str(ROOT), str(ROOT / "src")):
    if path not in sys.path:
        sys.path.insert(0, path)

from FlintParser import FlintParser
from FlintNPC import load_json

DATASET_DIR = ROOT / "npcs" / "termy" / "dataset"
VOCAB_DIR = DATASET_DIR / "vocabulary"


def build_parser(intents=None):
    templates = []
    if intents is None:
        dataset = []
        for f in glob.glob(os.path.join(DATASET_DIR, "dataset_*.json")):
            dataset.extend(
                load_json(DATASET_DIR, os.path.basename(f))
            )
        for f in glob.glob(os.path.join(DATASET_DIR, "templates_*.json")):
            templates.extend(
                load_json(DATASET_DIR, os.path.basename(f))
            )
        personality = load_json(str(DATASET_DIR), "personality.json")
        intents = [
            b for b in dataset + personality
            if isinstance(b, dict) and "input" in block_has_input(b)
        ] if False else [
            b for b in dataset + personality
            if isinstance(b, dict) and "input" in b
        ]

    return FlintParser(
        "termy",
        load_json(str(VOCAB_DIR), "vocabulary.json"),
        templates,
        load_json(str(VOCAB_DIR), "templates.json"),
        load_json(str(DATASET_DIR), "types.json"),
        "WARNING",
        intents,
    )


class LevenshteinSimilarity(unittest.TestCase):
    EXACT = [
        ("kernel", "kernel", 1.0),
        ("Linux", "linux", 1.0),
    ]
    BOUNDS = [
        ("kubernetes", "kubernetees", "gt", 0.85),
        ("kernel", "banana", "lt", 0.3),
    ]

    def setUp(self):
        self.nlp = build_parser()

    def test_exact_and_case_insensitive(self):
        for a, b, expected in self.EXACT:
            with self.subTest(a=a, b=b):
                sim = self.nlp.levenshtein_similarity(a, b)
                self.assertEqual(sim, expected)

    def test_typo_and_unrelated_bounds(self):
        for a, b, op, bound in self.BOUNDS:
            with self.subTest(a=a, b=b):
                sim = self.nlp.levenshtein_similarity(a, b)
                if op == "gt":
                    self.assertGreater(sim, bound)
                else:
                    self.assertLess(sim, bound)


class SentenceSimilarity(unittest.TestCase):
    def setUp(self):
        self.nlp = build_parser()

    def test_identical_and_reordered_score_one(self):
        s = "what is a zombie process"
        reordered = "process zombie a is what"
        self.assertEqual(self.nlp.sentence_similarity(s, s), 1.0)
        self.assertEqual(self.nlp.sentence_similarity(reordered, s), 1.0)

    def test_missing_words_reduce_score(self):
        full = "what is a zombie process"
        partial = self.nlp.sentence_similarity("what is a", full)
        whole = self.nlp.sentence_similarity(full, full)
        self.assertLess(partial, whole)


class AutoWeights(unittest.TestCase):
    """
    Regression: a candidate's own keyword must outweigh scaffolding
    shared with a sibling intent (e.g. "syscall" vs "zombie process").
    """

    def setUp(self):
        self.intents = [
            {"input": [
                "what is a zombie process in linux",
                "explain zombie process",
            ]},
            {"input": [
                "what is a syscall in linux",
                "explain system calls linux",
            ]},
        ]
        self.nlp = build_parser(self.intents)

    def test_keyword_outweighs_shared_scaffolding(self):
        query = "what is a syscall in linux"
        zombie = self.nlp.sentence_similarity(
            query, "what is a zombie process in linux"
        )
        syscall = self.nlp.sentence_similarity(
            query, "what is a syscall in linux"
        )
        self.assertEqual(syscall, 1.0)
        self.assertLess(zombie, 0.3)

    def test_exclusive_words_outweigh_shared_words(self):
        w = self.nlp.weights
        self.assertLess(w["what"], w["zombie"])
        self.assertLess(w["linux"], w["syscall"])


class ShortIdentifierWeight(unittest.TestCase):
    """
    Regression: a short (<3 char) anchor word must use its own
    computed IDF weight rather than being flattened to a low
    constant, so a rare single-letter identifier (e.g. "c" vs "r"
    as in the programming languages) is still recognized as
    salient instead of discarded.
    """

    def setUp(self):
        self.intents = [
            {"input": [
                "what is the c programming language",
                "explain c language",
            ]},
            {"input": [
                "what is the r programming language",
                "explain r language",
            ]},
        ]
        self.nlp = build_parser(self.intents)

    def test_rare_short_identifier_outweighs_shared_scaffolding(self):
        query = "what is the c programming language"
        c_score = self.nlp.sentence_similarity(
            query, "what is the c programming language"
        )
        r_score = self.nlp.sentence_similarity(
            query, "what is the r programming language"
        )
        self.assertEqual(c_score, 1.0)
        self.assertLess(r_score, 0.5)
        self.assertGreater(self.nlp.weights["c"], self.nlp.weights["what"])


class TextSanitization(unittest.TestCase):
    def setUp(self):
        self.nlp = build_parser()
        self.vocabulary = load_json(str(VOCAB_DIR), "vocabulary.json")

    def test_strip_and_count_removes_and_counts(self):
        cleaned, removed = self.nlp.strip_and_count(
            "please clean the damn logs", ["damn"]
        )
        self.assertEqual(removed, 1)
        self.assertNotIn("damn", cleaned)

    def test_strip_and_sentiment_tracks_thanking_words(self):
        sentiment = {k: 0 for k in [
            "expletives", "interjections", "thanking_words",
            "encouraging_words", "discouraging_words",
        ]}
        cleaned, sentiment = self.nlp.strip_and_sentiment(
            "thanks for the help", self.vocabulary, sentiment,
            ["thanking_words"],
        )
        self.assertEqual(sentiment["thanking_words"], 1)
        self.assertNotIn("thanks", cleaned.lower())


class TemplateStructure(unittest.TestCase):
    def setUp(self):
        self.nlp = build_parser()

    def test_count_letters_template_extracts_slots(self):
        structure, slots = self.nlp.parse_structure(
            "how many l in hello", 0.75
        )
        matched = self.nlp.match_structure(self.nlp.templates, structure)
        self.assertIsNotNone(matched)
        self.assertEqual(matched.get("intent"), "count_letters_in_word")
        self.assertEqual(slots.get("letter"), "l")
        self.assertEqual(slots.get("word"), "hello")


class MultiPathTemplateRegression(unittest.TestCase):
    """
    Regression: find_candidates must evaluate EVERY path inside a
    template's structure array-of-arrays, not only the last one
    (the old indentation bug made alternate word orders unparseable).
    """

    def setUp(self):
        self.nlp = build_parser()

    def test_find_candidates_considers_every_path(self):
        tpl = {
            "intent": "synthetic_order",
            "structure": [
                [
                    {"tag": "A", "type": "vocab", "required": True},
                    {"tag": "B", "type": "vocab", "required": True},
                ],
                [
                    {"tag": "B", "type": "vocab", "required": True},
                    {"tag": "A", "type": "vocab", "required": True},
                ],
            ],
        }
        # Isolate: real dataset templates contribute their own candidates
        # (including unhashable list tags), which would pollute assertions.
        self.nlp.templates = [tpl]

        candidates = []
        self.nlp.find_candidates([], candidates)
        tags = {t for _, t in candidates}
        self.assertTrue({"A", "B"} <= tags, f"both first nodes expected, got {tags}")

        candidates = []
        self.nlp.find_candidates(["A"], candidates)
        tags = {t for _, t in candidates}
        self.assertIn("B", tags, f"path 1 continuation missing, got {tags}")

        candidates = []
        self.nlp.find_candidates(["B"], candidates)
        tags = {t for _, t in candidates}
        self.assertIn("A", tags, f"path 2 continuation missing, got {tags}")

    def test_real_dir_deletion_matches_both_word_orders(self):
        """The original user-facing bug: one order parsed, the other was rejected."""
        for prompt in ("delete directory test", "directory delete test"):
            with self.subTest(prompt=prompt):
                structure, slots = self.nlp.parse_structure(prompt, 0.75)
                matched = self.nlp.match_structure(
                    self.nlp.templates, structure
                )
                self.assertIsNotNone(matched, prompt)
                self.assertEqual(matched.get("intent"), "dir_deletion")
                self.assertEqual(slots.get("dir"), "test")


class ArrayTagSupport(unittest.TestCase):
    """
    Test support for tags being either strings or arrays of strings.
    This allows multiple vocabulary variants to match the same slot.
    """

    def setUp(self):
        self.nlp = build_parser()

    def test_tag_matches_with_string_tag(self):
        self.assertTrue(self.nlp.tag_matches("<||vocab_show||>", "<||vocab_show||>"))
        self.assertFalse(self.nlp.tag_matches("<||vocab_show||>", "<||vocab_hide||>"))

    def test_tag_matches_with_array_tag(self):
        tag_array = ["<||vocab_show||>", "<||vocab_display||>", "<||vocab_reveal||>"]
        self.assertTrue(self.nlp.tag_matches("<||vocab_show||>", tag_array))
        self.assertTrue(self.nlp.tag_matches("<||vocab_display||>", tag_array))
        self.assertTrue(self.nlp.tag_matches("<||vocab_reveal||>", tag_array))
        self.assertFalse(self.nlp.tag_matches("<||vocab_hide||>", tag_array))

    def test_find_candidates_with_array_tags(self):
        template_with_array = {
            "intent": "test_array_tag",
            "structure": [[
                {
                    "tag": ["<||vocab_show||>", "<||vocab_display||>"],
                    "type": "vocab",
                    "required": True
                },
                {
                    "tag": "<||string||>",
                    "type": "string",
                    "required": True
                }
            ]]
        }
        self.nlp.templates.append(template_with_array)
        try:
            structure = ["<||vocab_display||>"]
            candidates = []
            self.nlp.find_candidates(structure, candidates)
            found = any(c[0] == "string" for c in candidates)
            self.assertTrue(found, "Array tag template should add next required slot to candidates")
        finally:
            self.nlp.templates.pop()

    def test_match_structure_with_array_tags(self):
        template_with_array = {
            "intent": "test_array_tag",
            "structure": [[
                {
                    "tag": ["<||vocab_show||>", "<||vocab_display||>"],
                    "type": "vocab",
                    "required": True
                },
                {
                    "tag": "<||string||>",
                    "type": "string",
                    "required": True
                }
            ]]
        }

        structure1 = ["<||vocab_show||>", "<||string||>"]
        matched1 = self.nlp.match_structure([template_with_array], structure1)
        self.assertIsNotNone(matched1, "Should match with first array tag variant")
        self.assertEqual(matched1.get("intent"), "test_array_tag")

        structure2 = ["<||vocab_display||>", "<||string||>"]
        matched2 = self.nlp.match_structure([template_with_array], structure2)
        self.assertIsNotNone(matched2, "Should match with second array tag variant")

        structure3 = ["<||vocab_hide||>", "<||string||>"]
        matched3 = self.nlp.match_structure([template_with_array], structure3)
        self.assertIsNone(matched3, "Should not match with value outside array tag")

    def test_backward_compatibility_with_string_tags(self):
        structure, slots = self.nlp.parse_structure(
            "how many l in hello", 0.75
        )
        matched = self.nlp.match_structure(self.nlp.templates, structure)
        self.assertIsNotNone(matched)
        self.assertEqual(matched.get("intent"), "count_letters_in_word")


class FlintParserEdgeCases(unittest.TestCase):
    """
    Regression tests for NPC-Forge's biological and structural edge cases.
    """

    def setUp(self):
        self.nlp = build_parser()

    def test_string_greedy_capture_with_embedded_vocab(self):
        """EDGE CASE 1: slang request containing spaces isn't broken by vocabulary."""
        prompt = "what is the definition of the slang noob"
        structure, slots = self.nlp.parse_structure(prompt, 0.75)
        matched = self.nlp.match_structure(self.nlp.templates, structure)

        self.assertIsNotNone(matched)
        self.assertEqual(matched.get("intent"), "slang_meaning")
        self.assertEqual(slots.get("string"), "noob")

    def test_single_reserved_word_as_variable_argument(self):
        """EDGE CASE 2: reserved word used as an argument."""
        prompt = "find in file create"
        structure, slots = self.nlp.parse_structure(prompt, 0.75)
        matched = self.nlp.match_structure(self.nlp.templates, structure)

        if matched:  # if the find template exists in the test dataset
            self.assertEqual(slots.get("word"), "create")

    def test_optional_vocab_nodes_do_not_fagocitate_variables(self):
        """EDGE CASE 3: optional nodes (required: false)."""
        prompt = "find in file file"
        structure, slots = self.nlp.parse_structure(prompt, 0.75)
        matched = self.nlp.match_structure(self.nlp.templates, structure)

        if matched:
            self.assertEqual(slots.get("word"), "file")

    def test_quoted_string_with_command_inside_remains_pure(self):
        """EDGE CASE 4: quoted strings."""
        prompt = 'what is the definition of the slang "define"'
        structure, slots = self.nlp.parse_structure(prompt, 0.75)
        matched = self.nlp.match_structure(self.nlp.templates, structure)

        self.assertIsNotNone(matched)
        self.assertEqual(matched.get("intent"), "slang_meaning")
        self.assertEqual(slots.get("string"), "define")


if __name__ == "__main__":
    unittest.main()