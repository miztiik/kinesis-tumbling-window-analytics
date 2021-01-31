from aws_cdk import core
from aws_cdk import aws_kinesisfirehose as _kinesis_fh
from aws_cdk import aws_kinesisanalytics as _kda
from aws_cdk import aws_lambda as _lambda
from aws_cdk import aws_iam as _iam
from aws_cdk import aws_logs as _logs
from aws_cdk import aws_s3 as _s3


class GlobalArgs:
    """
    Helper to define global statics
    """

    OWNER = "MystiqueAutomation"
    ENVIRONMENT = "production"
    REPO_NAME = "kinesis-tumbling-window-analytics"
    SOURCE_INFO = f"https://github.com/miztiik/{REPO_NAME}"
    VERSION = "2021_01_24"
    MIZTIIK_SUPPORT_EMAIL = ["mystique@example.com", ]


class KinesisTumblingWindowAnalyticsStack(core.Stack):

    def __init__(
        self,
        scope: core.Construct,
        construct_id: str,
        stack_log_level: str,
        src_stream,
        dest_stream,
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Kinesis Analytics IAM Role
        kda_store_revenue_agg_role = _iam.Role(
            self,
            "FirehoseAnalyticsRole",
            role_name=f"kda_store_revenue_agg_role",
            assumed_by=_iam.ServicePrincipal("kinesisanalytics.amazonaws.com"),
            external_id=core.Aws.ACCOUNT_ID,
        )

        # Add permissions to Kinesis Fireshose to Write to S3
        roleStmt3 = _iam.PolicyStatement(
            effect=_iam.Effect.ALLOW,
            resources=[f"{src_stream.stream_arn}"
                       ],
            actions=[
                "kinesis:DescribeStream",
                "kinesis:GetShardIterator",
                "kinesis:GetRecords",
                "kinesis:ListShards"
            ]
        )
        roleStmt3.sid = "AllowKinesisAnalyticsToReadInput"
        kda_store_revenue_agg_role.add_to_policy(roleStmt3)

        roleStmt4 = _iam.PolicyStatement(
            effect=_iam.Effect.ALLOW,
            resources=[f"arn:aws:firehose:{core.Aws.REGION}:{core.Aws.ACCOUNT_ID}:deliverystream/{dest_stream.delivery_stream_name}"
                       ],
            actions=[
                "firehose:DescribeDeliveryStream",
                "firehose:PutRecord",
                "firehose:PutRecordBatch"
            ]
        )
        roleStmt4.sid = "AllowKinesisAnalyticsWriteToFirehose"
        kda_store_revenue_agg_role.add_to_policy(roleStmt4)

        # Kinesis Analytics Application

        # Define Input Data Schema

        """
        # KDA doesn't like - (dash) in names
        col1 = _kda.CfnApplicationV2.RecordColumnProperty(
            name="store_id",
            sql_type="VARCHAR(16)",
            mapping="$.store_id"
        )
        col2 = _kda.CfnApplicationV2.RecordColumnProperty(
            name="category",
            sql_type="VARCHAR(16)",
            mapping="$.category"
        )
        col3 = _kda.CfnApplicationV2.RecordColumnProperty(
            name="evnt_time",
            sql_type="VARCHAR(16)",
            mapping="$.evnt_time"
        )
        col4 = _kda.CfnApplicationV2.RecordColumnProperty(
            name="sales",
            sql_type="REAL",
            mapping="$.sales"
        )

        sales_schema = _kda.CfnApplicationV2.InputSchemaProperty(
            record_columns=[col1, col2, col3, col4],
            record_encoding="UTF-8",
            record_format=_kda.CfnApplicationV2.RecordFormatProperty(
                record_format_type="JSON",
                mapping_parameters=_kda.CfnApplicationV2.MappingParametersProperty(
                    json_mapping_parameters=_kda.CfnApplicationV2.JSONMappingParametersProperty(
                        record_row_path="$"
                    )
                )
            )
        )

        store_revenue = _kda.CfnApplicationV2(
            self,
            "storeRevenuePerMinute",
            runtime_environment="SQL-1_0",
            service_execution_role=f"{kda_store_revenue_agg_role.role_arn}",
            application_description="Fetch store revenue per minute and store in S3",
            application_name="store_revenue_per_min",
            application_configuration=_kda.CfnApplicationV2.ApplicationConfigurationProperty(
                sql_application_configuration=_kda.CfnApplicationV2.SqlApplicationConfigurationProperty(
                    inputs=[_kda.CfnApplicationV2.InputProperty(
                        name_prefix="store_revenue_per_min",
                        kinesis_streams_input=_kda.CfnApplicationV2.KinesisStreamsInputProperty(
                            resource_arn=f"{data_pipe_stream.stream_arn}",
                        ),
                        # input_parallelism=_kda.CfnApplicationV2.InputParallelismProperty(
                        #     count=1),
                        input_schema=sales_schema
                    )
                    ]
                )
            )
        )

        """

        # KDA doesn't like - (dash) in names
        col1 = _kda.CfnApplication.RecordColumnProperty(
            name="store_id",
            sql_type="VARCHAR(16)",
            mapping="$.store_id"
        )
        col2 = _kda.CfnApplication.RecordColumnProperty(
            name="category",
            sql_type="VARCHAR(16)",
            mapping="$.category"
        )
        col3 = _kda.CfnApplication.RecordColumnProperty(
            name="evnt_time",
            sql_type="TIMESTAMP",
            mapping="$.evnt_time"
        )
        col4 = _kda.CfnApplication.RecordColumnProperty(
            name="sales",
            sql_type="REAL",
            mapping="$.sales"
        )

        sales_schema = _kda.CfnApplication.InputSchemaProperty(
            record_columns=[col1, col2, col3, col4],
            record_encoding="UTF-8",
            record_format=_kda.CfnApplication.RecordFormatProperty(
                record_format_type="JSON",
                mapping_parameters=_kda.CfnApplication.MappingParametersProperty(
                    json_mapping_parameters=_kda.CfnApplication.JSONMappingParametersProperty(
                        record_row_path="$"
                    )
                )
            )
        )

        revenue_agg_sql_01 = """CREATE OR REPLACE STREAM "DEST_SQL_STREAM_BY_STORE_ID" ("store_id" VARCHAR(16),"revenue" REAL, "timestamp" TIMESTAMP);
            CREATE OR REPLACE PUMP "STREAM_PUMP" AS INSERT INTO "DEST_SQL_STREAM_BY_STORE_ID"
                SELECT STREAM "store_id", SUM("sales") AS "revenue", ROWTIME AS "timestamp"
                    FROM "STORE_REVENUE_PER_MIN_001"
                    GROUP BY STEP("STORE_REVENUE_PER_MIN_001".ROWTIME BY INTERVAL '60' SECOND),
                    "store_id"
                    ;
            """

        store_revenue = _kda.CfnApplication(
            self,
            "storeRevenuePerMinute",
            application_description="Fetch store revenue per minute and store in S3",
            application_name="STORE_REVENUE_PER_MIN",
            application_code=revenue_agg_sql_01,
            inputs=[_kda.CfnApplication.InputProperty(
                name_prefix="STORE_REVENUE_PER_MIN",
                kinesis_streams_input=_kda.CfnApplication.KinesisStreamsInputProperty(
                            resource_arn=f"{src_stream.stream_arn}",
                            role_arn=f"{kda_store_revenue_agg_role.role_arn}"
                ),
                # input_parallelism=_kda.CfnApplication.InputParallelismProperty(
                #     count=1),
                input_schema=sales_schema
            )
            ]
        )

        # KDA Output
        kda_dest_schema = _kda.CfnApplicationOutput.DestinationSchemaProperty(
            record_format_type="JSON"
        )

        revenue_to_firehose = _kda.CfnApplicationOutput.KinesisFirehoseOutputProperty(
            resource_arn=f"{dest_stream.attr_arn}",
            role_arn=f"{kda_store_revenue_agg_role.role_arn}"
        )

        kida_output_to_firehose = _kda.CfnApplicationOutput(
            self,
            "storeRevenuePerMinuteToFirehose",
            # application_name=f"{store_revenue.application_name}",
            application_name=core.Fn.ref(store_revenue.logical_id),
            # application_name=f"{store_revenue.logical_id}",
            output=_kda.CfnApplicationOutput.OutputProperty(
                destination_schema=kda_dest_schema,
                kinesis_firehose_output=revenue_to_firehose,
                name="DEST_SQL_STREAM_BY_STORE_ID"
            )
        )

        ###########################################
        ################# OUTPUTS #################
        ###########################################
        output_0 = core.CfnOutput(
            self,
            "AutomationFrom",
            value=f"{GlobalArgs.SOURCE_INFO}",
            description="To know more about this automation stack, check out our github page."
        )
