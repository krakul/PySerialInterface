import unittest
from unittest.mock import MagicMock, patch
from serial import SerialException
from PySerialInterface.SerialInterface import SerialInterface, CLIResponseMessage, ResponseTimeout, SerialNotConnected, \
    InvalidMessage


class TestSerialInterface(unittest.TestCase):

    @patch("PySerialInterface.SerialInterface.Serial")
    def test_wait_for_start(self, mock_serial_class):
        # Setup
        mock_serial_instance = MagicMock()
        mock_serial_class.return_value = mock_serial_instance

        si = SerialInterface(["COM1", "COM2"])
        connected = si.is_connected()
        # Assertions
        self.assertFalse(connected)
        self.assertIsNone(si.get_serial())

    @patch("PySerialInterface.SerialInterface.Serial")
    def test_connect_success(self, mock_serial_class):
        # Setup
        mock_serial_instance = MagicMock()
        mock_serial_class.return_value = mock_serial_instance

        si = SerialInterface(["COM1", "COM2"])
        si.start()
        connected = si.is_connected()

        # Assertions
        self.assertTrue(connected)
        self.assertIsNotNone(si.get_serial())
        mock_serial_class.assert_called_with(port="COM1", baudrate=115200, timeout=0.1)

    @patch("PySerialInterface.SerialInterface.Serial")
    def test_variables(self, mock_serial_class):
        # Setup
        mock_serial_instance = MagicMock()
        mock_serial_class.return_value = mock_serial_instance

        si = SerialInterface(["COM2", "COM1"], 9600, 1.5)
        si.start()

        # Assertions
        self.assertIsNotNone(si.get_serial())
        mock_serial_class.assert_called_with(port="COM2", baudrate=9600, timeout=1.5)

    @patch("PySerialInterface.SerialInterface.Serial")
    def test_no_com_ports(self, mock_serial_class):
        # Setup
        mock_serial_instance = MagicMock()
        mock_serial_class.return_value = mock_serial_instance

        si = SerialInterface([])
        si.start()
        connected = si.is_connected()
        # Assertions
        self.assertIsNone(si.get_serial())
        self.assertFalse(connected)

    @patch("PySerialInterface.SerialInterface.Serial", side_effect=SerialException("No port"))
    def test_connect_failure(self, mock_serial_class):
        si = SerialInterface(["COM1"])
        si.start()
        connected = si.is_connected()
        self.assertFalse(connected)
        self.assertIsNone(si.get_serial())

    def test_parse_message_valid(self):
        event = SerialInterface.parse_message("OK\r\n")
        self.assertIsInstance(event, CLIResponseMessage)
        self.assertEqual(event.content, "OK")

    def test_parse_message_only_msg_end(self):
        event = SerialInterface.parse_message("\r\n")
        self.assertIsInstance(event, InvalidMessage)
        self.assertEqual(event.error, "Empty line")

    def test_parse_message_empty_message(self):
        event = SerialInterface.parse_message("")
        self.assertIsInstance(event, InvalidMessage)
        self.assertEqual(event.error, "Empty line")

    @patch("PySerialInterface.SerialInterface.Serial")
    def test_handle_serial_request_timeout(self, mock_serial_class):
        mock_serial_instance = MagicMock()
        mock_serial_instance.read_until.return_value = b"NOT OK\r\n"
        mock_serial_class.return_value = mock_serial_instance
        si = SerialInterface(["COM1"])
        si.start()

        event = si.queue_request_wait_response(
            req="AT", required_resp_start="HELLO", resp_type=CLIResponseMessage, timeout=0.1
        )

        self.assertIsInstance(event, ResponseTimeout)

    @patch("PySerialInterface.SerialInterface.Serial")
    def test_handle_serial_request_success(self, mock_serial_class):
        mock_serial_instance = MagicMock()
        mock_serial_instance.read_until.return_value = b"OK THIS IS GOOD\r\n"
        mock_serial_class.return_value = mock_serial_instance
        si = SerialInterface(["COM1"])
        si.start()

        self.assertTrue(si.is_connected())

        event = si.queue_request_wait_response(
            req="AT", required_resp_start="OK", resp_type=CLIResponseMessage, timeout=0.1
        )

        self.assertIsInstance(event, CLIResponseMessage)
        self.assertEqual(event.content, "OK THIS IS GOOD")

    @patch("PySerialInterface.SerialInterface.Serial")
    def test_handle_serial_request_only_match_start(self, mock_serial_class):
        mock_serial_instance = MagicMock()
        mock_serial_instance.read_until.return_value = b"NOT OK\r\n"
        mock_serial_class.return_value = mock_serial_instance
        si = SerialInterface(["COM1"])
        si.start()

        event = si.queue_request_wait_response(
            req="AT", required_resp_start="OK", resp_type=CLIResponseMessage, timeout=0.1
        )

        self.assertIsInstance(event, ResponseTimeout)

    def test_queue_request_wait_response_not_connected(self):
        si = SerialInterface([])
        response = si.queue_request_wait_response("AT", "OK")
        self.assertIsInstance(response, SerialNotConnected)


if __name__ == '__main__':
    unittest.main()
