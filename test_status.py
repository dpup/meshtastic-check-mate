import unittest
import json
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, mock_open
from status import StatusManager, Status


class TestStatusManager(unittest.TestCase):
    """Test case for the StatusManager class."""

    def setUp(self):
        """Set up a temporary directory for test status files."""
        self.temp_dir = tempfile.mkdtemp()
        self.status_manager = StatusManager(self.temp_dir)

    def tearDown(self):
        """Clean up the temporary directory after tests."""
        for file in Path(self.temp_dir).glob('*'):
            file.unlink()
        os.rmdir(self.temp_dir)

    def test_init_with_custom_dir(self):
        """Test initialization with a custom directory."""
        manager = StatusManager(self.temp_dir)
        self.assertEqual(str(manager.base_dir), self.temp_dir)
        self.assertEqual(str(manager.status_file), os.path.join(self.temp_dir, 'status.json'))
        
    @patch('pathlib.Path.mkdir', side_effect=PermissionError("Test permission error"))
    def test_init_permission_error(self, mock_mkdir):
        """Test initialization with permission error."""
        with self.assertRaises(PermissionError):
            StatusManager(self.temp_dir)

    @patch('status.platform.system')
    @patch('pathlib.Path.mkdir')
    def test_init_with_default_dir_darwin(self, mock_mkdir, mock_system):
        """Test initialization with default directory on macOS."""
        mock_system.return_value = 'Darwin'
        with patch('status.Path.home') as mock_home:
            home_dir = Path('/Users/testuser')
            mock_home.return_value = home_dir
            # Completely mock the DEFAULT_STATUS_PATHS dictionary
            with patch('status.DEFAULT_STATUS_PATHS', {
                'Darwin': home_dir / 'Library' / 'Application Support' / 'check-mate',
                'Linux': home_dir / '.local' / 'share' / 'check-mate',
                'Windows': home_dir / 'AppData' / 'Local' / 'check-mate',
            }):
                manager = StatusManager()
                expected_dir = home_dir / 'Library' / 'Application Support' / 'check-mate'
                self.assertEqual(manager.base_dir, expected_dir)
                mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)

    @patch('status.platform.system')
    @patch('pathlib.Path.mkdir')
    def test_init_with_default_dir_linux(self, mock_mkdir, mock_system):
        """Test initialization with default directory on Linux."""
        mock_system.return_value = 'Linux'
        with patch('status.Path.home') as mock_home:
            home_dir = Path('/home/testuser')
            mock_home.return_value = home_dir
            # Completely mock the DEFAULT_STATUS_PATHS dictionary
            with patch('status.DEFAULT_STATUS_PATHS', {
                'Darwin': home_dir / 'Library' / 'Application Support' / 'check-mate',
                'Linux': home_dir / '.local' / 'share' / 'check-mate',
                'Windows': home_dir / 'AppData' / 'Local' / 'check-mate',
            }):
                manager = StatusManager()
                expected_dir = home_dir / '.local' / 'share' / 'check-mate'
                self.assertEqual(manager.base_dir, expected_dir)
                mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)

    @patch('status.platform.system')
    @patch('pathlib.Path.mkdir')
    def test_init_with_default_dir_windows(self, mock_mkdir, mock_system):
        """Test initialization with default directory on Windows."""
        mock_system.return_value = 'Windows'
        with patch('status.Path.home') as mock_home:
            home_dir = Path('C:/Users/testuser')
            mock_home.return_value = home_dir
            # Completely mock the DEFAULT_STATUS_PATHS dictionary
            with patch('status.DEFAULT_STATUS_PATHS', {
                'Darwin': home_dir / 'Library' / 'Application Support' / 'check-mate',
                'Linux': home_dir / '.local' / 'share' / 'check-mate',
                'Windows': home_dir / 'AppData' / 'Local' / 'check-mate',
            }):
                manager = StatusManager()
                expected_dir = home_dir / 'AppData' / 'Local' / 'check-mate'
                self.assertEqual(manager.base_dir, expected_dir)
                mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)

    @patch('status.platform.system')
    @patch('pathlib.Path.mkdir')
    def test_init_with_empty_string_dir(self, mock_mkdir, mock_system):
        """Test initialization with an empty string directory."""
        mock_system.return_value = 'Linux'
        with patch('status.Path.home') as mock_home:
            home_dir = Path('/home/testuser')
            mock_home.return_value = home_dir
            # Completely mock the DEFAULT_STATUS_PATHS dictionary
            with patch('status.DEFAULT_STATUS_PATHS', {
                'Darwin': home_dir / 'Library' / 'Application Support' / 'check-mate',
                'Linux': home_dir / '.local' / 'share' / 'check-mate',
                'Windows': home_dir / 'AppData' / 'Local' / 'check-mate',
            }):
                manager = StatusManager("")
                expected_dir = home_dir / '.local' / 'share' / 'check-mate'
                self.assertEqual(manager.base_dir, expected_dir)
                mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)

    @patch('json.dump')
    @patch('builtins.open', new_callable=mock_open)
    def test_write_status(self, mock_file, mock_json_dump):
        """Test writing status to file."""
        status_data = {
            "status": Status.ACTIVE,
            "start_time": 123456789.0,
            "update_time": 123456789.0,
            "user_count": 5
        }
        self.status_manager.write_status(status_data)
        mock_file.assert_called_once_with(self.status_manager.status_file, 'w')
        mock_json_dump.assert_called_once_with(status_data, mock_file())

    @patch('builtins.open', side_effect=IOError("Test IO Error"))
    def test_write_status_io_error(self, mock_file):
        """Test error handling when writing status file fails."""
        status_data = {"status": Status.ACTIVE}
        with self.assertRaises(IOError):
            self.status_manager.write_status(status_data)

    @patch('builtins.open', side_effect=PermissionError("Test Permission Error"))
    def test_write_status_permission_error(self, mock_file):
        """Test error handling when writing status file lacks permissions."""
        status_data = {"status": Status.ACTIVE}
        with self.assertRaises(PermissionError):
            self.status_manager.write_status(status_data)

    @patch('pathlib.Path.exists')
    @patch('builtins.open', new_callable=mock_open, read_data='{"status": "active"}')
    def test_read_status(self, mock_file, mock_exists):
        """Test reading status from file."""
        mock_exists.return_value = True
        status = self.status_manager.read_status()
        self.assertEqual(status, {"status": "active"})
        mock_file.assert_called_once_with(self.status_manager.status_file, 'r')

    @patch('pathlib.Path.exists')
    def test_read_status_file_not_found(self, mock_exists):
        """Test handling when status file doesn't exist."""
        mock_exists.return_value = False
        status = self.status_manager.read_status()
        self.assertEqual(status, {"status": Status.UNKNOWN})

    @patch('pathlib.Path.exists')
    @patch('builtins.open', side_effect=IOError("Test IO Error"))
    def test_read_status_io_error(self, mock_file, mock_exists):
        """Test error handling when reading status file fails."""
        mock_exists.return_value = True
        status = self.status_manager.read_status()
        self.assertEqual(status, {"status": Status.UNKNOWN})

    @patch('pathlib.Path.exists')
    @patch('builtins.open', new_callable=mock_open, read_data='invalid json')
    def test_read_status_json_error(self, mock_file, mock_exists):
        """Test error handling with invalid JSON in status file."""
        mock_exists.return_value = True
        with self.assertRaises(json.JSONDecodeError):
            self.status_manager.read_status()

    @patch('builtins.print')
    def test_dump_active(self, mock_print):
        """Test dump method with active status."""
        with patch.object(StatusManager, 'read_status') as mock_read:
            mock_read.return_value = {"status": Status.ACTIVE}
            exit_code = self.status_manager.dump()
            self.assertEqual(exit_code, 0)
            mock_print.assert_called_once_with(json.dumps({"status": Status.ACTIVE}))

    @patch('builtins.print')
    def test_dump_inactive(self, mock_print):
        """Test dump method with inactive status."""
        with patch.object(StatusManager, 'read_status') as mock_read:
            mock_read.return_value = {"status": Status.SHUTDOWN}
            exit_code = self.status_manager.dump()
            self.assertEqual(exit_code, 1)
            mock_print.assert_called_once_with(json.dumps({"status": Status.SHUTDOWN}))


if __name__ == "__main__":
    unittest.main()