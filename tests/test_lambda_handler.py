import json
import unittest
from unittest import mock

import lambda_function
from pickem_plug import RunConfig, RunResult

RESULT = RunResult(week=10, csv_path='./out/x.csv', html_path='./out/readout.html')


class LambdaHandlerTest(unittest.TestCase):
    def test_scheduler_style_event_runs_with_defaults(self):
        event = {'version': '0', 'source': 'aws.events', 'time': '2026-11-09T12:00:00Z'}
        with mock.patch.object(lambda_function, 'run', return_value=RESULT) as run:
            lambda_function.lambda_handler(event, None)
        run.assert_called_once_with(RunConfig())

    def test_event_key_overrides_one_default(self):
        with mock.patch.object(lambda_function, 'run', return_value=RESULT) as run:
            lambda_function.lambda_handler({'fetch_espnbet': False}, None)
        run.assert_called_once_with(RunConfig(fetch_espnbet=False))

    def test_invalid_value_raises_and_nothing_runs(self):
        with mock.patch.object(lambda_function, 'run', return_value=RESULT) as run:
            with self.assertRaises(ValueError) as ctx:
                lambda_function.lambda_handler({'fetch_oddshark': 'no'}, None)
        self.assertIn('fetch_oddshark', str(ctx.exception))
        run.assert_not_called()

    def test_returns_json_serializable_summary(self):
        with mock.patch.object(lambda_function, 'run', return_value=RESULT):
            result = lambda_function.lambda_handler({}, None)
        self.assertEqual(result, {'week': 10, 'csv_path': './out/x.csv', 'html_path': './out/readout.html'})
        json.dumps(result)


if __name__ == '__main__':
    unittest.main()
