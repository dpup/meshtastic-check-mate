"""Tests for the NetstatResponder."""

import unittest
import time
from unittest.mock import patch, MagicMock

from checkmate.responders.netstat import NetstatResponder
from checkmate.constants import KEY_FROM, KEY_HOP_LIMIT, KEY_HOPS_AWAY, NETSTAT_WINDOW_HOURS


class TestNetstatResponder(unittest.TestCase):
    """Test case for the NetstatResponder class."""

    def setUp(self):
        """Set up test fixtures for NetstatResponder tests."""
        self.responder = NetstatResponder()
        
    @patch('checkmate.responders.netstat.is_text_message')
    def test_can_handle_not_text_message(self, mock_is_text_message):
        """Test can_handle returns False for non-text messages."""
        mock_is_text_message.return_value = False
        packet = {}
        
        result = self.responder.can_handle(packet)
        
        self.assertFalse(result)
        mock_is_text_message.assert_called_once_with(packet)
        
    @patch('checkmate.responders.netstat.is_text_message')
    @patch('checkmate.responders.netstat.get_text')
    def test_can_handle_not_netstat_command(self, mock_get_text, mock_is_text_message):
        """Test can_handle returns False for non-netstat commands."""
        mock_is_text_message.return_value = True
        mock_get_text.return_value = "Hello world"
        packet = {}
        
        result = self.responder.can_handle(packet)
        
        self.assertFalse(result)
        mock_is_text_message.assert_called_once_with(packet)
        mock_get_text.assert_called_once_with(packet)
        
    @patch('checkmate.responders.netstat.is_text_message')
    @patch('checkmate.responders.netstat.get_text')
    def test_can_handle_netstat_command(self, mock_get_text, mock_is_text_message):
        """Test can_handle returns True for ?net command."""
        mock_is_text_message.return_value = True
        mock_get_text.return_value = "?net"
        packet = {}
        
        result = self.responder.can_handle(packet)
        
        self.assertTrue(result)
        mock_is_text_message.assert_called_once_with(packet)
        mock_get_text.assert_called_once_with(packet)
        
    @patch('checkmate.responders.netstat.get_channel')
    @patch('checkmate.responders.netstat.get_name')
    def test_handle_no_nodes(self, mock_get_name, mock_get_channel):
        """Test handle with no nodes."""
        # Setup mocks
        mock_get_channel.return_value = 1
        mock_get_name.return_value = "Test User"
        
        # Test objects
        packet = {}
        interface = MagicMock()
        users = {"user1": "Test User"}
        location = "Test Location"
        
        # Call the method
        result = self.responder.handle(packet, interface, users, location)
        
        # Verify results
        self.assertTrue(result)
        mock_get_channel.assert_called_once_with(packet)
        mock_get_name.assert_called_once()
        interface.sendText.assert_called_once()
        self.assertEqual(interface.sendText.call_args[0][0], 
                         f"Net report! No active nodes seen in the last {NETSTAT_WINDOW_HOURS}hrs.")
        
    def test_packet_node_info_update(self):
        """Test updating node info from a packet."""
        # Setup test data
        packet = {
            KEY_FROM: 1234567890,  # This will be converted to a hex ID with id_to_hex
            KEY_HOP_LIMIT: 2
        }
        
        # We need to use can_handle which will indirectly call _update_node_info
        self.responder.can_handle(packet)
        
        # Verify results
        node_id = "!499602d2"  # Hex representation of 1234567890
        self.assertIn(node_id, self.responder.nodes)
        self.assertIn("last_seen", self.responder.nodes[node_id])
        self.assertIn("hops", self.responder.nodes[node_id])
        self.assertEqual(self.responder.nodes[node_id]["hops"], 1)  # MAX_HOPS(3) - 2 = 1
        
    def test_generate_report(self):
        """Test generating network report."""
        # Setup test data - nodes with varying hop counts and ages
        current_time = time.time()
        
        # Recent nodes (within activity window)
        self.responder.nodes = {
            "node1": {"last_seen": current_time - 1000, "hops": 0},
            "node2": {"last_seen": current_time - 2000, "hops": 0},
            "node3": {"last_seen": current_time - 3000, "hops": 1},
            "node4": {"last_seen": current_time - 4000, "hops": 1},
            "node5": {"last_seen": current_time - 5000, "hops": 1},
            "node6": {"last_seen": current_time - 6000, "hops": 2},
            "node7": {"last_seen": current_time - 7000, "hops": 2},
            # Old node (outside activity window)
            "old_node": {"last_seen": current_time - (4 * 3600), "hops": 0}
        }
        
        # Call the method
        report = self.responder._generate_report()
        
        # Verify results
        self.assertIn(f"Net report! In the last {NETSTAT_WINDOW_HOURS}hrs:", report)
        self.assertIn(" - 0 hops x 2", report)
        self.assertIn(" - 1 hop x 3", report)
        self.assertIn(" - 2 hops x 2", report)
        self.assertNotIn(" - 0 hops x 3", report)  # Should not include the old node
        
    @patch('checkmate.responders.netstat.time.time')
    def test_handle_with_nodes(self, mock_time):
        """Test handle with existing nodes."""
        # Setup mocks
        current_time = 1000000
        mock_time.return_value = current_time
        
        # Setup responder with some node data
        self.responder.nodes = {
            "node1": {"last_seen": current_time - 1000, "hops": 0},
            "node2": {"last_seen": current_time - 2000, "hops": 1},
            "node3": {"last_seen": current_time - 3000, "hops": 2}
        }
        
        # Test objects
        packet = {KEY_FROM: 1234567890}
        interface = MagicMock()
        users = {}
        location = "Test Location"
        
        # Call the method
        result = self.responder.handle(packet, interface, users, location)
        
        # Verify results
        self.assertTrue(result)
        interface.sendText.assert_called_once()
        sent_text = interface.sendText.call_args[0][0]
        self.assertIn(f"Net report! In the last {NETSTAT_WINDOW_HOURS}hrs:", sent_text)
        self.assertIn(" - 0 hops x 1", sent_text)
        self.assertIn(" - 1 hop x 1", sent_text)
        self.assertIn(" - 2 hops x 1", sent_text)
        
    def test_node_info_receiver(self):
        """Test the NodeInfoReceiver implementation."""
        # Setup test data
        node_id = "!abcdef"
        node_data = {
            KEY_HOPS_AWAY: 3,
            "user": {
                "id": "user123",
                "shortName": "Test User"
            }
        }
        
        # Call the method
        self.responder.update_node_info(node_id, node_data)
        
        # Verify results
        self.assertIn(node_id, self.responder.nodes)
        self.assertEqual(self.responder.nodes[node_id]["hops"], 3)


if __name__ == "__main__":
    unittest.main()