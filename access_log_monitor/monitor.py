from collections import deque
import os
import re
import threading
import time

from .worker import Worker
from .utils import get_utc_now


class AccessLogMonitor():
    """
    Main class that launches a watch on the target log file
    Starts a worker class in a background thread to generate necessary
    alerts and reports according to the time intervals set

    Note: Ideas for some of the implementation were taken from:
    http://www.dabeaz.com/generators/Generators.pdf
    """

    def __init__(
        self,
        alert_window=120,
        alert_threshold=10,
        alerting_interval=1,
        reporting_interval=10,
        path_to_log='./access_log_monitor/access.log',
        log_format=(
            r'^(?P<host>.*?) (?P<referrer>.*?) (?P<user>.*?) \[(?P<timestamp>.*?)\] '
            r'"(?P<request>.*?)" (?P<status_code>\d{3}|\-) (?P<content_size>[\d\-]+)$'
        )
    ):

        if reporting_interval < 1 or alerting_interval < 1:
            raise ValueError("reporting_interval and alerting_interval have to be greater or equal to 1")

        self.WORKER_CONFIG = dict(
            ALERT_WINDOW=alert_window,  # window to base the alerting average rate on
            ALERT_THRESHOLD=alert_threshold,  # threshold (req/s) to raise alert
            ALERTING_INTERVAL=alerting_interval,  # interval at which to raise/remove alerts
            REPORTING_INTERVAL=reporting_interval,  # interval at which to run the report
        )

        self.log_pattern = re.compile(log_format)
        self.log_file = open(path_to_log, 'rt')

        self.buffer = deque()

        self.shutdown_signal = threading.Event()
        self.worker_thread = None

    def start(self):

        self._print_stdout("[MONITOR] Starting..")

        # start worker thread
        self.worker_thread = Worker(self.buffer, self.shutdown_signal, self.WORKER_CONFIG)
        self.worker_thread.start()
        self._print_stdout("[MONITOR] Worker started")

        # start reading
        self._print_stdout("[MONITOR] Monitoring started")
        self._start_reading()

    def stop(self):

        self.log_file.close()
        self.shutdown_signal.set()

        # wait for worker thread to quit gracefully
        self._print_stdout("[MONITOR] Shutting down worker gracefully ..")
        self.worker_thread.join()

        self._print_stdout("[MONITOR] Shut down")

    def _start_reading(self):
        """
        Read new logs into buffer queue
        """

        raw_lines = self._read_file()
        parsed_lines = self._parse_lines(raw_lines)

        for line in parsed_lines:
            self.buffer.append(line)

    def _parse_lines(self, lines):
        """
        Converts the raw log string into a dictionary with the relevant keys
        """

        def add_section(parsed_dict):
            """
            add section key to the parsed_dict
            """

            # get resource as second element of request string
            resource = parsed_dict['request'].split(" ")[1]
            # section defined as word after first '/' in resource
            parsed_dict['section'] = resource.split("/")[1]

            return parsed_dict

        matches = (self.log_pattern.match(line) for line in lines)

        dicts = (match.groupdict() for match in matches if match)

        processed_dicts = (add_section(d) for d in dicts)

        return processed_dicts

    def _read_file(self):
        """
        Generator to watch field and yield latest entry

        see https://github.com/dabeaz/generators/blob/master/examples/follow.py
        """

        self.log_file.seek(0, os.SEEK_END)
        try:
            while True:

                line = self.log_file.readline()

                if not line:
                    time.sleep(0.1)
                    continue

                yield line

        except KeyboardInterrupt:
            raise

    def _print_stdout(self, msg):
        """
        Prepend timestamp to message
        """

        print("[{}] {}".format(get_utc_now(), msg))
