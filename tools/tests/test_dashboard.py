"""Observer safety and interpretation tests; no sudo, Mininet or OS-Ken needed."""
import json
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from live_dashboard import Collector, ThreadingHTTPServer, handler_for, parse_events, parse_flows

FLOW = "OFPST_FLOW reply (OF1.3):\n cookie=0xa, duration=8.5s, table=0, n_packets=4, n_bytes=280, hard_timeout=60, priority=200,tcp,nw_src=10.0.0.1,nw_dst=10.0.0.4,tp_dst=8080 actions=NORMAL\n cookie=0x0, duration=12s, table=0, n_packets=7, n_bytes=400, priority=100,tcp,nw_dst=10.0.0.4,tp_dst=8080 actions=drop\n"


class DashboardTests(unittest.TestCase):
    def test_flow_age_and_packet_counters_have_distinct_meaning(self):
        rules = parse_flows(FLOW)
        self.assertEqual(len(rules), 2)
        self.assertEqual((rules[0]['source'], rules[0]['remaining_s'], rules[0]['packets']),
                         ('10.0.0.1', 51.5, 4))
        self.assertEqual(rules[1]['kind'], 'deny')

    def test_unrelated_or_malformed_rules_never_become_host_grants(self):
        self.assertEqual(parse_flows(FLOW.replace('tp_dst=8080', 'tp_dst=22')), [])
        for old, new in [('nw_src=10.0.0.1', 'nw_src=10.0.0.1/24'),
                         ('actions=NORMAL', 'actions=drop'), ('n_packets=4', 'n_packets=bad'),
                         ('table=0', 'table=3'), ('priority=200,tcp', 'priority=200,in_port=99,tcp'),
                         ('priority=100,tcp', 'priority=100,in_port=99,tcp')]:
            with self.subTest(restriction=new), self.assertRaises(ValueError):
                parse_flows(FLOW.replace(old, new))

    def test_raw_log_fields_cannot_leak_through_events(self):
        events = parse_events("2026-11-01 07:51:25,340 INFO LOGIN_SUCCESS username='<script>bad</script> session_id=SECRET password=PRIVATE' client_ip=10.0.0.1\n")
        self.assertEqual(events[0]['event'], 'LOGIN_SUCCESS')
        encoded = json.dumps(events)
        for private in ['SECRET', 'PRIVATE', 'script', 'username', 'session_id']:
            self.assertNotIn(private, encoded)
        forged = parse_events("2026-11-01 07:51:25,340 WARNING LOGIN_FAILURE username='fake client_ip=10.0.0.2 text' client_ip=10.0.0.1 count=1\n")
        self.assertEqual(forged[0]['source'], '10.0.0.1')
        details = parse_events("2026-11-01 07:51:25,340 WARNING LOGIN_FAILURE username='x count=999 reason=EXPIRED remaining_sessions=8 x' client_ip=10.0.0.1 count=1\n")
        self.assertEqual(details[0]['count'], 1)
        self.assertNotIn('reason', details[0])
        self.assertNotIn('remaining_sessions', details[0])
        actual = parse_events("2026-11-01 07:51:25,340 INFO ACCESS_UPDATED reason=LOGOUT client_ip=10.0.0.1 remaining_sessions=2\n")
        self.assertEqual((actual[0]['reason'], actual[0]['remaining_sessions']), ('LOGOUT', 2))
        failed = parse_events("2026-11-01 07:51:25,340 ERROR ACCESS_UPDATE_UNCONFIRMED reason=ALLOW_FAILED client_ip=10.0.0.1\n")
        self.assertEqual(failed[0]['reason'], 'ALLOW_FAILED')
        self.assertEqual(parse_events('forged INFO LOGIN_SUCCESS client_ip=10.0.0.1'), [])

    def test_recorded_mode_cannot_launch_live_commands(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'flows.txt'
            path.write_text(FLOW)
            with patch('live_dashboard.command', side_effect=AssertionError('Live command in replay')):
                state = Collector(flow_snapshot=path).snapshot()
            self.assertEqual(state['mode'], 'recorded')
            self.assertTrue(state['switch_ok'])
            self.assertIsNone(state['listeners'])

    def test_unavailable_ovs_means_unknown_not_denied(self):
        with patch('live_dashboard.command', return_value=(False, '')):
            state = Collector().snapshot()
        self.assertFalse(state['switch_ok'])
        self.assertEqual(state['rules'], [])
        self.assertTrue(state['errors'])
        with patch('live_dashboard.command', side_effect=[(True, FLOW.replace('table=0', 'table=3')), (False, '')]):
            unknown = Collector().snapshot()
        self.assertFalse(unknown['switch_ok'])
        self.assertEqual(unknown['rules'], [])
        self.assertIn('policy is unknown', unknown['errors'][0])

    def test_collector_uses_only_read_commands(self):
        with patch('live_dashboard.command', side_effect=[(True, FLOW), (True, 'LISTEN 0 50 127.0.0.1:6653 0.0.0.0:*')]) as runner:
            state = Collector().snapshot()
        self.assertEqual([x.args[0] for x in runner.call_args_list], [
            ['ovs-ofctl', '-O', 'OpenFlow13', 'dump-flows', 's1'], ['ss', '-H', '-ltn']])
        self.assertTrue(state['listeners']['6653'])
        self.assertFalse(state['listeners']['9999'])

    def test_http_has_no_arbitrary_file_route_or_write_endpoint(self):
        collector = Collector()
        collector.snapshot = lambda: {'mode': 'recorded', 'rules': []}
        server = ThreadingHTTPServer(('127.0.0.1', 0), handler_for(collector))
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        base = f'http://127.0.0.1:{server.server_port}'
        try:
            with urlopen(base + '/api/state') as response:
                self.assertEqual(json.load(response)['mode'], 'recorded')
                self.assertEqual(response.headers['Cache-Control'], 'no-store')
            for request, code in [(Request(base + '/../../auth_server.py'), 404),
                                  (Request(base + '/', headers={'Host': 'foreign.example'}), 403),
                                  (Request(base + '/api/state', data=b'{}'), 501)]:
                with self.assertRaises(HTTPError) as error:
                    urlopen(request)
                self.assertEqual(error.exception.code, code)
        finally:
            server.shutdown()
            server.server_close()
            worker.join(2)


if __name__ == '__main__':
    unittest.main()
