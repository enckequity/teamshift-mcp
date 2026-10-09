import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import mcp_quality

from native_stdio import verify_source


class NativeAdmissionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'package.json').write_text(json.dumps({'name': 'owned-fixture', 'version': '1.0.0'}))
        (self.root / 'server.mjs').write_text('// No execution in admission tests\n')
        self.receipt = {'identity': 'owned-fixture', 'package': 'owned-fixture', 'version': '1.0.0',
                        'profile': 'baseline', 'admission': 'reviewed-offline-baseline',
                        'entrypoint': 'server.mjs', 'files': self.hashes()}

    def hashes(self):
        return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in self.root.iterdir() if p.is_file()}

    def test_exact_empty_dependency_tree_admitted(self):
        verify_source(self.root, self.receipt)

    def test_changed_or_unmanifested_source_refused(self):
        (self.root / 'extra.mjs').write_text('unreviewed')
        with self.assertRaisesRegex(ValueError, 'differ'):
            verify_source(self.root, self.receipt)

    def test_unlocked_dependency_refused(self):
        (self.root / 'package.json').write_text(json.dumps({'name': 'owned-fixture', 'version': '1.0.0',
                                                         'dependencies': {'unreviewed': '*'}}))
        self.receipt['files'] = self.hashes()
        with self.assertRaises(FileNotFoundError):
            verify_source(self.root, self.receipt)

    def test_tool_invocation_profile_refused(self):
        self.receipt['profile'] = 'fixed-fixture'
        with self.assertRaisesRegex(ValueError, 'baseline admission'):
            verify_source(self.root, self.receipt)

    def test_unreviewed_entrypoint_refused(self):
        self.receipt['entrypoint'] = '../foreign.mjs'
        with self.assertRaisesRegex(ValueError, 'entrypoint'):
            verify_source(self.root, self.receipt)

    def test_linux_static_engine_root_must_be_explicit(self):
        sandbox = self.root / 'never-executed-sandbox'
        sandbox.write_text('not executable')
        with mock.patch('mcp_quality.sys.platform', 'linux'), mock.patch.dict('os.environ', {
            'MCP_QUALITY_BWRAP': str(sandbox),
            'MCP_QUALITY_BWRAP_SHA256': hashlib.sha256(sandbox.read_bytes()).hexdigest()
        }, clear=True):
            with self.assertRaisesRegex(ValueError, 'Explicit owned static engine root required'):
                mcp_quality.execute([str(mcp_quality.ROOT / 'mcp_quality.py')],
                                    mcp_quality.environment(self.root), self.root, offline=True)


if __name__ == '__main__':
    unittest.main()
