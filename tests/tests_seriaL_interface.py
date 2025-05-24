import unittest
from unittest.mock import MagicMock, patch
from serial import SerialException
from PySerialInterface.SerialInterface import SerialInterface, CLIResponseMessage, ResponseTimeout, SerialNotConnected
import time
from logging import getLogger
import logging
logging.basicConfig(level=logging.INFO)


class TestSerialInterface(unittest.TestCase):

    def setUp(self):
        self.si = None  # Track the SerialInterface instance
        self.mock_serial_instance = MagicMock()
        self.logger = getLogger(self.__class__.__name__)

    def tearDown(self):
        # Stop and join thread if it was started
        if self.si and self.si.is_running():
            self.si.stop()
            for i in range(3):
                if self.si.is_running() is False:
                    break
                time.sleep(0.5)  # give time for the thread to stop

            if self.si.is_running():
                self.si.join()

    @patch("PySerialInterface.SerialInterface.Serial")
    def test_wait_for_start(self, mock_serial_class):
        # Setup
        mock_serial_class.return_value = self.mock_serial_instance

        self.si = SerialInterface(["COM1", "COM2"], logger=self.logger)

        time.sleep(1)  # give time for serial connection to establish

        connected = self.si.is_connected()
        # Assertions
        self.assertFalse(connected)
        self.assertIsNone(self.si.get_serial())

    @patch("PySerialInterface.SerialInterface.Serial")
    def test_connect_success(self, mock_serial_class):
        mock_serial_class.return_value = self.mock_serial_instance

        self.si = SerialInterface(["COM1", "COM2"])
        self.si.start()

        time.sleep(1)  # give time for serial connection to establish

        connected = self.si.is_connected()

        # Assertions
        self.assertTrue(connected)
        self.assertIsNotNone(self.si.get_serial())
        mock_serial_class.assert_called_with(port="COM1", baudrate=115200, timeout=0.1)

    @patch("PySerialInterface.SerialInterface.Serial")
    def test_variables(self, mock_serial_class):
        mock_serial_class.return_value = self.mock_serial_instance

        self.si = SerialInterface(["COM2", "COM1"], 9600, 1.5)
        self.si.start()

        # Assertions
        self.assertIsNotNone(self.si.get_serial())
        mock_serial_class.assert_called_with(port="COM2", baudrate=9600, timeout=1.5)

    @patch("PySerialInterface.SerialInterface.Serial")
    def test_no_com_ports(self, mock_serial_class):
        mock_serial_class.return_value = self.mock_serial_instance

        self.si = SerialInterface([])
        self.si.start()

        time.sleep(1)  # give time for serial connection to establish

        connected = self.si.is_connected()
        # Assertions
        self.assertIsNone(self.si.get_serial())
        self.assertFalse(connected)

    @patch("PySerialInterface.SerialInterface.Serial", side_effect=SerialException("No port"))
    def test_connect_failure(self, mock_serial_class):
        self.si = SerialInterface(["COM1"])
        self.si.start()

        time.sleep(1)  # give time for serial connection to establish

        connected = self.si.is_connected()
        self.assertFalse(connected)
        self.assertIsNone(self.si.get_serial())

    @patch("PySerialInterface.SerialInterface.Serial")
    def test_handle_serial_request_timeout(self, mock_serial_class):
        self.mock_serial_instance.read_until.return_value = b"NOT OK\r\n"
        mock_serial_class.return_value = self.mock_serial_instance
        self.si = SerialInterface(["COM1"])
        self.si.start()

        time.sleep(1)  # give time for serial connection to establish

        connected = self.si.is_connected()
        self.assertTrue(connected)

        event = self.si.queue_request_wait_response(
            req="AT", required_resp_start="HELLO", resp_type=CLIResponseMessage
        )

        self.assertIsInstance(event, ResponseTimeout)
        self.mock_serial_instance.write.assert_called()
        self.mock_serial_instance.write.assert_any_call(b"AT\n")

    @patch("PySerialInterface.SerialInterface.Serial")
    def test_handle_serial_request_specific_timeout(self, mock_serial_class):
        self.mock_serial_instance.read_until.return_value = b"NOT OK\r\n"
        mock_serial_class.return_value = self.mock_serial_instance
        self.si = SerialInterface(["COM1"])
        self.si.start()

        time.sleep(1)  # give time for serial connection to establish

        connected = self.si.is_connected()
        self.assertTrue(connected)

        timeout = 2.0  # seconds

        start_time = time.time()
        event = self.si.queue_request_wait_response(
            req="AT+1234", required_resp_start="HELLO", resp_type=CLIResponseMessage, timeout=timeout
        )
        end_time = time.time()
        elapsed = end_time - start_time
        self.mock_serial_instance.write.assert_called()
        self.mock_serial_instance.write.assert_any_call(b"AT+1234\n")
        self.assertIsInstance(event, ResponseTimeout)
        self.assertGreaterEqual(elapsed, timeout, f"Elapsed time {elapsed} was less than timeout {timeout}")
        self.assertLessEqual(elapsed, timeout + 0.5, f"Elapsed time {elapsed} was more than timeout + 0.5 {timeout + 0.5}")

    @patch("PySerialInterface.SerialInterface.Serial")
    def test_handle_serial_request_retry_cnt(self, mock_serial_class):
        self.mock_serial_instance.read_until.return_value = b"NOT OK\r\n"
        mock_serial_class.return_value = self.mock_serial_instance
        self.si = SerialInterface(["COM1"])
        self.si.start()

        time.sleep(1)  # give time for serial connection to establish

        connected = self.si.is_connected()
        self.assertTrue(connected)

        timeout = 2.0  # seconds
        retry_cnt = 3

        start_time = time.time()
        event = self.si.queue_request_wait_response(
            req="AT+1234", required_resp_start="HELLO", resp_type=CLIResponseMessage, timeout=timeout, retry_cnt=retry_cnt
        )
        end_time = time.time()
        elapsed = end_time - start_time
        self.mock_serial_instance.write.assert_called()
        self.mock_serial_instance.write.assert_any_call(b"AT+1234\n")
        self.assertIsInstance(event, ResponseTimeout)
        self.assertGreaterEqual(elapsed, timeout * retry_cnt, f"Elapsed time {elapsed} was less than timeout * retry_cnt {timeout * retry_cnt}")
        self.assertLessEqual(elapsed, timeout * retry_cnt + 0.5, f"Elapsed time {elapsed} was more than timeout * retry_cnt + 0.5 {timeout * retry_cnt + 0.5}")

    @patch("PySerialInterface.SerialInterface.Serial")
    def test_handle_serial_request_success(self, mock_serial_class):
        self.mock_serial_instance.read_until.return_value = b"OK THIS IS GOOD\r\n"
        mock_serial_class.return_value = self.mock_serial_instance
        self.si = SerialInterface(["COM1"])
        self.si.start()

        time.sleep(1)  # give time for serial connection to establish

        connected = self.si.is_connected()
        self.assertTrue(connected)

        event = self.si.queue_request_wait_response(
            req="AT", required_resp_start="OK", resp_type=CLIResponseMessage, timeout=0.1
        )

        self.assertIsInstance(event, CLIResponseMessage)
        self.assertEqual(event.content, "OK THIS IS GOOD")

    @patch("PySerialInterface.SerialInterface.Serial")
    def test_handle_serial_request_only_match_start(self, mock_serial_class):
        self.mock_serial_instance.read_until.return_value = b"NOT OK\r\n"
        mock_serial_class.return_value = self.mock_serial_instance
        self.si = SerialInterface(["COM1"])
        self.si.start()

        time.sleep(1)  # give time for serial connection to establish

        connected = self.si.is_connected()
        self.assertTrue(connected)

        event = self.si.queue_request_wait_response(
            req="AT", required_resp_start="OK", resp_type=CLIResponseMessage, timeout=0.1
        )

        self.assertIsInstance(event, ResponseTimeout)

    def test_queue_request_wait_response_not_connected(self):
        self.si = SerialInterface([])
        response = self.si.queue_request_wait_response("AT", "OK")
        self.assertIsInstance(response, SerialNotConnected)


if __name__ == '__main__':
    unittest.main()
