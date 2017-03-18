import sys
import subprocess

from treq.test.util import TestCase


class TreqImportTests(TestCase):
    def test_importing_treq_should_not_install_reactor(self):
        # This test must be run under a new python process
        # since treq.test.util has imported reactor already.
        code = '\n'.join([
            'import sys',
            'import treq',
            'sys.exit(int("twisted.internet.reactor" in sys.modules))',
        ])
        subprocess.check_call([sys.executable, '-c', code])
