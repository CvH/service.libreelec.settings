import unittest
from unittest.mock import patch, MagicMock, ANY
import sys
import os
import time # For testing time-related features like delay

# Adjust sys.path (similar to test_os_tools.py)
ADDON_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
LIB_PATH = os.path.join(ADDON_ROOT, 'resources', 'lib')
if LIB_PATH not in sys.path:
    sys.path.insert(0, LIB_PATH)

# Attempt to import oe, with fallback for different execution environments
try:
    import oe
except ImportError as e1:
    # This might happen if 'tests' is not in the direct parent of 'resources/lib'
    # or if the environment is structured differently.
    # Try adding the parent of ADDON_ROOT if 'resources/lib' isn't found directly.
    # This is speculative and depends on the actual test environment structure.
    print(f"Initial ImportError: {e1}. Current sys.path: {sys.path}")
    # If oe.py is directly in LIB_PATH, the above should work.
    # If oe.py is in ADDON_ROOT (e.g. flat structure in some test runners)
    if ADDON_ROOT not in sys.path:
        sys.path.insert(0, ADDON_ROOT)
    try:
        import oe
    except ImportError as e2:
        print(f"Second ImportError: {e2}. Attempting relative import from 'lib' if 'oe.py' is there.")
        # This path is for when the script is run from 'tests' directory
        # and 'lib' is a sibling to 'tests', with 'oe.py' inside 'lib'.
        # This is less likely given the initial LIB_PATH, but as a fallback.
        try:
            from lib import oe # if 'oe.py' is in 'lib' and 'lib' is discoverable
        except ImportError as e3:
            print(f"Third ImportError: {e3}. Giving up.")
            raise # Re-raise the last error if all attempts fail

class TestPINStorage(unittest.TestCase):

    def setUp(self):
        # This dictionary will act as our mock settings database for each test
        self.settings_db = {}

        # Create mock functions that use self.settings_db
        # The key format should match how PINStorage generates it: f"{self.module}_{self.prefix}_{item}"
        self.mock_read_setting_func = lambda module, key: self.settings_db.get(f"{module}_{key}")
        self.mock_write_setting_func = lambda module, key, value: self.settings_db.update({f"{module}_{key}": value})

        # Apply patches
        patcher_read = patch('oe.read_setting', side_effect=self.mock_read_setting_func)
        patcher_write = patch('oe.write_setting', side_effect=self.mock_write_setting_func)

        self.mock_read_setting = patcher_read.start()
        self.mock_write_setting = patcher_write.start()
        
        self.addCleanup(patcher_read.stop)
        self.addCleanup(patcher_write.stop)

    def test_default_initialization(self):
        # settings_db is empty, so read_setting will return None for all keys
        ps = oe.PINStorage(module='test_module', prefix='test_prefix')
        self.assertFalse(ps.isEnabled(), "Should be disabled by default")
        self.assertFalse(ps.isSet(), "Should not have a PIN set by default")
        self.assertEqual(ps.numFail, 0, "numFail should be 0 by default")
        self.assertEqual(ps.timeFail, 0.0, "timeFail should be 0.0 by default")
        # Check if disable() was called due to isEnabled() != isSet()
        # In default init, isEnabled is False and isSet is False, so disable() should NOT be called.
        # disable() calls set(None), which writes 'pin' to None.
        # disable() also writes 'enable' to '0'.
        # If these were truly None to start, then no write for 'pin' or 'enable' should occur just from this equality check.
        # However, the constructor reads 'enable', 'pin', 'numFail', 'timeFail'.
        # If read_setting returns None for 'enable', it's set to '0'.
        # If read_setting returns None for 'pin', it's set to None.
        # If read_setting returns None for 'numFail', it's set to 0.
        # If read_setting returns None for 'timeFail', it's set to 0.0.
        # The critical part of disable() is that it *writes* these values.
        # Since enable is already '0' and pin is None after initial reads,
        # the condition isEnabled() != isSet() (0 != None) is false, so disable() is not called for this reason.
        
        # Let's check what was attempted to be read
        expected_reads = [
            unittest.mock.call('test_module', 'test_prefix_enable'),
            unittest.mock.call('test_module', 'test_prefix_pin'),
            unittest.mock.call('test_module', 'test_prefix_numFail'),
            unittest.mock.call('test_module', 'test_prefix_timeFail'),
        ]
        self.mock_read_setting.assert_has_calls(expected_reads, any_order=True)
        # No writes should occur if initial state is consistent (all defaults)
        self.mock_write_setting.assert_not_called()


    def test_init_with_pin_set_and_enabled(self):
        # Simulate settings already stored
        self.settings_db['test_module_test_prefix_enable'] = '1'
        # Need a valid salthash for 'pin'
        temp_ps = oe.PINStorage(module='temp', prefix='temp_init') # Helper to generate a salthash
        temp_ps.set("preexistingpin")
        self.settings_db['test_module_test_prefix_pin'] = temp_ps.salthash
        self.settings_db['test_module_test_prefix_numFail'] = '1' 
        self.settings_db['test_module_test_prefix_timeFail'] = '12345.0'

        ps = oe.PINStorage(module='test_module', prefix='test_prefix')
        self.assertTrue(ps.isEnabled())
        self.assertTrue(ps.isSet())
        self.assertEqual(ps.salthash, temp_ps.salthash)
        self.assertEqual(ps.numFail, 1)
        self.assertEqual(ps.timeFail, 12345.0)
        # No writes should occur if initial state is consistent and read correctly
        self.mock_write_setting.assert_not_called()

    def test_init_calls_disable_if_enabled_but_no_pin(self):
        self.settings_db['test_module_test_prefix_enable'] = '1'
        # test_module_test_prefix_pin is not set in settings_db, so read_setting returns None
        
        ps = oe.PINStorage(module='test_module', prefix='test_prefix')
        
        # disable() calls set(None), which writes pin=None
        # disable() also writes enable='0'
        self.mock_write_setting.assert_any_call('test_module', 'test_prefix_pin', None)
        self.mock_write_setting.assert_any_call('test_module', 'test_prefix_enable', '0')
        self.assertFalse(ps.isEnabled(), "Should be disabled as PIN was missing")
        self.assertFalse(ps.isSet(), "PIN should be cleared")

    def test_init_calls_disable_if_disabled_but_pin_is_set(self):
        self.settings_db['test_module_test_prefix_enable'] = '0'
        temp_ps = oe.PINStorage(module='temp', prefix='temp_init')
        temp_ps.set("somepin")
        self.settings_db['test_module_test_prefix_pin'] = temp_ps.salthash
        
        ps = oe.PINStorage(module='test_module', prefix='test_prefix')
        
        self.mock_write_setting.assert_any_call('test_module', 'test_prefix_pin', None)
        # enable is already '0', so it might not be written again by disable() if it checks current state first.
        # The current PINStorage.disable() writes 'enable' and calls self.set(None) unconditionally.
        self.mock_write_setting.assert_any_call('test_module', 'test_prefix_enable', '0')
        self.assertFalse(ps.isEnabled())
        self.assertFalse(ps.isSet())

    def test_enable_when_disabled_and_pin_is_set(self):
        ps = oe.PINStorage(module='test_module', prefix='test_prefix')
        ps.set("1234") # Sets the PIN, but doesn't enable
        self.assertFalse(ps.isEnabled()) # Pre-condition
        self.assertTrue(ps.isSet())    # Pre-condition
        self.mock_write_setting.reset_mock() # Reset after set()

        ps.enable()
        self.assertTrue(ps.isEnabled())
        self.mock_write_setting.assert_called_once_with('test_module', 'test_prefix_enable', '1')

    def test_enable_does_nothing_if_no_pin_is_set(self):
        ps = oe.PINStorage(module='test_module', prefix='test_prefix')
        self.assertFalse(ps.isSet()) # Pre-condition
        self.mock_write_setting.reset_mock()

        ps.enable() # Attempt to enable
        self.assertFalse(ps.isEnabled(), "Should not enable if no PIN is set")
        # enable() should not write 'enable' to '1' if no pin is set because it should return early.
        self.mock_write_setting.assert_not_called()


    def test_disable_when_enabled(self):
        # Setup initial state as enabled with a PIN
        self.settings_db['test_module_test_prefix_enable'] = '1'
        temp_ps = oe.PINStorage(module='temp', prefix='temp_disable')
        temp_ps.set("1234")
        self.settings_db['test_module_test_prefix_pin'] = temp_ps.salthash
        
        ps = oe.PINStorage(module='test_module', prefix='test_prefix')
        self.assertTrue(ps.isEnabled()) # Pre-condition
        self.assertTrue(ps.isSet())     # Pre-condition
        self.mock_write_setting.reset_mock()

        ps.disable()
        self.assertFalse(ps.isEnabled())
        self.assertFalse(ps.isSet(), "PIN should be cleared on disable")
        self.mock_write_setting.assert_any_call('test_module', 'test_prefix_enable', '0')
        self.mock_write_setting.assert_any_call('test_module', 'test_prefix_pin', None) # disable calls set(None)

    def test_set_pin_and_enable(self): # Renamed from example to be more descriptive
        ps = oe.PINStorage(module='test_module', prefix='test_prefix')
        ps.set("1234")
        self.assertTrue(ps.isSet())
        self.assertIsNotNone(ps.salthash)
        self.mock_write_setting.assert_any_call('test_module', 'test_prefix_pin', ps.salthash)
        
        # Reset mock before enabling to check only enable's write call
        self.mock_write_setting.reset_mock()
        ps.enable() 
        self.assertTrue(ps.isEnabled())
        self.mock_write_setting.assert_called_once_with('test_module', 'test_prefix_enable', '1')


    def test_set_none_clears_pin(self):
        # Setup initial state with a PIN
        temp_ps = oe.PINStorage(module='temp', prefix='temp_setnone')
        temp_ps.set("1234")
        self.settings_db['test_module_test_prefix_pin'] = temp_ps.salthash
        
        ps = oe.PINStorage(module='test_module', prefix='test_prefix')
        self.assertTrue(ps.isSet()) # Pre-condition
        self.mock_write_setting.reset_mock()

        ps.set(None)
        self.assertFalse(ps.isSet())
        self.assertIsNone(ps.salthash)
        self.mock_write_setting.assert_called_once_with('test_module', 'test_prefix_pin', None)

    def test_verify_correct_pin(self):
        ps = oe.PINStorage(module='test_module', prefix='test_prefix')
        ps.set("1234")
        self.settings_db['test_module_test_prefix_numFail'] = '1' # Simulate prior fail
        self.settings_db['test_module_test_prefix_timeFail'] = '100.0'
        ps.numFail = 1 # Ensure internal state matches for test
        ps.timeFail = 100.0
        self.mock_write_setting.reset_mock() 

        self.assertTrue(ps.verify("1234"))
        self.assertEqual(ps.numFail, 0, "numFail should be reset on correct verification")
        self.assertEqual(ps.timeFail, 0.0, "timeFail should be reset on correct verification")
        self.mock_write_setting.assert_any_call('test_module', 'test_prefix_numFail', 0)
        self.mock_write_setting.assert_any_call('test_module', 'test_prefix_timeFail', 0.0)


    def test_verify_incorrect_pin_triggers_fail(self):
        ps = oe.PINStorage(module='test_module', prefix='test_prefix')
        ps.set("1234")
        self.mock_write_setting.reset_mock() 

        self.assertFalse(ps.verify("wrong"))
        self.assertEqual(ps.numFail, 1)
        # timeFail is set to time.time(), so we check with ANY
        self.mock_write_setting.assert_any_call('test_module', 'test_prefix_numFail', 1)
        self.mock_write_setting.assert_any_call('test_module', 'test_prefix_timeFail', ANY)

    def test_success_resets_fail_counts(self):
        ps = oe.PINStorage(module='test_module', prefix='test_prefix')
        # Simulate prior fails
        self.settings_db['test_module_test_prefix_numFail'] = '2'
        self.settings_db['test_module_test_prefix_timeFail'] = '12345.0'
        ps.numFail = 2
        ps.timeFail = 12345.0
        self.mock_write_setting.reset_mock()

        ps.success()
        self.assertEqual(ps.numFail, 0)
        self.assertEqual(ps.timeFail, 0.0)
        self.mock_write_setting.assert_any_call('test_module', 'test_prefix_numFail', 0)
        self.mock_write_setting.assert_any_call('test_module', 'test_prefix_timeFail', 0.0)
    
    def test_success_does_not_write_if_already_clear(self):
        ps = oe.PINStorage(module='test_module', prefix='test_prefix')
        # numFail and timeFail are already 0
        self.mock_write_setting.reset_mock()
        ps.success()
        self.mock_write_setting.assert_not_called()


    @patch('time.time') 
    def test_max_attempts_and_delay(self, mock_time):
        mock_time.return_value = 1000.0 # Initial time
        ps = oe.PINStorage(module='test_module', prefix='test_prefix', maxAttempts=2, delay=100)
        ps.set("1234")
        self.mock_write_setting.reset_mock()

        # Attempt 1 (incorrect)
        self.assertFalse(ps.verify("0000"), "First incorrect PIN should fail verification")
        self.assertEqual(ps.numFail, 1, "numFail should be 1 after first fail")
        self.assertEqual(ps.timeFail, 1000.0, "timeFail should be set to current time")
        self.assertFalse(ps.isDelayed(), "Should not be delayed after 1st fail")
        self.mock_write_setting.assert_any_call('test_module', 'test_prefix_numFail', 1)
        self.mock_write_setting.assert_any_call('test_module', 'test_prefix_timeFail', 1000.0)
        self.mock_write_setting.reset_mock()


        # Attempt 2 (incorrect) - maxAttempts reached
        mock_time.return_value = 1001.0 # Time moves forward a bit
        self.assertFalse(ps.verify("0001"), "Second incorrect PIN should fail verification") 
        self.assertEqual(ps.numFail, 2, "numFail should be 2 after second fail")
        self.assertEqual(ps.timeFail, 1001.0)
        self.assertTrue(ps.isDelayed(), "Should be delayed after reaching max attempts (2)")
        self.mock_write_setting.assert_any_call('test_module', 'test_prefix_numFail', 2)
        self.mock_write_setting.assert_any_call('test_module', 'test_prefix_timeFail', 1001.0)
        self.mock_write_setting.reset_mock()

        # Check within delay period
        mock_time.return_value = 1050.0 # Current time = 1050.0. timeFail = 1001.0. delay = 100.
                                      # 1050.0 - 1001.0 = 49.0. 49.0 < 100. delayRemaining = 100 - 49 = 51.
        self.assertTrue(ps.isDelayed(), "Should still be delayed within the delay period")
        self.assertEqual(ps.delayRemaining(), 51.0) # 100 - (1050 - 1001)
        self.mock_write_setting.assert_not_called() # No writes during isDelayed check

        # Check after delay period
        mock_time.return_value = 1102.0 # Current time = 1102.0. timeFail = 1001.0. delay = 100.
                                      # 1102.0 - 1001.0 = 101.0. 101.0 > 100. Delay passed.
        self.assertFalse(ps.isDelayed(), "Delay should have passed, fail counts should be reset") 
        self.assertEqual(ps.numFail, 0, "numFail should be reset after delay passes")
        self.assertEqual(ps.timeFail, 0.0, "timeFail should be reset after delay passes")
        # success() is called by isDelayed() when delay has passed
        self.mock_write_setting.assert_any_call('test_module', 'test_prefix_numFail', 0)
        self.mock_write_setting.assert_any_call('test_module', 'test_prefix_timeFail', 0.0)

    def test_isdelayed_no_attempts_made(self):
        ps = oe.PINStorage(module='test_module', prefix='test_prefix', maxAttempts=2, delay=100)
        ps.set("1234")
        self.assertFalse(ps.isDelayed())

    def test_isdelayed_attempts_not_maxed(self):
        ps = oe.PINStorage(module='test_module', prefix='test_prefix', maxAttempts=3, delay=100)
        ps.set("1234")
        ps.verify("wrong1") # numFail = 1
        self.assertFalse(ps.isDelayed())
        ps.verify("wrong2") # numFail = 2
        self.assertFalse(ps.isDelayed())


# Standard unittest runner
if __name__ == '__main__':
    unittest.main()

class TestOeUtils(unittest.TestCase):
    def test_split_dialog_text_short(self):
        text = "This is a short text."
        expected = ["This is a short text.", "", ""]
        self.assertEqual(oe.split_dialog_text(text), expected)

    def test_split_dialog_text_empty(self):
        text = ""
        expected = ["", "", ""]
        self.assertEqual(oe.split_dialog_text(text), expected)

    def test_split_dialog_text_exact_60_chars_no_space(self):
        text = "a" * 60
        expected = [text, "", ""]
        self.assertEqual(oe.split_dialog_text(text), expected)

    def test_split_dialog_text_exact_60_chars_with_space_at_end(self):
        text = ("a" * 59) + " " # Length 60
        expected = [text, "", ""] # The space is a non-word char, so it's included.
        self.assertEqual(oe.split_dialog_text(text), expected)

    def test_split_dialog_text_one_split_at_word_boundary(self):
        # Text is 70 chars. Split should happen before/at 60.
        # "This is a longer text that will definitely exceed the sixty " (60 chars, ends with space)
        # "characters for a single line example." (rest of the string)
        text = "This is a longer text that will definitely exceed the sixty characters for a single line example."
        line1 = "This is a longer text that will definitely exceed the sixty " # 60 chars
        line2 = "characters for a single line example."
        expected = [line1, line2, ""]
        self.assertEqual(oe.split_dialog_text(text), expected)
        
    def test_split_dialog_text_one_split_no_word_boundary_at_60(self):
        # Text is 70 'a's. Should split at 60th 'a'.
        text = "a" * 70
        line1 = "a" * 60
        line2 = "a" * 10
        expected = [line1, line2, ""]
        self.assertEqual(oe.split_dialog_text(text), expected)

    def test_split_dialog_text_two_splits(self):
        # Total length 150 chars.
        # Line 1: 60 chars. Line 2: 60 chars. Line 3: 30 chars.
        text = "This is line one, it is exactly sixty characters long, abcdef." + \
               "This is line two, it is also exactly sixty characters long, ghi." + \
               "This is line three, shorter."
        line1 = "This is line one, it is exactly sixty characters long, abcdef."
        line2 = "This is line two, it is also exactly sixty characters long, ghi."
        line3 = "This is line three, shorter."
        expected = [line1, line2, line3]
        self.assertEqual(oe.split_dialog_text(text), expected)

    def test_split_dialog_text_max_three_lines(self):
        # Total length 200 chars. Should only return first 3 "lines" based on split.
        text = ("a" * 60) + ("b" * 60) + ("c" * 60) + ("d" * 20)
        line1 = "a" * 60
        line2 = "b" * 60
        # The third line will take up to 60 of the remaining text.
        line3 = "c" * 60 
        expected = [line1, line2, line3]
        self.assertEqual(oe.split_dialog_text(text), expected)

    def test_split_dialog_text_with_internal_short_non_word_sequences(self):
        # Test if it correctly handles short non-word sequences like " - "
        text = "This is a test - it has a dash. This should not break mid-dash if possible." #len=76
        # Expected: "This is a test - it has a dash. This should not break " (59)
        #           "mid-dash if possible." (25)
        line1 = "This is a test - it has a dash. This should not break "
        line2 = "mid-dash if possible."
        expected = [line1, line2, ""]
        self.assertEqual(oe.split_dialog_text(text), expected)

    def test_split_dialog_text_with_existing_newlines(self):
        # The function uses re.findall on the whole text. The '.' in regex
        # does not match newlines by default. So, newlines are treated like any other character
        # if the regex `\W` matches them or if they are part of the 60 chars.
        # However, the problem description implies the function should split a single block of text.
        # Let's assume input text does not contain newlines intended for formatting.
        # If it did, they would likely be part of the content and could be part of the split lines.
        # The current implementation of split_dialog_text does not pre-process newlines.
        # `re.findall('.{1,60}(?:\W|$)', text)`
        # If text = "Line one\nLine two", and "Line one\n" is <= 60, it will be one part.
        # If text = "L"*58 + "\n" + "L"*5, then "L"*58 + "\n" is first part.
        text_with_newline = "This is the first line and it's quite long, almost sixty chars.\nThis is the second line after a newline."
        # Expected: The \n is a \W.
        # "This is the first line and it's quite long, almost sixty chars.\n" (60 chars)
        # "This is the second line after a newline."
        line1 = "This is the first line and it's quite long, almost sixty chars.\n"
        line2 = "This is the second line after a newline."
        expected = [line1, line2, ""]
        self.assertEqual(oe.split_dialog_text(text_with_newline), expected)

        text_newline_at_50 = ("a" * 50) + "\n" + ("b" * 20)
        # "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\n" (51 chars)
        # "bbbbbbbbbbbbbbbbbbbb" (20 chars)
        expected_newline_at_50 = [("a" * 50) + "\n", "b" * 20, ""]
        self.assertEqual(oe.split_dialog_text(text_newline_at_50), expected_newline_at_50)
