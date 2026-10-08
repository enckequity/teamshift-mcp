import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from fixtures import fixtures

ROOT = Path(__file__).parents[1]
spec = importlib.util.spec_from_file_location('quality', ROOT / 'mcp_quality.py')
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)

class SyntheticFixtures(unittest.TestCase):
    def test_100_labeled_positive_cases_and_held_out_controls(self):
        engine = os.environ.get('MCP_QUALITY_SEMGREP')
        if not engine:
            self.fail('MCP_QUALITY_SEMGREP is required; fixture checks cannot silently skip')
        cases = fixtures()
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory); source = home / 'source'; source.mkdir()
            for case in cases:
                path = source / case['file']; path.parent.mkdir(parents=True, exist_ok=True); path.write_text(case['content'])
            # Not drawn from the positive fixture generators.
            controls = {'benign.py': 'print("hello")\nvalue = 2 + 3\n',
                        'benign.ts': 'const result = JSON.parse(input);\n',
                        'benign.md': 'The owner reviews instructions before sending messages.\n',
                        'benign/package.json': json.dumps({'dependencies': {'express':'5.0.0','zod':'4.0.0'}, 'scripts': {'test':'node --test'}})}
            for name, content in controls.items():
                path = source / name; path.parent.mkdir(parents=True, exist_ok=True); path.write_text(content)
            result = m.execute([engine, 'scan', '--config', str(ROOT/'rules.yaml'), '--metrics', 'off',
                                '--disable-version-check', '--no-git-ignore', '--json', str(source)], m.environment(home), home, offline=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            data = json.loads(result.stdout); self.assertEqual(data['errors'], [])
            observations = {(Path(x['path']).relative_to(source).as_posix(), x['check_id'].split('.')[-1]) for x in data['results']}
            observations |= {(x['path'], x['rule'].split('.')[-1]) for x in m.package_observations(source)}
            for case in cases:
                with self.subTest(case=case['id']):
                    self.assertIn((case['file'], case['rule'].split('.')[-1]), observations)
            for name in controls:
                with self.subTest(benign=name):
                    self.assertFalse(any(path == name for path, rule in observations))
