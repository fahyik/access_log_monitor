import getopt
import logging
import os
import sys


def get_arguments(argv):
    helper = 'Usage: python main.py -l --log-file=<path_to_log_file> -a --alert-threshold=<int: req/s>'

    path_to_log = ""
    alert_threshold = 10

    try:
        opts, args = getopt.getopt(argv, "a:h:l:", ["log-file=", "alert-threshold="])

    except getopt.GetoptError:
        print(helper)
        sys.exit(2)

    for opt, arg in opts:
        if opt == '-h':
            print(helper)
            sys.exit()

        elif opt in ("-a", "--alert-threshold"):
            alert_threshold = arg

        elif opt in ("-l", "--log-file"):
            path_to_log = arg

    if not path_to_log:
        path_to_log = '/tmp/access.log'
        print("Path to log file not set! defaults to '/tmp/access.log'")

    return path_to_log, alert_threshold


if __name__ == '__main__':

    current_path = os.path.dirname(os.path.abspath(__file__))
    sys.path.append(os.path.join(current_path, "access_log_monitor"))

    logging.basicConfig(level=logging.DEBUG)

    path_to_log, alert_threshold = get_arguments(sys.argv[1:])

    from access_log_monitor.monitor import AccessLogMonitor

    monitor = AccessLogMonitor(
        alert_threshold=alert_threshold,
        path_to_log=path_to_log
    )

    try:
        monitor.start()

    except KeyboardInterrupt:

        monitor.stop()
