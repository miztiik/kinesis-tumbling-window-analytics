from aws_cdk import core
from aws_cdk import aws_kinesisfirehose as _kinesis_fh
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


class FirehoseTransformationStack(core.Stack):

    def __init__(
        self,
        scope: core.Construct,
        construct_id: str,
        stack_log_level: str,
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # The code that defines your stack goes here
        # Create an S3 Bucket for storing streaming data events from firehose
        fh_data_store = _s3.Bucket(
            self,
            "fhDataStore",
            removal_policy=core.RemovalPolicy.DESTROY,
            auto_delete_objects=True
        )

        firehose_delivery_stream_name = f"revenue_analytics_stream"

        # Firehose Lambda Transformer
        # Read Lambda Code
        try:
            with open("kinesis_tumbling_window_analytics/stacks/back_end/firehose_transformation_stack/lambda_src/kinesis_firehose_transformer.py",
                      encoding="utf-8",
                      mode="r"
                      ) as f:
                fh_transformer_fn_code = f.read()
        except OSError:
            print("Unable to read Lambda Function Code")
            raise

        fh_transformer_fn = _lambda.Function(
            self,
            "fhDataTransformerFn",
            function_name=f"fh_data_transformer",
            description="Transform incoming data events with newline character",
            runtime=_lambda.Runtime.PYTHON_3_7,
            code=_lambda.InlineCode(
                fh_transformer_fn_code),
            handler="index.lambda_handler",
            timeout=core.Duration.seconds(5),
            reserved_concurrent_executions=1,
            environment={
                "LOG_LEVEL": "INFO",
                "APP_ENV": "Production",
            }
        )

        # Create Custom Loggroup for Producer
        fh_transformer_fn_lg = _logs.LogGroup(
            self,
            "fhDataTransformerFnLogGroup",
            log_group_name=f"/aws/lambda/{fh_transformer_fn.function_name}",
            removal_policy=core.RemovalPolicy.DESTROY,
            retention=_logs.RetentionDays.ONE_DAY
        )

        fh_delivery_role = _iam.Role(
            self,
            "fhDeliveryRole",
            # role_name="FirehoseDeliveryRole",
            assumed_by=_iam.ServicePrincipal("firehose.amazonaws.com"),
            external_id=core.Aws.ACCOUNT_ID,
        )

        # Add permissions to allow Kinesis Fireshose to Write to S3
        roleStmt1 = _iam.PolicyStatement(
            effect=_iam.Effect.ALLOW,
            resources=[f"{fh_data_store.bucket_arn}",
                       f"{fh_data_store.bucket_arn}/*"
                       ],
            actions=[
                "s3:AbortMultipartUpload",
                "s3:GetBucketLocation",
                "s3:GetObject",
                "s3:ListBucket",
                "s3:ListBucketMultipartUploads",
                "s3:PutObject"
            ]
        )
        # roleStmt1.add_resources(
        #     fh_data_store.arn_for_objects("*")
        # )
        roleStmt1.sid = "AllowKinesisToWriteToS3"
        fh_delivery_role.add_to_policy(roleStmt1)

        # Add permissions to Kinesis Fireshose to Write to CloudWatch Logs
        roleStmt2 = _iam.PolicyStatement(
            effect=_iam.Effect.ALLOW,
            resources=[
                f"arn:aws:logs:{core.Aws.REGION}:{core.Aws.ACCOUNT_ID}:log-group:/aws/kinesisfirehose/{firehose_delivery_stream_name}:log-stream:*"
            ],
            actions=[
                "logs:PutLogEvents"
            ]
        )
        roleStmt2.sid = "AllowKinesisToWriteToCloudWatch"
        fh_delivery_role.add_to_policy(roleStmt2)

        # Add permissions to Kinesis Fireshose to Invoke Lambda for Transformations
        roleStmt3 = _iam.PolicyStatement(
            effect=_iam.Effect.ALLOW,
            resources=[
                f"{fh_transformer_fn.function_arn}"
            ],
            actions=[
                "lambda:InvokeFunction"
            ]
        )
        roleStmt3.sid = "AllowKinesisToInvokeLambda"
        fh_delivery_role.add_to_policy(roleStmt3)

        self.fh_to_s3 = _kinesis_fh.CfnDeliveryStream(
            self,
            "fhDeliveryStream",
            delivery_stream_name=f"{firehose_delivery_stream_name}",
            extended_s3_destination_configuration=_kinesis_fh.CfnDeliveryStream.ExtendedS3DestinationConfigurationProperty(
                bucket_arn=fh_data_store.bucket_arn,
                buffering_hints=_kinesis_fh.CfnDeliveryStream.BufferingHintsProperty(
                    interval_in_seconds=60,
                    size_in_m_bs=1
                ),
                compression_format="UNCOMPRESSED",
                prefix=f"sales_revenue/",
                # prefix="sales_revenue/date=!{timestamp:yyyy}-!{timestamp:MM}-!{timestamp:dd}/",
                role_arn=fh_delivery_role.role_arn,
                processing_configuration=_kinesis_fh.CfnDeliveryStream.ProcessingConfigurationProperty(
                    enabled=True,
                    processors=[
                        _kinesis_fh.CfnDeliveryStream.ProcessorProperty(
                            parameters=[
                                _kinesis_fh.CfnDeliveryStream.ProcessorParameterProperty(
                                    parameter_name="LambdaArn",
                                    parameter_value=fh_transformer_fn.function_arn,
                                )
                            ],
                            type="Lambda",
                        )
                    ]
                ),
            ),
        )

        # Restrict Transformer Lambda to be invoked by Firehose only from the stack owner account
        _lambda.CfnPermission(
            self,
            "restrictLambdaInvocationToFhInOwnAccount",
            action="lambda:InvokeFunction",
            function_name=fh_transformer_fn.function_arn,
            principal="firehose.amazonaws.com",
            source_account=core.Aws.ACCOUNT_ID,
            source_arn=self.fh_to_s3.attr_arn,
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

        output_1 = core.CfnOutput(
            self,
            "FirehoseArn",
            value=f"https://console.aws.amazon.com/firehose/home?region={core.Aws.REGION}#/details/{self.fh_to_s3.delivery_stream_name}",
            description="Produce streaming data events and push to Kinesis stream."
        )
        output_2 = core.CfnOutput(
            self,
            "FirehoseDataStore",
            value=f"https://console.aws.amazon.com/s3/buckets/{fh_data_store.bucket_name}",
            description="The firehose datastore bucket"
        )

    # properties to share with other stacks
    @property
    def get_fh_stream(self):
        return self.fh_to_s3
