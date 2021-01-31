#!/usr/bin/env python3

from kinesis_tumbling_window_analytics.stacks.back_end.serverless_kinesis_producer_stack.serverless_kinesis_producer_stack import ServerlessKinesisProducerStack
from kinesis_tumbling_window_analytics.stacks.back_end.firehose_transformation_stack.firehose_tranformation_stack import FirehoseTransformationStack
from kinesis_tumbling_window_analytics.stacks.back_end.kinesis_tumbling_window_analytics_stack.kinesis_tumbling_window_analytics_stack import KinesisTumblingWindowAnalyticsStack

from aws_cdk import core

app = core.App()

# Kinesis Data Producer on Lambda
serverless_kinesis_producer_stack = ServerlessKinesisProducerStack(
    app,
    f"{app.node.try_get_context('project')}-producer-stack",
    stack_log_level="INFO",
    description="Miztiik Automation: Kinesis Data Producer on Lambda"
)

# Firehose with lambda transformations
kinesis_firehose_transformation_stack = FirehoseTransformationStack(
    app,
    f"{app.node.try_get_context('project')}-firehose-stack",
    stack_log_level="INFO",
    description="Miztiik Automation: Firehose with lambda transformations"
)


# Analytics on stream of data using lambda tumbling window.
tumbling_window_stream_analytics_stack = KinesisTumblingWindowAnalyticsStack(
    app,
    f"{app.node.try_get_context('project')}-consumer-stack",
    stack_log_level="INFO",
    src_stream=serverless_kinesis_producer_stack.get_stream,
    dest_stream=kinesis_firehose_transformation_stack.get_fh_stream,
    description="Miztiik Automation: Analytics on stream of data using Kinesis Data Analytics tumbling window"
)


# Stack Level Tagging
_tags_lst = app.node.try_get_context("tags")

if _tags_lst:
    for _t in _tags_lst:
        for k, v in _t.items():
            core.Tags.of(app).add(k, v, apply_to_launched_instances=True)


app.synth()
