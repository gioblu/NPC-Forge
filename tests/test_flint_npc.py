"""
Integration tests for FlintNPC: exact/typo-tolerant matching,
template slot extraction, false-positive resolution and the
conversational context system, across the "termy" NPC dataset
shipped in this repository (dataset_*.json split format).
"""
import os
import sys
import unittest
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
for path in (str(ROOT), str(ROOT / "src")):
    if path not in sys.path:
        sys.path.insert(0, path)

os.chdir(ROOT)  # FlintNPC resolves "npcs/<name>" relative to the cwd

from FlintNPC import FlintNPC


@lru_cache(maxsize=1)
def get_npc():
    return FlintNPC("termy", log_level="WARNING")


def make_block(message, inputs=None, context=None):
    """Builds a minimal synthetic NDF block for context tests."""
    block = {
        "input": inputs or [],
        "message": [message],
        "permission": "yolo",
    }
    if context is not None:
        block["context"] = context
    return block


class TestFlintNPC(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.npc = get_npc()

    def test_exact_match_returns_full_confidence(self):
        res = self.npc.process_message("what time is it")
        self.assertEqual(res["status"], "exact match")
        self.assertEqual(res["confidence"], 1.0)

    def test_probabilistic_match_tolerates_typos(self):
        query = "what is a zombie procces in linux"
        res = self.npc.process_message(query)
        self.assertEqual(res["status"], "probabilistic match")
        self.assertGreaterEqual(
            res["confidence"], self.npc.sentence_threshold
        )
        self.assertIn("process table", res["response"])

    def test_unknown_input_is_rejected(self):
        res = self.npc.process_message("asdkjqwoe kqjwe oiqjwe")
        self.assertEqual(res["status"], "rejected")
        self.assertEqual(res["confidence"], 0.0)

    def test_template_match_extracts_slots(self):
        res = self.npc.process_message("how many l in hello")
        self.assertEqual(res["status"], "template match")
        self.assertEqual(res["slots"].get("letter"), "l")
        self.assertEqual(res["slots"].get("word"), "hello")


class TestContextSystem(unittest.TestCase):
    """
    Covers the runtime conversational context: priority over the
    global dataset, sibling persistence, overwrite, explicit clear
    ("context": []) and rejection-time clearing.
    Each test uses a fresh NPC instance so mutations never leak.
    """

    def setUp(self):
        self.npc = FlintNPC("termy", log_level="ERROR")
        self.parent = make_block("parent", context=[
            make_block("moved", inputs=["move it"]),
            make_block("deleted", inputs=["delete it"]),
        ])

    def test_update_context_loads_and_clears(self):
        self.npc.update_context(self.parent)
        self.assertIn("move it", self.npc.active_context_map)
        self.assertIn("delete it", self.npc.active_context_map)

        # Block without context key: state persists
        self.npc.update_context(make_block("leaf"))
        self.assertIn("move it", self.npc.active_context_map)

        # "context": [] explicitly clears
        self.npc.update_context(make_block("clearer", context=[]))
        self.assertEqual(self.npc.active_context_map, {})

    def test_context_match_and_sibling_persistence(self):
        self.npc.update_context(self.parent)

        res = self.npc.process_message("move it")
        self.assertEqual(res["status"], "context match")
        self.assertEqual(res["response"], "moved")

        # Consumed leaf has no nested context: sibling stays active
        self.assertIn("delete it", self.npc.active_context_map)

        res = self.npc.process_message("delete it")
        self.assertEqual(res["status"], "context match")
        self.assertEqual(res["response"], "deleted")

    def test_context_overrides_global_exact_match(self):
        shadow = make_block("context wins", inputs=["what time is it"])
        self.npc.update_context(make_block("p", context=[shadow]))

        res = self.npc.process_message("what time is it")
        self.assertEqual(res["status"], "context match")
        self.assertEqual(res["response"], "context wins")

    def test_exact_match_with_context_overwrites_state(self):
        self.npc.update_context(self.parent)

        starter = make_block("started", inputs=["start the flow"], context=[
            make_block("inner", inputs=["inner yes"]),
        ])
        self.npc.exact_match_map["start the flow"] = starter

        res = self.npc.process_message("start the flow")
        self.assertEqual(res["status"], "exact match")

        # Old context replaced by the new one
        self.assertNotIn("move it", self.npc.active_context_map)
        self.assertIn("inner yes", self.npc.active_context_map)

    def test_probabilistic_match_recalls_context_entries(self):
        # Synthetic fixtures carry OOV words; the shipped 0.6668 threshold is
        # calibrated for real corpus phrases. Lower it for this routing test.
        self.npc.sentence_threshold = 0.5
        self.npc.word_threshold = 0.5

        ctx = make_block("ctx fuzzy", inputs=["what is a zombie capacitor"])
        self.npc.update_context(make_block("p", context=[ctx]))

        res = self.npc.process_message("what is a zombie capacitro")
        self.assertEqual(res["status"], "probabilistic match")
        self.assertEqual(res["response"], "ctx fuzzy")

    def test_rejection_persists_context(self):
        self.npc.update_context(self.parent)
        res = self.npc.process_message("asdkjqwoe kqjwe oiqjwe")
        self.assertEqual(res["status"], "rejected")
        self.assertIn("move it", self.npc.active_context_map)

    def test_multi_turn_directory_flow(self):
        """The motivating flow: create -> move it -> delete it."""
        creator = make_block("created", inputs=["create a directory"], context=[
            make_block("moving", inputs=["move it"]),
            make_block("deleting", inputs=["delete it"]),
        ])
        self.npc.exact_match_map["create a directory"] = creator

        self.assertEqual(
            self.npc.process_message("create a directory")["status"],
            "exact match",
        )
        self.assertEqual(
            self.npc.process_message("move it")["status"], "context match"
        )
        self.assertEqual(
            self.npc.process_message("delete it")["status"], "context match"
        )


class TestFalsePositiveResolution(unittest.TestCase):
    """
    Each query below belongs to a large cluster of "what is X in
    linux" / "explain X" intents that share near-identical scaffolding
    (what, is, explain, linux, does, mean...) and differ only by one
    or two distinguishing keywords. Every case must resolve to its own
    intent rather than bleeding into a scaffolding sibling.
    """

    CASES = [
        ("what is netfilter", "Netfilter is a kernel framework"),
        ("what is ebpf", "sandboxed programs"),
        ("what does sysctl do", "Sysctl is used to configure"),
        ("what is kswapd", "reclaiming memory pages"),
        ("what is an io scheduler", "disk read and write requests"),
        ("what is sysfs", "exports information about sub-systems"),
        ("what causes a kernel panic", "kernel panic is a safety"),
        ("tell me about swap", "paging and swapping"),
        ("what is the oom killer", "Out-Of-Memory Killer"),
        ("difference between process and thread", "lightweight subunit"),
        ("what are cgroups", "Cgroups are a core kernel feature"),
        ("what are linux namespaces", "routing tables, process trees"),
        ("what does copy on write mean", "COW is an optimization"),
        ("what is an interrupt handler", "high-priority callback"),
        ("what is the proc filesystem", "in-memory filesystem"),
        ("what is the role of the linux kernel", "core interface"),
        ("what does monolithic kernel mean", "single kernel space"),
        ("user space vs kernel space", "Kernel space is reserved"),
        ("what are kernel modules", "loaded or unloaded"),
        ("how does linux achieve multitasking", "completely fair"),
        ("what is the virtual filesystem vfs", "abstraction layer"),
        ("what is the init process", "PID 1"),
        ("difference between a terminal and a shell", "underlying"),
        ("what does the pipe symbol do", "redirects the standard"),
        ("difference between > and >>", "overwrites the file"),
        ("what does 2>&1 mean", "stderr"),
        ("what is the etc directory for", "system configuration"),
        ("difference between chmod and chown", "owner or group"),
        ("what does chmod 755 mean", "permissions (rwx)"),
        ("hard link vs soft link", "physical data (inode)"),
        ("ctrl c vs ctrl z", "SIGINT"),
        ("environment variables like path", "PATH variable"),
        ("single vs double quotes in shell", "variable expansion"),
        ("why do i get permission denied as admin", "prefix the"),
        ("what is a syscall", "programmatic way"),
        ("what is a zombie process", "process table"),
    ]

    @classmethod
    def setUpClass(cls):
        cls.npc = get_npc()

    def test_resolves_to_own_intent(self):
        for query, expected in self.CASES:
            with self.subTest(query=query):
                res = self.npc.process_message(query)
                self.assertIn(expected, res["response"])


class TestKnownLimitations(unittest.TestCase):
    """
    Documents remaining false positives so regressions and future
    fixes stay visible instead of silently disappearing. Both cases
    share the same root cause: a short anchor token that is punctuation
    only ("~", ".", "..") gets its real (high) IDF weight since it
    occurs in only one intent, but the user query spells the word out
    ("tilde", "dot", "dotdot") instead of typing the literal symbol, so
    the anchor never matches and its weight is lost from the score
    instead of contributing to it.
    """

    @classmethod
    def setUpClass(cls):
        cls.npc = get_npc()

    @unittest.expectedFailure
    def test_tilde_symbol_anchor_not_spelled_out_in_query(self):
        res = self.npc.process_message("what does the tilde represent")
        self.assertIn("user home directory", res["response"])

    @unittest.expectedFailure
    def test_dot_dotdot_symbol_anchor_not_spelled_out_in_query(self):
        res = self.npc.process_message("what does dot and dotdot mean")
        self.assertIn("parent directory", res["response"])


if __name__ == "__main__":
    unittest.main()