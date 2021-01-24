#!/usr/bin/env python3

from aws_cdk import core

from kinesis_tumbling_window_analytics.kinesis_tumbling_window_analytics_stack import KinesisTumblingWindowAnalyticsStack


app = core.App()
KinesisTumblingWindowAnalyticsStack(app, "kinesis-tumbling-window-analytics")

app.synth()
