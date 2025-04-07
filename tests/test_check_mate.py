import unittest
from unittest.mock import patch, MagicMock
import requests
from checkmate.main import CheckMate
from checkmate.status import StatusManager, Status


class TestCheckMate(unittest.TestCase):
    """Test case for the CheckMate class."""

    def setUp(self):
        """Set up test fixtures for CheckMate tests."""
        self.mock_status_manager = MagicMock(spec=StatusManager)
        self.host = "test.local"
        self.location = "Test Location"
        self.health_check_url = "https://example.com/healthcheck"
        self.checkmate = CheckMate(
            self.mock_status_manager, 
            self.host, 
            self.location, 
            self.health_check_url
        )

    def test_init(self):
        """Test initialization of CheckMate instance."""
        self.assertEqual(self.checkmate.host, self.host)
        self.assertEqual(self.checkmate.location, self.location)
        self.assertEqual(self.checkmate.health_check_url, self.health_check_url)
        self.assertEqual(self.checkmate.users, {})
        self.assertFalse(self.checkmate.connected)
        self.assertIsNone(self.checkmate.iface)
        self.assertIsNone(self.checkmate.last_health_check)
        self.assertEqual(self.checkmate.status["status"], "starting")

    def test_init_default_location(self):
        """Test initialization with default location."""
        checkmate = CheckMate(self.mock_status_manager, self.host)
        self.assertEqual(checkmate.location, "Unknown Location")

    def test_set_status(self):
        """Test setting status updates internal state and calls status manager."""
        self.checkmate.set_status(Status.ACTIVE, ping=True)
        self.assertEqual(self.checkmate.status["status"], Status.ACTIVE)
        self.assertIn("last_device_ping", self.checkmate.status)
        self.mock_status_manager.write_status.assert_called_once_with(self.checkmate.status)

    def test_set_status_no_ping(self):
        """Test setting status without ping doesn't update ping timestamp."""
        self.checkmate.set_status(Status.ACTIVE, ping=False)
        self.assertEqual(self.checkmate.status["status"], Status.ACTIVE)
        self.assertNotIn("last_device_ping", self.checkmate.status)

    @patch('checkmate.main.requests.head')
    def test_report_health_success(self, mock_head):
        """Test successful health check report."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_head.return_value = mock_response

        self.checkmate.report_health()
        mock_head.assert_called_once_with(self.health_check_url, timeout=10)
        self.assertIsNotNone(self.checkmate.last_health_check)

    @patch('checkmate.main.requests.head')
    def test_report_health_failure(self, mock_head):
        """Test failed health check report."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_head.return_value = mock_response

        self.checkmate.report_health()
        mock_head.assert_called_once_with(self.health_check_url, timeout=10)
        self.assertIsNotNone(self.checkmate.last_health_check)

    @patch('checkmate.main.requests.head', side_effect=requests.RequestException("Test exception"))
    def test_report_health_exception(self, mock_head):
        """Test health check report with exception."""
        self.checkmate.report_health()
        mock_head.assert_called_once_with(self.health_check_url, timeout=10)
        self.assertIsNotNone(self.checkmate.last_health_check)

    @patch('checkmate.main.time.time')
    def test_report_health_throttling(self, mock_time):
        """Test health check throttling."""
        # Set up a recent health check
        mock_time.return_value = 1000.0
        self.checkmate.last_health_check = 999.0  # Just 1 second ago
        
        # Health check should be skipped
        self.checkmate.report_health()
        # No requests were made due to throttling
        self.assertEqual(self.checkmate.last_health_check, 999.0)

    def test_report_health_no_url(self):
        """Test health check skipped when no URL is configured."""
        checkmate = CheckMate(self.mock_status_manager, self.host)
        checkmate.health_check_url = None
        
        # Should do nothing and return immediately
        checkmate.report_health()
        self.assertIsNone(checkmate.last_health_check)

    def test_on_connect(self):
        """Test connection handler updates status and processes nodes."""
        mock_interface = MagicMock()
        mock_interface.nodes = {
            "node1": {"user": {"id": "user1", "shortName": "User One"}},
            "node2": {"user": {"id": "user2", "shortName": "User Two"}}
        }
        
        self.checkmate.on_connect(mock_interface)
        
        self.assertEqual(self.checkmate.users, {
            "user1": "User One",
            "user2": "User Two"
        })
        self.mock_status_manager.write_status.assert_called_with(self.checkmate.status)
        self.assertEqual(self.checkmate.status["status"], Status.CONNECTED)

    def test_on_connect_no_nodes(self):
        """Test connection handler with no nodes."""
        mock_interface = MagicMock()
        mock_interface.nodes = {}
        
        self.checkmate.on_connect(mock_interface)
        
        self.assertEqual(self.checkmate.users, {})
        self.mock_status_manager.write_status.assert_called_with(self.checkmate.status)
        self.assertEqual(self.checkmate.status["status"], Status.CONNECTED)

    def test_on_disconnect(self):
        """Test disconnect handler updates status."""
        mock_interface = MagicMock()
        self.checkmate.connected = True
        
        self.checkmate.on_disconnect(mock_interface)
        
        self.assertFalse(self.checkmate.connected)
        self.mock_status_manager.write_status.assert_called_with(self.checkmate.status)
        self.assertEqual(self.checkmate.status["status"], Status.DISCONNECTED)

    def test_update_user(self):
        """Test updating user information."""
        user_info = {
            "id": "user123",
            "shortName": "Test User"
        }
        
        self.checkmate.update_user(user_info)
        
        self.assertEqual(self.checkmate.users["user123"], "Test User")

    def test_update_user_missing_fields(self):
        """Test updating user with missing fields."""
        user_info = {
            "id": "user123"
            # Missing shortName
        }
        
        # Should not update users dictionary
        self.checkmate.update_user(user_info)
        self.assertEqual(self.checkmate.users, {})

    @patch('checkmate.main.time.sleep', side_effect=KeyboardInterrupt)
    def test_start_keyboard_interrupt(self, mock_sleep):
        """Test graceful shutdown on keyboard interrupt."""
        result = self.checkmate.start()
        
        self.assertEqual(result, 0)
        self.mock_status_manager.write_status.assert_called_with(self.checkmate.status)
        self.assertEqual(self.checkmate.status["status"], Status.SHUTDOWN)

    @patch('checkmate.main.time.sleep')
    def test_keyboard_interrupt_during_loop(self, mock_sleep):
        """Test handling keyboard interrupt during the main loop."""
        # First sleep is fine, second raises KeyboardInterrupt
        mock_sleep.side_effect = [None, KeyboardInterrupt]
        
        # Mock interface to avoid actual connection
        self.checkmate.iface = MagicMock()
        self.checkmate.connected = True
        
        result = self.checkmate.start()
        
        self.assertEqual(result, 0)
        # Check that final status is SHUTDOWN
        self.assertEqual(self.checkmate.status["status"], Status.SHUTDOWN)


if __name__ == "__main__":
    unittest.main()
