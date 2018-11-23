# Access Log Monitor
## Design

The log monitor is designed to work as follow:

The main thread keeps a watch on the log file and parses and pushes all new log lines to a `buffer queue`.

A worker thread is spawned to consume the buffer every second (polling_interval). This allows us to keep track of the no. of requests hitting us each second (stored in a separate queue). It also appends the consumed logs into a separate `to_process` queue which the `reporting` method will consume to generate the report. A simple lock is used to prevent concurrency issues between the `polling` and `reporting`.

In addition to this, the worker thread also executes the `alerting` and `reporting` methods according to the respective intervals set.

Other settings not available on the command line can be overriden in the class `AccessLogMonitor` in `monitor.py`.

### Potential problems and improvement
- The monitor is hardcoded to read logs of the format provided, if the log format suddenly changes, it will need to be updated manually. This can be improved by providing a config.
- The monitor is not tested to work at scale, i.e. what happens when the worker thread needs long than the polling interval to consume off the buffer.
- The shutdown can be more gracefully handled.


## Quickstart

### With Docker:
```bash
$ docker build . -t log_monitor
$ docker run -it log_monitor

# to specify alert threshold and path to log
$ docker run -it log_monitor --log-file='/path/to/log' --alert-threshold=200
```

### If you have python (>3.6) installed:
First set up your virtualenv.
Then:
```bash
# to install requirements
$ pip install -r requirements.txt

# to run
$ python main.py --log-file='/path/to/log' --alert-threshold=10
```


### Expected results:

## Start-up:
```
[2018-11-22 17:57:22+00:00] [MONITOR] Starting..
[2018-11-22 17:57:22+00:00] [MONITOR] Worker started
[2018-11-22 17:57:22+00:00] [MONITOR] Monitoring started
```

## Reports:
```
[2018-11-22 15:52:25+00:00] [REPORT]
=========================================================
SUMMARY FOR LAST 10 SECONDS:
---------------------------------------------------------
Most hit section   : 'food' (19 hits)
Total hits         : 124
Successes          : 23
Errors             : 101
=========================================================
```

## Alerts:
```
[2018-11-22 13:24:28+00:00] [ALERT] [#2] [TRIGGERED] - Current Rate: 10.09/s (Threshold: 10/s)

[2018-11-22 13:29:58+00:00] [ALERT] [#2] [REMOVED] Triggered at: 2018-11-22 13:24:28+00:00 - Current Rate: 10.00/s (Threshold: 10/s)
```

Existing alerts and history, if any, will show up at the bottom of the report
```
[2018-11-22 13:25:12+00:00] [REPORT]
========================================================================================================================
SUMMARY FOR LAST 10 SECONDS:
------------------------------------------------------------------------------------------------------------------------
Most hit section   : 'locations' (28 hits)
Total hits         : 166
Successes          : 36
Errors             : 130

EXISTING ALERT:
------------------------------------------------------------------------------------------------------------------------
Id: #3 - Triggered at: 2018-11-22 13:24:28+00:00 - Rate at Trigger: 10.09/s - Current Rate: 15.02/s (Threshold: 10/s)

ALERT HISTORY:
------------------------------------------------------------------------------------------------------------------------
Id: #2 - Triggered at: 2018-11-22 13:18:41+00:00 - Rate at Trigger: 11.10/s - Resolved at: 2018-11-22 13:22:58+00:00
Id: #1 - Triggered at: 2018-11-22 13:18:36+00:00 - Rate at Trigger: 10.60/s - Resolved at: 2018-11-22 13:18:40+00:00
========================================================================================================================
```

## Shutdown:
```
[2018-11-22 13:25:17+00:00] [MONITOR] Shutting down worker gracefully ..
[2018-11-22 13:25:17+00:00] [WORKER] Shut down
[2018-11-22 13:25:17+00:00] [MONITOR] Shut down
```