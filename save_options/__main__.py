import json
from pulumi import Config, FileArchive, AssetArchive, Output
from pulumi_aws import glue, iam, lambda_, scheduler, sqs, s3


config = Config()

# Get the MY_ENV_VAR environment variable
stage = config.require("stage")

dlq = sqs.Queue("stocks-trigger-deadletter", name="stocks-trigger-deadletter-queue")

dlq_redrive_policy = Output.all(dlq.arn).apply(
    lambda args: json.dumps(
        {
            "deadLetterTargetArn": args[0],
            "maxReceiveCount": 3,
        }
    )
)

trigger_queue = sqs.Queue(
    "stocksTickerQueue",
    name="tickers",
    delay_seconds=0,
    max_message_size=1024,
    message_retention_seconds=180,
    receive_wait_time_seconds=20,
    redrive_policy=dlq_redrive_policy,
    visibility_timeout_seconds=60,
    # has to be greater than the scraper function timeout
)

# Create an IAM role that the Lambda function will assume
trigger_role = iam.Role(
    "triggerLambdaRole",
    assume_role_policy=json.dumps(
        {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Action": "sts:AssumeRole",
                    "Effect": "Allow",
                    "Principal": {
                        "Service": "lambda.amazonaws.com",
                    },
                },
            ],
        }
    ),
)
queue_arn = Output.all(trigger_queue.arn).apply(lambda args: args[0])

trigger_lambda_policy = queue_arn.apply(
    lambda arn: iam.Policy(
        "triggerLambdaPolicy",
        description="PolicyLambda2Sqs",
        policy=json.dumps(
            {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Action": ["sqs:SendMessage", "sqs:Get*"],
                        "Resource": arn,
                        "Effect": "Allow",
                    },
                    {
                        "Effect": "Allow",
                        "Action": ["logs:*"],
                        "Resource": "arn:aws:logs:*:*:*",
                    },
                ],
            }
        ),
    )
)

iam.RolePolicyAttachment(
    "triggerLambdaPolicy",
    role=trigger_role.name,
    policy_arn=trigger_lambda_policy.arn,
)

# Attach the AWSLambdaBasicExecutionRole policy to the IAM role
iam.RolePolicyAttachment(
    "stocksLambdaRolePolicyAttachment",
    role=trigger_role.name,
    policy_arn="arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole",
)
iam.RolePolicyAttachment(
    "attachSqsPermissions", role=trigger_role.name, policy_arn=trigger_lambda_policy.arn
)

trigger_layer1 = lambda_.LayerVersion(
    "stocksTriggerLayerCalendar",
    layer_name="triggerLayerCalendar",
    code=AssetArchive({".": FileArchive("../tmp/trigger1.zip")}),
    # need to run scripts/upload_lambda_layers for each runtime requirements.txt
    compatible_runtimes=["python3.11"],
    description="Layer containing dependencies for trigger lambda function",
)
# layer2 = aws.lambda_.LayerVersion(
#     "stockstriggerLayerAioboto3",
#     layer_name="LayerAioboto3",
#     code=AssetArchive({".": FileArchive("../tmp/trigger2.zip")}),
#     # need to run scripts/upload_lambda_layers for each runtime requirements.txt
#     compatible_runtimes=["python3.11"],
#     description="Layer containing dependencies for trigger lambda function",
# )

# Create an AWS Lambda function
# need to upload to s3 https://github.com/pulumi/pulumi-aws-native/issues/124
trigger_function = lambda_.Function(
    "stockstriggerFunction",
    code=AssetArchive({".": FileArchive("./runtime/trigger")}),
    role=trigger_role.arn,
    handler="handler.handler",
    runtime="python3.11",
    environment={"variables": {"QUEUE_URL": trigger_queue.id, "STAGE": stage}},
    layers=[trigger_layer1.arn],
    timeout=60,
    memory_size=328,
)

scheduler_role = iam.Role(
    "schedulerRole",
    assume_role_policy=json.dumps(
        {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Action": "sts:AssumeRole",
                    "Principal": {"Service": "scheduler.amazonaws.com"},
                    "Effect": "Allow",
                    "Sid": "",
                }
            ],
        }
    ),
)

# Attach the necessary policy to the role
iam.RolePolicyAttachment(
    "schedulerRolePolicyAttachment",
    role=scheduler_role.name,
    policy_arn="arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole",
)

schedule = {
    "marketOpen": "cron(30 14 ? * MON-FRI * )",  # 9:30 AM EST
    "quarterPastOpen": "cron(45 14 ? * MON-FRI * )",  # 9:45 AM EST
    "intraday": "cron(0 15-21 ? * MON-FRI * )",  # 10 AM - 4 PM EST, every hour
    "quarterToClose": "cron(45 20 ? * MON-FRI *)",  # 3:45 PM EST
}

for event_name, cron_expression in schedule.items():
    scheduler.Schedule(
        f"stocksScheduler-{event_name}",
        name=event_name,
        flexible_time_window=scheduler.ScheduleFlexibleTimeWindowArgs(
            mode="OFF",
        ),
        schedule_expression=cron_expression,
        target=scheduler.ScheduleTargetArgs(
            arn=trigger_function.arn,
            role_arn=scheduler_role.arn,
        ),
    )

bucket_name = config.require("bucket")
if stage == "dev":
    bucket = s3.Bucket(bucket_name)
else:
    bucket = s3.Bucket.get("stocksBucket", bucket_name)


save_role = iam.Role(
    "saveOptionslambdaRole",
    assume_role_policy=json.dumps(
        {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Action": "sts:AssumeRole",
                    "Effect": "Allow",
                    "Principal": {
                        "Service": "lambda.amazonaws.com",
                    },
                },
            ],
        }
    ),
)

bucket_arn = Output.all(bucket.arn).apply(lambda args: args[0])

save_base_policy = bucket_arn.apply(
    lambda arn: iam.Policy(
        "saveLambdaPolicyBase",
        description="PolicyLambda2S3",
        policy=json.dumps(
            {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Action": ["logs:*"],
                        "Resource": "arn:aws:logs:*:*:*",
                    },
                    {
                        "Effect": "Allow",
                        "Action": ["s3:*"],
                        "Resource": arn,
                    },
                    {
                        "Effect": "Allow",
                        "Action": ["ssm:GetParameter"],
                        "Resource": "*",
                    },
                    {
                        "Effect": "Allow",
                        "Action": ["kms:Decrypt"],
                        "Resource": "*",
                    },
                ],
            }
        ),
    )
)
account = config.get("account")
if stage == "dev":
    glue_db = glue.CatalogDatabase("stocks")
else:
    glue_db = glue.CatalogDatabase.get("glueDb", f"{account}:stocks")

gluedb_arn = Output.all(glue_db.arn).apply(lambda args: args[0])

glue_db_policy = gluedb_arn.apply(
    lambda arn: iam.Policy(
        "scraperLambdaPolicyGlue",
        description="PolicyLambda2S3",
        policy=json.dumps(
            {
                "Version": "2012-10-17",
                "Statement": [
                    {"Effect": "Allow", "Action": ["glue:*"], "Resource": arn},
                ],
            }
        ),
    )
)

save_sqs_policy = queue_arn.apply(
    lambda arn: iam.Policy(
        "saveSqsPolicy",
        description="PolicySqsSaveLambda",
        policy=json.dumps(
            {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Action": ["sqs:Receive*", "sqs:DeleteMessage", "sqs:Get*"],
                        "Resource": arn,
                    },
                ],
            }
        ),
    )
)
save_dlq_policy = Output.all(dlq.arn).apply(
    lambda arn: iam.Policy(
        "saveDlqPolicy",
        description="PolicyDlqSaveLambda",
        policy=json.dumps(
            {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Action": ["sqs:Send*", "sqs:Receive*", "sqs:Get*"],
                        "Resource": arn,
                    },
                ],
            }
        ),
    )
)

iam.RolePolicyAttachment(
    "attachSaveBasePermissions",
    role=save_role.name,
    policy_arn=save_base_policy.arn,
)
iam.RolePolicyAttachment(
    "attachSaveGluePermissions",
    role=save_role.name,
    policy_arn=glue_db_policy.arn,
)
iam.RolePolicyAttachment(
    "attachSaveDlqPermissions",
    role=save_role.name,
    policy_arn=save_dlq_policy.arn,
)
iam.RolePolicyAttachment(
    "attachSaveSqsPermissions",
    role=save_role.name,
    policy_arn=save_sqs_policy.arn,
)


pandas_sdk_layer_arn = (
    "arn:aws:lambda:us-east-1:336392948345:layer:AWSSDKPandas-Python311:12"
)
save_layer = lambda_.LayerVersion(
    "saveOptionsLayer",
    layer_name="tdameritrade",
    code=AssetArchive({".": FileArchive("../tmp/tdameritrade.zip")}),
    # need to run scripts/upload_lambda_layers for each runtime requirements.txt
    compatible_runtimes=["python3.11"],
    description="Layer containing dependencies for trigger lambda function",
)
stage = config.get("stage")

dead_letter_config = lambda_.FunctionDeadLetterConfigArgs(target_arn=dlq.arn)

scraper = lambda_.Function(
    "saveOptionsFunction",
    code=AssetArchive({".": FileArchive("./runtime/save")}),
    role=save_role.arn,
    handler="handler.handler",
    runtime="python3.11",
    environment={
        "variables": {
            "STAGE": stage,
            "S3_BUCKET": bucket_name,
        }
    },
    layers=[pandas_sdk_layer_arn, save_layer.arn],
    timeout=60,
    memory_size=328,
    dead_letter_config=dead_letter_config,
)


lambda_.EventSourceMapping(
    "sourceQueue",
    event_source_arn=trigger_queue.arn,
    function_name=scraper.arn,
    enabled=True,
)


#         error_logs_lambda = _lambda.Function(
#             self,
#             "ErrorLogsLambda",
#             function_name="ErrorLogsLambda",
#             runtime=_lambda.Runtime.PYTHON_3_8,
#             code=_lambda.Code.asset(path="stocks_cdk/filter_cwlogs/"),
#             handler="lambda_function.lambda_handler",
#             timeout=Duration.seconds(amount=60),
#             environment={"SLACK_URL": hook_url, "SLACK_CHANNEL": slack_channel},
#             log_retention=logs.RetentionDays.ONE_MONTH,
#             role=_lambda_role,
#             memory_size=192,
#             layers=[requests_layer],
#             retry_attempts=0,
#             reserved_concurrent_executions=10,
#         )

#         logs.SubscriptionFilter(
#             self,
#             "SaveOptions-Error-Logs",
#             log_group=save_options_lambda.log_group,
#             destination=log_dest.LambdaDestination(error_logs_lambda),
#             filter_pattern=logs.FilterPattern.any_term("?ERROR ?CRITICAL"),
#         )

#         logs.SubscriptionFilter(
#             self,
#             "DST-Error-Logs",
#             log_group=dst_change_lambda.log_group,
#             destination=log_dest.LambdaDestination(error_logs_lambda),
#             filter_pattern=logs.FilterPattern.any_term("ERROR"),
#         )
