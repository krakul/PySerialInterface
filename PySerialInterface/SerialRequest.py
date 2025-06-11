# SPDX-License-Identifier: MIT

from dataclasses_json import dataclass_json
from dataclasses import dataclass
from typing import Union
import time


@dataclass_json
@dataclass
class Event:
    timestamp: float = time.time()


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
class EmptyMessage(Event):
    error: str = None


class SerialRequest:
    def __init__(self, msg_out, required_resp_start, required_resp_type, timeout: float, retry_cnt: int):
        self.msg_out = msg_out
        self.required_resp_start = required_resp_start
        self.required_resp_type = required_resp_type
        self.timeout: float = timeout
        self.retry_cnt: int = retry_cnt
        self.response: Union[Event, None] = None

    @staticmethod
    def cut_line_end_characters(line):
        # Cut the new line character
        if line[-1] == 0x0a:
            if len(line[:-1]) == 0:
                msg = InvalidMessage(content=line, error="Msg only 0x0a")
                return msg
            line = line[:-1]

        if line[-1] == 0x0d:
            if len(line[:-1]) == 0:
                msg = InvalidMessage(content=line, error="Msg only 0x0d")
                return msg
            line = line[:-1]
            if line[-1] == 0x0d:
                if len(line[:-1]) == 0:
                    msg = InvalidMessage(content=line, error="Msg only 0x0d")
                    return msg
                line = line[:-1]
        return line

    @staticmethod
    def check_valid_ascii(line) -> bool:
        # Check that bytes are valid ASCII characters
        for b in line:
            if b < 0x20 or b > 0x7E:
                return False
        return True

    @staticmethod
    def parse_message(line) -> Event:
        if line is None or len(line) == 0:
            return EmptyMessage(error="Empty line")
        line = SerialRequest.cut_line_end_characters(line)
        if isinstance(line, InvalidMessage):
            return line

        if SerialRequest.check_valid_ascii(line) is False:
            msg = InvalidMessage(content=line, error="Illegal character(s)")
            return msg

        # Try to decode line as ASCII
        try:
            line = line.decode('ascii')
        except UnicodeDecodeError as e:
            msg = InvalidMessage(content=line.hex('-'), error=f"Not ASCII: {e}")
            return msg

        # Strip trailing whitespaces
        line = line.rstrip()

        # Make sure text is not empty
        if not line:
            return EmptyMessage(error="Empty line")

        # Get content behind prefix
        if len(line) > 1:
            content = line.lstrip()
        else:
            content = ''

        return CLIResponseMessage(content=content)
