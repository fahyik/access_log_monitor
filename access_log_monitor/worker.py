from collections import deque, defaultdict
from threading import Lock, Thread
import time

from .utils import get_utc_now


class Worker(Thread):
    """
    Worker thread to handle the alert plus reporting
    """

    def __init__(self, buffer, shutdown_signal, worker_config):
        # invoke base constructor before doing anything else
        # see: https://docs.python.org/3/library/threading.html#threading.Thread
        super().__init__()

        self.daemon = True

        self.WORKER_CONFIG = worker_config

        # parent buffer
        self.buffer = buffer

        # REPORTING
        # --------------------------------------------------
        # queue logs to be processed
        self.to_process = deque()
        # lock to access to_process
        self.processing_lock = Lock()

        # ALERTING
        # --------------------------------------------------
        # queue to keep track of requests during last X secs
        self.tracking = deque(maxlen=self.WORKER_CONFIG['ALERT_WINDOW'])
        self.alert = None
        self.alert_history = []

        # SHUTDOWN
        # --------------------------------------------------
        self.shutdown_signal = shutdown_signal

    def run(self):
        """
        Run an infinite loop to poll the buffer queue every `polling_interval` seconds

        """

        count = 0
        start_time = time.time()
        polling_interval = 1
        alerting_interval = self.WORKER_CONFIG['ALERTING_INTERVAL']
        reporting_interval = self.WORKER_CONFIG['REPORTING_INTERVAL']

        while True:

            if self.shutdown_signal.is_set():
                print("[{}] [WORKER] Shut down".format(get_utc_now()))
                break

            polling = Thread(target=self._poll, daemon=True)
            polling.start()

            if count and count % alerting_interval == 0:
                alerting = Thread(target=self._alert, daemon=True)
                alerting.start()

            if count and count % reporting_interval == 0:
                reporting = Thread(target=self._report, daemon=True)
                reporting.start()

            count += 1

            # run every `polling_interval` seconds
            time.sleep(polling_interval - ((time.time() - start_time) % polling_interval))

    def _poll(self):

        requests_qty = len(self.buffer)
        self.tracking.append(requests_qty)

        self.processing_lock.acquire()

        try:
            for i in range(requests_qty):
                self.to_process.append(self.buffer.popleft())
        finally:
            self.processing_lock.release()

    def _report(self):

        """
        Report consists of 4 statistics:
        1. most hit section along with number of hits
        2. total no. of requests
        3. total no. of successes (status code 2xx) and errors (non 2xx, i.e. status code 4xx, 5xx)
        4. report existing alert, if any
        """

        report = self._generate_report()
        self._print_report(report)

    def _alert(self):

        average = sum(self.tracking) / len(self.tracking)

        if average > self.WORKER_CONFIG['ALERT_THRESHOLD']:

            if not self.alert:
                self.alert = {
                    "id": len(self.alert_history) + 1,
                    "triggered_at": get_utc_now(),  # datetime
                    "resolved_at": get_utc_now(),  # datetime
                    "rate_at_trigger": average,  # requests/s
                    "current_rate": average,  # requests/s
                }
                self._print_alert("TRIGGERED")

            else:
                self.alert['current_rate'] = average

        else:

            if self.alert:
                """
                Remove alert and append to history
                """

                self.alert['current_rate'] = average
                self.alert['resolved_at'] = get_utc_now()
                self._print_alert("REMOVED")

                # append to history
                self.alert_history.append(self.alert)
                self.alert = None

    def _print_alert(self, action):

        msg = "[{}] [ALERT] [#{}] [{}] {}- Current Rate: {:.2f}/s (Threshold: {}/s)"

        triggered_at = "Triggered at: {} ".format(self.alert['triggered_at'])

        msg = msg.format(
            get_utc_now(),
            self.alert["id"],
            action,
            "" if action == "TRIGGERED" else triggered_at,
            self.alert['current_rate'],
            self.WORKER_CONFIG['ALERT_THRESHOLD']
        )

        print(msg)

    def _print_report(self, report):

        print("[{}] [REPORT]".format(get_utc_now()))
        print(60 * "==")  # print horizontal rule

        print("SUMMARY FOR LAST {} SECONDS:".format(self.WORKER_CONFIG['REPORTING_INTERVAL']))
        print(60 * "--")

        if not report['total_requests']:
            print("No new requests.")
        else:
            print(
                "Most hit section   : '{}' ({} hits)"
                .format(
                    report['most_requested_section'],
                    report['most_requested_count']
                )
            )
            print("Total hits         : {}".format(report['total_requests']))
            print("Successes          : {}".format(report['successes']))
            print("Errors             : {}".format(report['total_requests'] - report['successes']))

        # print existing alert
        if self.alert:
            print("\nEXISTING ALERT:")
            print(60 * "--")

            existing_alert = (
                "Id: #{} - Triggered at: {} - Rate at Trigger: {:.2f}/s - Current Rate: {:.2f}/s (Threshold: {}/s)"
                .format(
                    self.alert['id'],
                    self.alert['triggered_at'],
                    self.alert['rate_at_trigger'],
                    self.alert['current_rate'],
                    self.WORKER_CONFIG['ALERT_THRESHOLD']
                )
            )

            print(existing_alert)

        # print alert history
        if self.alert_history:
            print("\nALERT HISTORY:")
            print(60 * "--")

            for alert in reversed(self.alert_history):
                alert = (
                    "Id: #{} - Triggered at: {} - Rate at Trigger: {:.2f}/s - Resolved at: {}"
                    .format(
                        alert['id'],
                        alert['triggered_at'],
                        alert['rate_at_trigger'],
                        alert['resolved_at']
                    )
                )

                print(alert)

        print(60 * "==")  # print horizontal rule

    def _generate_report(self):

        report = {
            "most_requested_section": "",
            "most_requested_count": 0,
            "successes": 0,
            "total_requests": 0
        }

        self.processing_lock.acquire()

        try:
            # record total no. of requests
            report['total_requests'] = len(self.to_process)

            # hashmap to track top section hit
            section_count = defaultdict(int)

            while self.to_process:

                req = self.to_process.popleft()

                # count no. of successes
                status_code = int(req['status_code'])
                if status_code >= 200 and status_code < 400:
                    report['successes'] += 1

                section_count[req['section']] += 1

            # determine most hit section
            if section_count:
                sorted_section_count = sorted(section_count.items(), key=lambda s: s[1], reverse=True)
                report['most_requested_section'], report['most_requested_count'] = sorted_section_count[0]

        finally:
            self.processing_lock.release()

        return report
