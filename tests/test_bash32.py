"""Tests that TERMy shell helpers work under bash 3.2 (macOS /bin/bash)."""
import subprocess
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent / "npcs" / "termy" / "scripts"
STUBS = "termy_say() { :; }; termy_set_context() { :; }; tput() { :; };"

def run_bash(script, stdin=""):
    return subprocess.run(
        ["/bin/bash", "-c", script], input=stdin, capture_output=True, text=True
    )

class TestHelpersOnBash32(unittest.TestCase):
    def test_termy_question_sets_caller_variable_example(self):
        script = f'source "{SCRIPTS / "termy.sh"}"; {STUBS} termy_question "Name" ans; printf "[%s]" "$ans"'
        res = run_bash(script, stdin="hello\n")
        self.assertEqual(res.stdout.split("Name: ")[-1], "[hello]", res.stderr)
        self.assertEqual(res.stderr, "")

    def test_termy_execute_extension_case_invariant(self):
        with tempfile.TemporaryDirectory() as tmp:
            for name in ("run.py", "run.PY", "run.Py"):
                with self.subTest(name=name):
                    path = Path(tmp) / name
                    path.write_text("print('ok')\n")
                    script = f'source "{SCRIPTS / "files.sh"}"; {STUBS} termy_execute "{path}"'
                    res = run_bash(script)
                    self.assertEqual(res.returncode, 0, res.stderr)
                    self.assertEqual(res.stdout.strip(), "ok")

if __name__ == "__main__":
    unittest.main()
