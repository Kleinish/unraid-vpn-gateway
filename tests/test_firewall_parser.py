import importlib.util
import tempfile
import unittest
from pathlib import Path
spec = importlib.util.spec_from_file_location('firewall', Path(__file__).resolve().parents[1] / 'src/firewall.py')
firewall = importlib.util.module_from_spec(spec)
spec.loader.exec_module(firewall)

class ParserTests(unittest.TestCase):
    def test_numeric_remote(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'client.ovpn'
            p.write_text('client\nproto udp\nremote 198.51.100.5 1194\n')
            self.assertEqual(firewall.endpoints(p), [('198.51.100.5', '1194', 'udp')])
    def test_hostname_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'client.ovpn'
            p.write_text('remote example.org 1194\n')
            with self.assertRaises(ValueError):
                firewall.endpoints(p)
if __name__ == '__main__':
    unittest.main()
