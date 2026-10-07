import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class CliPackageResolutionTests(unittest.TestCase):
    def test_direct_entrypoint_uses_matching_modules_ahead_of_installed_core(self):
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            unrelated = temporary / 'old_install' / 'core'
            unrelated.mkdir(parents=True)
            (unrelated / '__init__.py').write_text('')
            (unrelated / 'diagnostics.py').write_text('raise RuntimeError("Wrong core package imported")\n')
            script = temporary / 'check.bs'
            script.write_text('''value = 7
if true:
    push(f"Value ${value}")
end
try:
    pyimport("urllib.request").Request("http://example.invalid", method="DELETE")
catch TypeError:
    push("caught")
end
''')
            environment = dict(os.environ, PYTHONPATH=str(unrelated.parent))
            result = subprocess.run([sys.executable, str(ROOT / 'core/main.py'), str(script)],
                                    cwd=temporary, env=environment, capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout, 'Value 7\ncaught\n')
            self.assertEqual(result.stderr, '')
