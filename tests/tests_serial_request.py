import unittest
from PySerialInterface.SerialRequest import SerialRequest, EmptyMessage, CLIResponseMessage, InvalidMessage


class TestSerialRequest(unittest.TestCase):

    def test_serial_request_init(self):
        msg_out = b"Test message"
        required_resp_start = b"OK"
        required_resp_type = CLIResponseMessage
        timeout = 5.5
        retry_cnt = 5
        ser = SerialRequest(msg_out, required_resp_start, required_resp_type, timeout, retry_cnt)
        self.assertEqual(ser.msg_out, msg_out)
        self.assertEqual(ser.required_resp_start, required_resp_start)
        self.assertEqual(ser.required_resp_type, required_resp_type)
        self.assertEqual(ser.timeout, timeout)
        self.assertEqual(ser.retry_cnt, retry_cnt)

    def test_parse_message_none(self):
        event = SerialRequest.parse_message(None)
        self.assertIsInstance(event, EmptyMessage)
        self.assertEqual(event.error, "Empty line")

    def test_parse_message_empty_line(self):
        event = SerialRequest.parse_message(b" \r\n")
        self.assertIsInstance(event, EmptyMessage)
        self.assertEqual(event.error, "Empty line")

    def test_parse_message_trailing_whitespace(self):
        event = SerialRequest.parse_message(b"OK \r\n")
        self.assertIsInstance(event, CLIResponseMessage)
        self.assertEqual(event.content, "OK")

    def test_parse_message_valid(self):
        event = SerialRequest.parse_message(b"OK\r\n")
        self.assertIsInstance(event, CLIResponseMessage)
        self.assertEqual(event.content, "OK")

    def test_parse_message_invalid(self):
        event = SerialRequest.parse_message(b"OK\00\r\n")
        self.assertIsInstance(event, InvalidMessage)
        self.assertEqual(event.error, "Illegal character(s)")
        self.assertEqual(event.content, b"OK\00")

    def test_parse_message_only_0x0a(self):
        event = SerialRequest.parse_message(b"\n")
        self.assertIsInstance(event, InvalidMessage)
        self.assertEqual(event.error, "Msg only 0x0a")
        self.assertEqual(event.content, b"\n")

    def test_parse_message_only_0x0d(self):
        event = SerialRequest.parse_message(b"\r")
        self.assertIsInstance(event, InvalidMessage)
        self.assertEqual(event.error, "Msg only 0x0d")
        self.assertEqual(event.content, b"\r")

    def test_parse_message_only_0x0d_0x0a(self):
        event = SerialRequest.parse_message(b"\r\n")
        self.assertIsInstance(event, InvalidMessage)
        self.assertEqual(event.error, "Msg only 0x0d")
        self.assertEqual(event.content, b"\r")

    def test_parse_message_only_0x0d_0x0d(self):
        event = SerialRequest.parse_message(b"\r\r")
        self.assertIsInstance(event, InvalidMessage)
        self.assertEqual(event.error, "Msg only 0x0d")
        self.assertEqual(event.content, b"\r")

    def test_parse_message_only_msg_end(self):
        event = SerialRequest.parse_message(b"\r\n")
        self.assertIsInstance(event, InvalidMessage)
        self.assertEqual(event.error, "Msg only 0x0d")

    def test_parse_message_empty_message(self):
        event = SerialRequest.parse_message(b"")
        self.assertIsInstance(event, EmptyMessage)
        self.assertEqual(event.error, "Empty line")


if __name__ == '__main__':
    unittest.main()
