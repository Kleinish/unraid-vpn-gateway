import importlib.util
import unittest
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace
spec = importlib.util.spec_from_file_location('firewall', Path(__file__).resolve().parents[1] / 'src/firewall.py')
firewall = importlib.util.module_from_spec(spec)
spec.loader.exec_module(firewall)

class LanRouteTests(unittest.TestCase):
    def test_cross_vlan_route(self):
        outputs = [
            SimpleNamespace(stdout='default via 10.6.72.1 dev eth0\n'),
            SimpleNamespace(stdout='10.6.72.1 dev eth0 src 10.6.72.10\n'),
            SimpleNamespace(stdout='10.7.7.0 via 10.8.0.5 dev tun0\n'),
        ]
        with patch.object(firewall.subprocess, 'run', side_effect=outputs), patch.object(firewall, 'run') as runner:
            firewall.lan_routes(['10.7.7.0/24'], '')
            runner.assert_called_once_with('ip', '-4', 'route', 'replace', '10.7.7.0/24', 'via', '10.6.72.1', 'dev', 'eth0')

    def test_reject_default_bypass(self):
        with patch.object(firewall.subprocess, 'run', return_value=SimpleNamespace(stdout='10.6.72.1 dev eth0')):
            with self.assertRaises(ValueError):
                firewall.lan_routes(['0.0.0.0/0'], '10.6.72.1')

    def test_existing_direct_route_not_overwritten(self):
        outputs = [SimpleNamespace(stdout='10.6.72.1 dev eth0'), SimpleNamespace(stdout='10.6.72.0 dev eth0 src 10.6.72.10')]
        with patch.object(firewall.subprocess, 'run', side_effect=outputs), patch.object(firewall, 'run') as runner:
            firewall.lan_routes(['10.6.72.0/24'], '10.6.72.1')
            runner.assert_not_called()

if __name__ == '__main__':
    unittest.main()
