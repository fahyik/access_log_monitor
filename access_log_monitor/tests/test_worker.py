from collections import deque
import mock

from ..worker import Worker


WORKER_CONFIG = dict(
    ALERT_WINDOW=10,  # window to base the alerting average rate on
    ALERT_THRESHOLD=10,  # threshold (req/s) to raise alert
    ALERTING_INTERVAL=1,  # interval at which to raise/remove alerts
    REPORTING_INTERVAL=10,  # interval at which to run the report
)


class TestWorkerAlerting():

    @mock.patch.object(Worker, '_print_alert')
    def test_alert_should_trigger(self, mock_print_alert):
        """
        Threshold = 10 req/s
        We simulate an average rate of 20 req/s
        Expect:
            alert to be triggered
        """

        w = Worker(mock.Mock(), mock.Mock(), WORKER_CONFIG)

        w.tracking = deque([20, 20])

        w._alert()

        assert w.alert
        mock_print_alert.assert_called_with("TRIGGERED")

    @mock.patch.object(Worker, '_print_alert')
    def test_alert_should_not_trigger(self, mock_print_alert):
        """
        Threshold = 10 req/s
        We simulate an average rate of 5 requests/s
        Expect:
            alert to be triggered
        """

        w = Worker(mock.Mock(), mock.Mock(), WORKER_CONFIG)

        w.tracking = deque([5, 5])

        w._alert()

        assert not w.alert
        mock_print_alert.assert_not_called()

    @mock.patch.object(Worker, '_print_alert')
    def test_alert_should_trigger_and_resolve(self, mock_print_alert):
        """
        Threshold = 10 req/s
        We first trigger an alert with average of 20 req/s
        We simulate more polls to bring down average to below threshold.
        Expect:
            alert to be triggered
            alert to be removed thereafter
            alert to be logged in alert_history
        """

        w = Worker(mock.Mock(), mock.Mock(), WORKER_CONFIG)

        w.tracking = deque([20, 20])

        # expects an alert here
        w._alert()

        assert w.alert
        assert not w.alert_history
        mock_print_alert.assert_called_with("TRIGGERED")

        # simulate empty polls to lower average to 5
        for i in range(4):
            w.tracking.append(0)

        w._alert()

        assert not w.alert
        assert w.alert_history
        mock_print_alert.assert_called_with("REMOVED")
