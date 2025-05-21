from resources.lib import hostname
import unittest
from unittest import mock
import sys
import os

# Add the directory containing the modules to sys.path
sys.path.insert(0, os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..')))

mock_config_module = mock.MagicMock()
mock_config_module.OS_RELEASE = {'NAME': 'TestOS'}
mock_config_module.HOSTNAME = '/test/hostname_mock_path'
sys.modules['config'] = mock_config_module

mock_log_module = mock.MagicMock()
sys.modules['log'] = mock_log_module


class TestHostname(unittest.TestCase):
    def setUp(self):
        self.mock_hostname_file = mock_config_module.HOSTNAME
        self.mock_os_release_name = mock_config_module.OS_RELEASE['NAME']

        mock_config_module.reset_mock()
        mock_config_module.OS_RELEASE = {
            'NAME': 'TestOS'}  # Re-assign after reset
        mock_config_module.HOSTNAME = '/test/hostname_mock_path'  # Re-assign after reset
        mock_log_module.reset_mock()

    def tearDown(self):
        mock.patch.stopall()

    @mock.patch('os_tools.read_shell_setting')
    def test_get_hostname(self, mock_read_shell_setting_on_os_tools_mock):
        expected_hostname = "test-host"
        mock_read_shell_setting_on_os_tools_mock.return_value = expected_hostname
        actual_hostname = hostname.get_hostname()
        mock_read_shell_setting_on_os_tools_mock.assert_called_once_with(
            self.mock_hostname_file,
            self.mock_os_release_name
        )
        self.assertEqual(actual_hostname, expected_hostname)

    @mock.patch('resources.lib.hostname.get_hostname')
    @mock.patch('builtins.open', new_callable=mock.mock_open)
    @mock.patch('os_tools.execute')
    @mock.patch('os.path.isfile')
    def test_set_hostname_different_no_file(self, mock_isfile, mock_os_tools_execute, mock_open_file, mock_get_current_hostname):
        mock_get_current_hostname.return_value = "old-hostname"
        # os.path.isfile is NOT called if hostnames are different due to short-circuit 'or'
        mock_isfile.return_value = False  # Set its behavior anyway for completeness
        new_hostname_val = "new-hostname"

        result = hostname.set_hostname(new_hostname_val)
        self.assertTrue(result)

        mock_isfile.assert_not_called()  # Hostnames are different, so isfile is not called
        mock_open_file.assert_called_once_with(
            self.mock_hostname_file, mode='w', encoding='utf-8')
        mock_open_file().write.assert_has_calls(
            [mock.call(f'{new_hostname_val}\n')])

        expected_execute_calls = [
            mock.call('systemctl restart network-base'),
            mock.call('systemctl try-restart avahi-daemon wsdd2')
        ]
        mock_os_tools_execute.assert_has_calls(
            expected_execute_calls, any_order=False)

    @mock.patch('resources.lib.hostname.get_hostname')
    @mock.patch('builtins.open', new_callable=mock.mock_open)
    @mock.patch('os_tools.execute')
    @mock.patch('os.path.isfile')
    def test_set_hostname_different_file_exists(self, mock_isfile, mock_os_tools_execute, mock_open_file, mock_get_current_hostname):
        mock_get_current_hostname.return_value = "old-hostname"
        # os.path.isfile is NOT called if hostnames are different
        mock_isfile.return_value = True  # Set its behavior anyway
        new_hostname_val = "new-hostname"

        result = hostname.set_hostname(new_hostname_val)
        self.assertTrue(result)

        mock_isfile.assert_not_called()  # Hostnames are different, so isfile is not called
        mock_open_file.assert_called_once_with(
            self.mock_hostname_file, mode='w', encoding='utf-8')
        mock_open_file().write.assert_has_calls(
            [mock.call(f'{new_hostname_val}\n')])
        expected_execute_calls = [
            mock.call('systemctl restart network-base'),
            mock.call('systemctl try-restart avahi-daemon wsdd2')
        ]
        mock_os_tools_execute.assert_has_calls(
            expected_execute_calls, any_order=False)

    @mock.patch('resources.lib.hostname.get_hostname')
    @mock.patch('builtins.open', new_callable=mock.mock_open)
    @mock.patch('os_tools.execute')
    @mock.patch('os.path.isfile')
    def test_set_hostname_same_file_exists(self, mock_isfile, mock_os_tools_execute, mock_open_file, mock_get_current_hostname):
        current_hostname_val = "current-hostname"
        mock_get_current_hostname.return_value = current_hostname_val
        mock_isfile.return_value = True  # This will be checked

        result = hostname.set_hostname(current_hostname_val)
        self.assertFalse(result)

        mock_isfile.assert_called_once_with(
            self.mock_hostname_file)  # isfile IS called
        mock_open_file.assert_not_called()
        mock_os_tools_execute.assert_not_called()

    @mock.patch('resources.lib.hostname.get_hostname')
    @mock.patch('builtins.open', new_callable=mock.mock_open)
    @mock.patch('os_tools.execute')
    @mock.patch('os.path.isfile')
    def test_set_hostname_same_no_file(self, mock_isfile, mock_os_tools_execute, mock_open_file, mock_get_current_hostname):
        current_hostname_val = "current-hostname"
        mock_get_current_hostname.return_value = current_hostname_val
        mock_isfile.return_value = False  # This will be checked

        result = hostname.set_hostname(current_hostname_val)
        self.assertTrue(result)

        mock_isfile.assert_called_once_with(
            self.mock_hostname_file)  # isfile IS called
        mock_open_file.assert_called_once_with(
            self.mock_hostname_file, mode='w', encoding='utf-8')
        mock_open_file().write.assert_has_calls(
            [mock.call(f'{current_hostname_val}\n')])
        expected_execute_calls = [
            mock.call('systemctl restart network-base'),
            mock.call('systemctl try-restart avahi-daemon wsdd2')
        ]
        mock_os_tools_execute.assert_has_calls(
            expected_execute_calls, any_order=False)


if __name__ == '__main__':
    unittest.main()
