import importlib.util
import pathlib
import unittest

from pickem_plug import FETCH_OPTION_KEYS, RunConfig

# __main__.py can't be imported by name (that gives the test runner), so load it by path.
_spec = importlib.util.spec_from_file_location('pickem_cli', pathlib.Path(__file__).parent.parent / '__main__.py')
cli = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cli)


class RunConfigDefaultsTest(unittest.TestCase):
    def test_all_fetch_options_default_true(self):
        config = RunConfig()
        for key in FETCH_OPTION_KEYS:
            self.assertIs(getattr(config, key), True, key)

    def test_override_csv_defaults_to_none(self):
        self.assertIsNone(RunConfig().override_csv_data)


class RunConfigFromEventTest(unittest.TestCase):
    def test_scheduler_style_event_uses_defaults(self):
        event = {'version': '0', 'source': 'aws.events', 'time': '2026-11-09T12:00:00Z', 'detail': {}}
        self.assertEqual(RunConfig.from_event(event), RunConfig())

    def test_empty_or_missing_event_uses_defaults(self):
        self.assertEqual(RunConfig.from_event({}), RunConfig())
        self.assertEqual(RunConfig.from_event(None), RunConfig())

    def test_event_overrides_one_default(self):
        config = RunConfig.from_event({'fetch_espnbet': False})
        self.assertFalse(config.fetch_espnbet)
        self.assertTrue(config.fetch_pickem)
        self.assertTrue(config.fetch_draftkings)
        self.assertTrue(config.fetch_oddshark)

    def test_event_can_set_every_option(self):
        config = RunConfig.from_event({key: False for key in FETCH_OPTION_KEYS})
        for key in FETCH_OPTION_KEYS:
            self.assertFalse(getattr(config, key), key)

    def test_non_boolean_value_raises_naming_the_key(self):
        for bad in ('false', 0, 1, None, []):
            with self.assertRaises(ValueError) as ctx:
                RunConfig.from_event({'fetch_pickem': bad})
            self.assertIn('fetch_pickem', str(ctx.exception))


class CliParsingTest(unittest.TestCase):
    def test_no_flags_uses_defaults(self):
        self.assertEqual(cli.parse_args([]), RunConfig())

    def test_no_fetch_flag_turns_one_source_off(self):
        config = cli.parse_args(['--no-fetch-oddshark'])
        self.assertFalse(config.fetch_oddshark)
        self.assertTrue(config.fetch_pickem)
        self.assertTrue(config.fetch_draftkings)
        self.assertTrue(config.fetch_espnbet)

    def test_every_source_can_be_turned_off(self):
        argv = ['--no-' + key.replace('_', '-') for key in FETCH_OPTION_KEYS]
        config = cli.parse_args(argv)
        for key in FETCH_OPTION_KEYS:
            self.assertFalse(getattr(config, key), key)

    def test_positive_flag_keeps_source_on(self):
        self.assertTrue(cli.parse_args(['--fetch-pickem']).fetch_pickem)

    def test_override_csv(self):
        self.assertEqual(cli.parse_args(['--override-csv', 'out/x.csv']).override_csv_data, 'out/x.csv')

    def test_help_lists_every_flag_and_default(self):
        text = cli.build_parser().format_help()
        for key in FETCH_OPTION_KEYS:
            self.assertIn('--no-' + key.replace('_', '-'), text)
        self.assertIn('default: True', text)


if __name__ == '__main__':
    unittest.main()
