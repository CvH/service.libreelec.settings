import unittest
from unittest.mock import patch, mock_open
import sys
import os

# Adjust sys.path to allow importing from resources.lib
# This assumes 'tests' is in the root, and 'resources/lib' is also in the root.
ADDON_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
LIB_PATH = os.path.join(ADDON_ROOT, 'resources', 'lib')
if LIB_PATH not in sys.path:
    sys.path.insert(0, LIB_PATH)

# Now import the module to test
try:
    import os_tools 
except ImportError:
    # Fallback if the above path manipulation isn't perfect during subtask execution
    # This is a bit of a hack for the subtask environment; locally, you'd ensure PYTHONPATH.
    # Adding current dir to path to see if os_tools is discoverable if it was copied to a flat structure
    sys.path.insert(0, os.path.join(ADDON_ROOT)) # Try adding root if lib isn't found
    # Attempt to find resources.lib if it's a sibling to tests
    # This is tricky; the worker environment might place files differently.
    # The primary goal is for the worker to get the import to succeed.
    if os.path.exists(os.path.join(ADDON_ROOT, 'resources', 'lib', 'os_tools.py')):
         # This path should have been added already by LIB_PATH
         pass
    else: # If script is run from within tests dir, and resources is sibling
        # This is another attempt based on common local structures
        potential_lib_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'resources', 'lib'))
        if potential_lib_path not in sys.path:
             sys.path.insert(0, potential_lib_path)
    import os_tools


class TestOsTools(unittest.TestCase):

    def test_read_shell_setting_reads_first_line(self):
        mock_content = "FIRST_LINE_VALUE\nSECOND_LINE"
        # Patch 'open' within the 'os_tools' module's scope
        with patch('os_tools.open', mock_open(read_data=mock_content), create=True):
            # Patch 'os.path.isfile' to always return True for this test
            with patch('os_tools.os.path.isfile', return_value=True):
                result = os_tools.read_shell_setting('dummy/path/file.conf')
                self.assertEqual(result, "FIRST_LINE_VALUE")

    def test_read_shell_setting_returns_default_if_file_not_found(self):
        with patch('os_tools.os.path.isfile', return_value=False):
            result = os_tools.read_shell_setting('dummy/path/nonexistent.conf', default="DEFAULT_VAL")
            self.assertEqual(result, "DEFAULT_VAL")
            
    def test_read_shell_setting_ignores_comments(self):
        mock_content = "# This is a comment\nACTUAL_VALUE"
        with patch('os_tools.open', mock_open(read_data=mock_content), create=True):
            with patch('os_tools.os.path.isfile', return_value=True):
                result = os_tools.read_shell_setting('dummy/path/file.conf')
                self.assertEqual(result, "ACTUAL_VALUE")

    def test_read_shell_setting_default_for_comment_only_file(self):
        mock_content = "# This is a comment\n# Another comment"
        with patch('os_tools.open', mock_open(read_data=mock_content), create=True):
            with patch('os_tools.os.path.isfile', return_value=True):
                result = os_tools.read_shell_setting('dummy/path/file.conf', default="DEFAULT_VAL")
                self.assertEqual(result, "DEFAULT_VAL")

    # New tests for read_shell_settings (plural)

    def test_read_shell_settings_parses_valid_file(self):
        mock_content = 'VAR1="value1"\nVAR2="value with space"\n#COMMENT\nVAR3=unquoted\nVAR4=\nVAR5="quoted" # inline comment'
        expected_dict = {"VAR1": "value1", "VAR2": "value with space", "VAR3": "unquoted", "VAR4": "", "VAR5": "quoted"}
        with patch('os_tools.open', mock_open(read_data=mock_content), create=True):
            with patch('os_tools.os.path.isfile', return_value=True):
                result = os_tools.read_shell_settings('dummy/path/settings.conf')
                self.assertEqual(result, expected_dict)

    def test_read_shell_settings_handles_empty_file(self):
        mock_content = ""
        expected_dict = {}
        with patch('os_tools.open', mock_open(read_data=mock_content), create=True):
            with patch('os_tools.os.path.isfile', return_value=True):
                result = os_tools.read_shell_settings('dummy/path/empty.conf')
                self.assertEqual(result, expected_dict)

    def test_read_shell_settings_handles_comments_and_blank_lines(self):
        mock_content = '# Full comment line\n\nVAR_A="alpha"\n  # Indented comment\nVAR_B="beta"'
        expected_dict = {"VAR_A": "alpha", "VAR_B": "beta"}
        with patch('os_tools.open', mock_open(read_data=mock_content), create=True):
            with patch('os_tools.os.path.isfile', return_value=True):
                result = os_tools.read_shell_settings('dummy/path/commented.conf')
                self.assertEqual(result, expected_dict)

    def test_read_shell_settings_skips_invalid_lines(self):
        mock_content = 'VALID_VAR="valid"\njust_a_string\nANOTHER_VALID="next"\n=startswithseparator'
        expected_dict = {"VALID_VAR": "valid", "ANOTHER_VALID": "next"}
        with patch('os_tools.open', mock_open(read_data=mock_content), create=True):
            with patch('os_tools.os.path.isfile', return_value=True):
                result = os_tools.read_shell_settings('dummy/path/mixed.conf')
                self.assertEqual(result, expected_dict)

    def test_read_shell_settings_handles_various_quoting_and_spaces(self):
        mock_content = 'KEY1="val1"\nKEY2=\'val2\'\nKEY3=val3\nKEY4="  leading and trailing spaces  "\nKEY5=\'  val with spaces  \'\nKEY6=  val_unquoted_spaces  '
        expected_dict = {
            "KEY1": "val1",
            "KEY2": "val2", # Assuming it handles single quotes as well, or removes them. The original code removes " and '.
            "KEY3": "val3",
            "KEY4": "  leading and trailing spaces  ", # Quotes preserve spaces
            "KEY5": "  val with spaces  ",
            "KEY6": "val_unquoted_spaces" # Unquoted values are stripped
        }
        with patch('os_tools.open', mock_open(read_data=mock_content), create=True):
            with patch('os_tools.os.path.isfile', return_value=True):
                result = os_tools.read_shell_settings('dummy/path/quoting.conf')
                self.assertEqual(result, expected_dict)
    
    def test_read_shell_settings_export_keyword(self):
        mock_content = 'export EXPORTED_VAR="exported value"\nNORMAL_VAR="normal value"'
        # The function should strip 'export ' prefix from the key if present
        expected_dict = {"EXPORTED_VAR": "exported value", "NORMAL_VAR": "normal value"}
        with patch('os_tools.open', mock_open(read_data=mock_content), create=True):
            with patch('os_tools.os.path.isfile', return_value=True):
                result = os_tools.read_shell_settings('dummy/path/export.conf')
                self.assertEqual(result, expected_dict)


    def test_read_shell_settings_file_not_found_returns_default(self):
        with patch('os_tools.os.path.isfile', return_value=False):
            default_val = {"DEFAULT_KEY": "default_value"}
            result = os_tools.read_shell_settings('dummy/path/nonexistent.conf', defaults=default_val)
            self.assertEqual(result, default_val)
        
    def test_read_shell_settings_file_not_found_returns_empty_dict_if_no_default(self):
        with patch('os_tools.os.path.isfile', return_value=False):
            result = os_tools.read_shell_settings('dummy/path/nonexistent.conf')
            self.assertEqual(result, {})


if __name__ == '__main__':
    unittest.main()
