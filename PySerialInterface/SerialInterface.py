"""
Serial communication interface
"""
import time
from asyncio import QueueEmpty
from dataclasses import dataclass
import logging
from logging import getLogger
from typing import Union, List
from queue import Queue, Empty
from threading import Thread
from dataclasses_json import dataclass_json
from serial import Serial, SerialException


@dataclass_json
@dataclass
class Event:
    timestamp: float = 0.0


@dataclass_json
@dataclass
class CLIResponseMessage(Event):
    content: str = ""


@dataclass_json
@dataclass
class InvalidMessage(Event):
    content: str = ""
    error: str = None


@dataclass_json
@dataclass
class ResponseTimeout(Event):
    request: str = ""


@dataclass_json
@dataclass
class RequestHandlerTimeout(Event):
    request: str = ""


@dataclass_json
@dataclass
class SerialConnected(Event):
    port: str = ""


@dataclass_json
@dataclass
class SerialConnectionLost(Event):
    reason: str = ""


@dataclass_json
@dataclass
class SerialNotConnected(Event):
    pass


# ----------------------------------------------------------------------------------------------------------------------


# Serial communication interface
class SerialInterface(Thread):
    # Fields
    __serial: Union[Serial, None] = None
    __serial_list: List[str]
    __is_stopped: bool = False
    __is_force_reconnect_requested: bool = False
    __connected: bool = False
    __request_queue: Queue = Queue()
    __response_queue: Queue = Queue()

    # Constructor
    def __init__(self, port_list: List[str], baudrate=115200, timeout=0.1, logger=None):
        super().__init__(daemon=True)

        if logger is None:
            self.__logger = getLogger(self.__class__.__name__)
        else:
            self.__logger = logger

        # Construct fields
        self.__baudrate = baudrate
        self.__serial_list = port_list
        self.__timeout: float = timeout

    def get_serial(self):
        return self.__serial

    def is_connected(self) -> bool:
        return self.__connected

    def stop(self):
        self.__logger.info("Stop called!")
        self.__is_stopped = True

    def force_reconnect(self):
        self.__logger.info("Force reconnect requested!")
        self.__is_force_reconnect_requested = True

    # Connect to first available serial interface
    def __connect(self):
        self.__connected = False
        self.__is_force_reconnect_requested = False
        # Reset previous serial interface
        self.__serial = None

        # Try connecting
        for port in self.__serial_list:
            try:
                # Try to open port
                self.__serial = Serial(port=port, baudrate=self.__baudrate, timeout=self.__timeout)
                self.__logger.info(f"UART connection opened on port {self.__serial.port} with " +
                                   f"baudrate {self.__serial.baudrate} and timeout {self.__serial.timeout}")

                # Create event
                conn = SerialConnected(timestamp=time.time(), port=port)
                self.__event_to_log(conn)
                return True
            except SerialException as e:
                self.__logger.error(f"{e}")
        return False

    # Append event to log
    def __event_to_log(self, event: Event, level=logging.INFO):
        self.__logger.log(level, f"{event}")

    # Parse message
    @staticmethod
    def parse_message(text) -> Event:

        # Strip trailing whitespaces
        text = text.rstrip()

        # Make sure text is not empty
        if not text:
            return InvalidMessage(timestamp=time.time(), content=text, error="Empty line")

        # Get content behind prefix
        if len(text) > 1:
            content = text.lstrip()
        else:
            content = ''

        return CLIResponseMessage(timestamp=time.time(), content=content)

    # Read message
    # Return None if timeout
    def __read_message(self) -> Union[Event, None]:

        # Read line bytes - note that it can time out
        line = self.__serial.read_until(b'\r')

        # Got line ?
        if line:
            # Cut the new line character
            if line[-1] == 0x0a:
                line = line[:-1]
                if len(line) == 0:
                    msg = InvalidMessage(timestamp=time.time(), content=line.hex('-'), error="Msg only 0x0a")
                    return msg

            if line[-1] == 0x0d:
                line = line[:-1]
                if len(line) == 0:
                    msg = InvalidMessage(timestamp=time.time(), content=line.hex('-'), error="Msg only 0x0d")
                    return msg
                if line[-1] == 0x0d:
                    line = line[:-1]
                if len(line) == 0:
                    msg = InvalidMessage(timestamp=time.time(), content=line.hex('-'), error="Msg only 0x0d")
                    return msg

            # Check that bytes are valid ASCII characters
            for b in line:
                if b < 0x20 or b > 0x7E:
                    msg = InvalidMessage(timestamp=time.time(), content=line.hex('-'), error="Illegal character(s)")
                    self.__event_to_log(msg)
                    return msg

            # Try to decode line as ASCII
            try:
                text = line.decode('ascii')
            except UnicodeDecodeError as e:
                msg = InvalidMessage(timestamp=time.time(), content=line.hex('-'), error=f"Not ASCII: {e}")
                self.__event_to_log(msg)
                return msg

            msg = self.parse_message(text)
            return msg

        return None

    def __wait_for_response(self, required_resp_start, resp_type, timeout):
        timeout_time = time.time() + timeout
        while True:
            msg = self.__read_message()
            self.__event_to_log(msg, logging.DEBUG)
            # Got something ?
            if isinstance(msg, resp_type):
                if type(required_resp_start) == list:
                    for i in required_resp_start:
                        if msg.content.startswith(i):
                            return msg
                else:
                    if msg.content.startswith(required_resp_start):
                        return msg

            # Timeout ?
            if time.time() > timeout_time:
                break

        # We have timeout
        msg = ResponseTimeout(timestamp=time.time())
        self.__event_to_log(msg)
        return msg

    # Handle serial request
    def __handle_serial_request(self, req, required_resp_start, resp_type, timeout):
        if req is None:
            return self.__wait_for_response(required_resp_start, resp_type, timeout)
        else:
            # Try to send request up to 3 times
            for trial in range(3):
                # Send the request
                self.__serial.write(bytes(req + '\n', 'ascii'))

                # Make sure message goes out
                self.__serial.flush()

                if required_resp_start is None:
                    return None

                msg = self.__wait_for_response(required_resp_start, resp_type, timeout=timeout)

                if isinstance(msg, ResponseTimeout):
                    continue
                else:
                    return msg

            # We have timeout
            msg = ResponseTimeout(timestamp=time.time(), request=req)
            self.__event_to_log(msg)
            return msg

    def __process_incoming_message(self):
        msg = self.__read_message()
        if msg is not None:
            self.__event_to_log(msg, logging.DEBUG)

    def __process_request_queue(self):
        if self.__request_queue.empty():
            return
        try:
            queue_item = self.__request_queue.get(block=False)
            req, required_resp_start, resp_type, timeout = queue_item
            resp = self.__handle_serial_request(req, required_resp_start, resp_type, timeout)
            if resp:
                self.__response_queue.put(resp)
        except QueueEmpty:
            # Shouldn't happen but is guarded.
            self.__logger.warning("QueueEmpty exception caught unexpectedly.")

    def __handle_connection_lost(self, err):
        conn = SerialConnectionLost(timestamp=time.time(), reason=str(err))
        self.__event_to_log(conn)
        try:
            self.__serial.close()
        except Exception as close_err:
            self.__logger.warning(f"Failed to close serial: {close_err}")

    def __main_loop(self):
        err = None
        try:
            while self.__is_stopped is False and self.__is_force_reconnect_requested is False:
                if not self.__request_queue.empty():
                    self.__process_request_queue()
                else:
                    self.__process_incoming_message()
        except SerialException as e:
            err = e
        finally:
            if self.__is_force_reconnect_requested:
                self.__is_force_reconnect_requested = False
                err = "Reconnect Forced"
            self.__handle_connection_lost(err)

    # Thread entry function
    def run(self):
        while self.__is_stopped is False:

            # If connection succeeds, go to main loop
            if self.__connect():
                self.__connected = True
                self.__main_loop()
            self.__connected = False

            # Idle for 3 seconds before reconnecting.
            # But handle pending requests also meanwhile, otherwise they queue up...
            for loop in range(3):
                time.sleep(1)

                # Process queued requests and respond with not-connected
                while not self.__request_queue.empty():
                    try:
                        self.__request_queue.get(block=False, timeout=None)
                        conn = SerialNotConnected(timestamp=time.time())
                        self.__event_to_log(conn)
                        self.__response_queue.put(conn)
                    except QueueEmpty:
                        pass

    # Queue request and wait for response (up to 10 seconds)
    def queue_request_wait_response(self, req, required_resp_start, resp_type=CLIResponseMessage, timeout=1.5):
        if self.__connected:
            self.__request_queue.put((req, required_resp_start, resp_type, timeout))
            if required_resp_start is not None:
                try:
                    # Timeout has to 3 x each request timeout + some more
                    return self.__response_queue.get(block=True, timeout=timeout + 10.0)
                except Empty:
                    # It should not happen, but don't crash.
                    err = RequestHandlerTimeout(timestamp=time.time(), request=req)
                    self.__event_to_log(err)
                    return err
            else:
                return CLIResponseMessage(timestamp=time.time(), content="")
        else:
            return SerialNotConnected(timestamp=time.time())
