import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('mcp_quality', Path(__file__).parents[1] / 'mcp_quality.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class Boundaries(unittest.TestCase):
    def test_remote_or_credential_url_refused(self):
        for value in ['https://example.org/mcp', 'http://localhost/mcp', 'http://127.0.0.1.example.org/mcp', 'http://127.0.0.1/mcp?key=x', 'http://user:secret@127.0.0.1/mcp']:
            with self.subTest(value=value), self.assertRaises(ValueError):
                m.local_url(value)
        self.assertEqual(m.local_url('http://127.0.0.1:3210/mcp'), 'http://127.0.0.1:3210/mcp')

    def test_symlink_refused_and_candidate_bytes_not_executed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); source = root / 'source'; source.mkdir()
            (source / 'hook.py').write_text('raise RuntimeError("candidate hook must never run")')
            hashes = m.stage(source, root / 'snapshot')
            self.assertIn('hook.py', hashes)
            (source / 'escape').symlink_to('/etc/hosts')
            with self.assertRaises(ValueError): m.stage(source, root / 'snapshot2')

    def test_ignore_file_cannot_hide_candidate(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); source = root / 'source'; source.mkdir()
            (source / '.semgrepignore').write_text('*\n'); (source / 'a.py').write_text('eval(user_input)')
            m.stage(source, root / 'snapshot')
            self.assertFalse((root / 'snapshot/.semgrepignore').exists())
            self.assertTrue((root / 'snapshot/a.py').exists())

    def test_package_heuristic_is_not_cve_or_certification(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory); (path / 'package.json').write_text(json.dumps({'scripts': {'postinstall': 'node hook.js'}, 'dependencies': {'reqests': '1.0.0', 'express': '5.0.0'}}))
            matches = m.package_observations(path)
            self.assertEqual({x['rule'] for x in matches}, {'mcp.package-lifecycle', 'mcp.name-confusion'})
            self.assertIn('not proven typosquat', next(x['status'] for x in matches if 'status' in x))

    def test_control_name_collision_preserves_every_file_and_mapping(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); source = root / 'source'; source.mkdir()
            originals = {'.gitignore': '*\n', '.gitignore.disabled.txt': 'eval(user_input)', '.gitignore.disabled.1.txt': 'second candidate'}
            for name, content in originals.items(): (source / name).write_text(content)
            mapping = {}; snapshot = root / 'snapshot'
            hashes = m.stage(source, snapshot, path_mapping=mapping)
            self.assertEqual(set(hashes), set(originals))
            self.assertEqual(mapping, {'.gitignore': '.gitignore.disabled.2.txt'})
            for name, content in originals.items():
                self.assertEqual((snapshot / mapping.get(name, name)).read_text(), content)

    def test_database_staging_preserves_manifest_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); source = root / 'database'; source.mkdir()
            (source / 'osv-scanner.toml').write_text('snapshot member')
            m.stage(source, root / 'snapshot', neutralize_controls=False)
            self.assertEqual((root / 'snapshot/osv-scanner.toml').read_text(), 'snapshot member')

    def test_missing_advisory_results_never_certify_clean(self):
        for output in ['', '{}', '[]', '{"results": null}']:
            with self.subTest(output=output), self.assertRaises(ValueError): m.advisory_output(output)
        self.assertEqual(m.advisory_output('{"results": []}'), {'results': []})
