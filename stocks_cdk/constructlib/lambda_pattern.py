"""
cdk construct to deploy the common serverless scraper-parser system

    - fifo queues are created because they allow content-based deduplication.
        If the system queries by party name, there will often be duplication in
        different queries. Using content-based deduplication offloads the
        deduplication to the queue.

    - required arguments:
        - location: the location of the project, i.e.
            'tn-shelby-general-sessions'. This string value could include just
            the state if the project encompasses all courts within the state,
            or be more specific to a given court in the given state.
        - s3_path: the s3 path where files will be saved. This path is the
            parent directory to the subdirectories where different types of files
            will be saved (i.e., if parsed json files will be saved in the 'json'
            subdir, `s3_path` is the path to the parent directory of that `json` dir.
        - src: path to local source directory. this is the parent directory
            to the various serverless functions, queue_feeder, case_id_scraper, etc.
        - cron_expression: the cron expression to run the queue_feeder lambda function on.
        For details, see: https://docs.aws.amazon.com/AmazonCloudWatch/latest/events/ScheduledEvents.html#CronExpressions

    - optional arguments:
        - bucket: the s3 bucket where files are saved (default -
            `courtdata-test`)
        - layers: a list of names of lambda layers to include in the each
        lambda function. All functions will get all lambda layers in the
        list. ( default - ['layer-awswrangler', 'layer-bs4',
                            'layer-requests', 'layer-loguru-backoff'] )
        - concurrency: a dictionary of reserved concurrency limits for each
        lambda function. Each key-value pair should be the function type as
        the key and the limit as the value.
            example: {'queue_feeder': 1, 'case_id_scraper': 5,
            'file_scraper': 10, 'file_parser': 30}
            the values in the example are the default values.


"""
from aws_cdk import (
    aws_lambda_event_sources as lambda_event_sources,
    aws_s3 as s3,
    aws_iam as iam,
    aws_sqs as sqs,
    core,
)

from cdk_constants import ManagedPolicies

from .lambda_function import LambdaConstruct
from .sqs_queue import SqsQueueConstruct


class LambdaPatternConstruct(core.Construct):
    """cdk construct to deploy the common serverless scraper-parser system"""
    def __init__(self, app: core.Construct, id: str, **kwargs) \
            -> None:
        super().__init__(app, id)

        account = app.account
        location = kwargs.get('location')
        s3_path = kwargs.get('s3_path')
        src = kwargs.get('src')

        if kwargs.get('tags')['environment'] == 'prod':
            bucket = 'court-data'
        else:
            bucket = 'court-data-test'

        bucket_resource = s3.Bucket.from_bucket_name(self,
                                                     'bucket',
                                                     bucket_name=bucket)

        concurrency = {
            "queue_feeder": 1,
            "case_id_scraper": 5,
            "file_scraper": 10,
            "file_parser": 30
        }

        if 'concurrency' in kwargs:
            input_concurrency = kwargs.get('concurrency')
            if 'queue_feeder' in input_concurrency:
                concurrency['queue_feeder'] = input_concurrency['queue_feeder']
            if 'case_id_scraper' in input_concurrency:
                concurrency['case_id_scraper'] = input_concurrency[
                    'case_id_scraper']
            if 'file_scraper' in input_concurrency:
                concurrency['file_scraper'] = input_concurrency['file_scraper']
            if 'file_parser' in input_concurrency:
                concurrency['file_parser'] = input_concurrency['file_parser']

        duration = {
            "queue_feeder": 120,
            "case_id_scraper": 600,
            "file_scraper": 300,
            "file_parser": 300
        }

        if 'duration' in kwargs:
            input_duration = kwargs.get('duration')
            if 'queue_feeder' in input_duration:
                duration['queue_feeder'] = input_duration['queue_feeder']
            if 'case_id_scraper' in input_duration:
                duration['case_id_scraper'] = input_duration['case_id_scraper']
            if 'file_scraper' in input_duration:
                duration['file_scraper'] = input_duration['file_scraper']
            if 'file_parser' in input_duration:
                duration['file_parser'] = input_duration['file_parser']

        memory_size = {
            "queue_feeder": 128,
            "case_id_scraper": 128,
            "file_scraper": 128,
            "file_parser": 128
        }

        if 'memory_size' in kwargs:
            input_memory_size = kwargs.get('memory_size')
            if 'queue_feeder' in input_memory_size:
                memory_size['queue_feeder'] = input_memory_size['queue_feeder']
            if 'case_id_scraper' in input_memory_size:
                memory_size['case_id_scraper'] = input_memory_size[
                    'case_id_scraper']
            if 'file_scraper' in input_memory_size:
                memory_size['file_scraper'] = input_memory_size['file_scraper']
            if 'file_parser' in input_memory_size:
                memory_size['file_parser'] = input_memory_size['file_parser']

        if 'layers' in kwargs:
            layers = kwargs.get('layers')
        else:
            if kwargs.get('headless'):
                layers = [
                    'layer-loguru-backoff', 'layer-headless-chromium',
                    'layer-bs4', 'layer-requestium'
                ]
            else:
                layers = [
                    'layer-awswrangler', 'layer-bs4', 'layer-requests',
                    'layer-loguru-backoff'
                ]

        role_policies = [
            ManagedPolicies.AMAZON_S3_FULL_ACCESS,
            ManagedPolicies.AMAZON_SNS_FULL_ACCESS,
            ManagedPolicies.AMAZON_SQS_FULL_ACCESS,
        ]

        dead_letter_queue_arn = \
            f'arn:aws:sqs:us-east-1:{account}:dead-letter-queue.fifo'
        lambda_error_queue_arn = \
            f'arn:aws:sqs:us-east-1:{account}:error-queue'

        error_queue = sqs.Queue.from_queue_arn(
            self, 'error_queue_url', queue_arn=lambda_error_queue_arn)

        query_queue_construct = SqsQueueConstruct(
            self,
            id='query-queue',
            queue_name=f'{location}-query-queue.fifo',
            dead_letter_queue_arn=dead_letter_queue_arn)

        case_id_queue_construct = SqsQueueConstruct(
            self,
            id='case-id-queue',
            queue_name=f'{location}-case-id-queue.fifo',
            dead_letter_queue_arn=dead_letter_queue_arn)

        env_vars = {
            'SQS_SCRAPE_QUERY_Q': query_queue_construct.queue.queue_url,
            'SQS_ERROR_Q': error_queue.queue_url,
            'LOCATION': location
        }

        self.queue_feeder = LambdaConstruct(
            self,
            f"{location}-queue-feeder",
            managed_policies=role_policies,
            duration=duration['queue_feeder'],
            handler_code=f'{src}/queue_feeder',
            cron_expression=kwargs.get('cron_expression'),
            error_sns_topic_arn=error_queue.queue_arn,
            reserved_concurrency=concurrency['queue_feeder'],
            layers=layers,
            memory_size=memory_size['queue_feeder'],
            environmental_variables=env_vars)

        env_vars = {
            'S3_BUCKET': bucket,
            'SQS_SCRAPE_QUERY_Q': query_queue_construct.queue.queue_url,
            'SQS_SCRAPE_CASE_Q': case_id_queue_construct.queue.queue_url,
            'S3_FILINGS_PATH': f'{s3_path}/filings',
            'SQS_ERROR_Q': error_queue.queue_url,
            'LOCATION': location
        }

        self.case_id_scraper = LambdaConstruct(
            self,
            f"{location}-case-id-scraper",
            managed_policies=role_policies,
            duration=duration['case_id_scraper'],
            handler_code=f'{src}/case_id_scraper',
            error_sns_topic_arn=error_queue.queue_arn,
            reserved_concurrency=concurrency['case_id_scraper'],
            layers=layers,
            memory_size=memory_size['case_id_scraper'],
            environmental_variables=env_vars)

        self.case_id_scraper.lambda_function.add_event_source(
            lambda_event_sources.SqsEventSource(query_queue_construct.queue))

        env_vars = {
            'S3_BUCKET': bucket,
            'SQS_SCRAPE_CASE_Q': case_id_queue_construct.queue.queue_url,
            'S3_HTML_PATH': f'{s3_path}/html',
            'SQS_ERROR_Q': error_queue.queue_url,
            'LOCATION': location
        }

        self.file_scraper = LambdaConstruct(
            self,
            f"{location}-file-scraper",
            managed_policies=role_policies,
            duration=duration['file_scraper'],
            handler_code=f'{src}/file_scraper',
            error_sns_topic_arn=error_queue.queue_arn,
            reserved_concurrency=concurrency['file_scraper'],
            memory_size=memory_size['file_scraper'],
            layers=layers,
            environmental_variables=env_vars)

        self.file_scraper.lambda_function.add_event_source(
            lambda_event_sources.SqsEventSource(case_id_queue_construct.queue))

        env_vars = {
            'S3_BUCKET': bucket,
            'SQS_SCRAPE_CASE_Q': case_id_queue_construct.queue.queue_url,
            'SQS_ERROR_Q': error_queue.queue_url,
            'S3_PARSED_PATH': f'{s3_path}/json',
            'LOCATION': location
        }

        self.file_parser = LambdaConstruct(
            self,
            f"{location}-file-parser",
            managed_policies=role_policies,
            duration=duration['file_parser'],
            handler_code=f'{src}/file_parser',
            error_sns_topic_arn=error_queue.queue_arn,
            reserved_concurrency=concurrency['file_parser'],
            memory_size=memory_size['file_parser'],
            layers=layers,
            environmental_variables=env_vars)

        self.file_parser.lambda_function.add_to_role_policy(
            iam.PolicyStatement(effect=iam.Effect.ALLOW,
                                resources=[bucket_resource.bucket_arn],
                                actions=["lambda:InvokeFunction"],
                                conditions={
                                    "StringEquals": {
                                        "AWS:SourceAccount": str(account)
                                    },
                                    "ArnLike": {
                                        "AWS:SourceArn":
                                        f"arn:aws:s3:::{bucket}"
                                    }
                                }))
