import json
import os
from zipfile import ZipFile
from typing import List, Dict
import codecs
from datetime import datetime, timedelta
import boto3
import botocore

CONFIG = botocore.config.Config(retries={'max_attempts': 1},
                                s3={'addressing_style': 'path'},
                                region_name='us-east-1')


class LocalStackLambda:
    def get_client():
        return boto3.client('lambda',
                            aws_access_key_id='',
                            aws_secret_access_key='',
                            region_name='us-east-1',
                            endpoint_url='http://localhost:4574',
                            config=CONFIG)

    def deploy_lambda(*, function_name: str, zip_file_path: str, role: str,
                      env_vars: Dict):

        with open(zip_file_path, 'rb') as f:
            zipped_code = f.read()

        lambda_client = LocalStackLambda.get_client()

        lambda_client.create_function(FunctionName=function_name,
                                      Runtime='python3.7',
                                      Role=role,
                                      Handler='lambda_function.lambda_handler',
                                      Code={'ZipFile': zipped_code},
                                      Environment={'Variables': env_vars})

    def get_function_arn(function_name):
        lambda_client = LocalStackLambda.get_client()
        resp = lambda_client.list_functions()
        for function in resp['Functions']:
            if function['FunctionName'] == function_name:
                return function['FunctionArn']

    def delete_lambda(function_name):
        lambda_client = LocalStackLambda.get_client()
        lambda_client.delete_function(FunctionName=function_name)

    def invoke_function_and_get_message(function_name):
        lambda_client = LocalStackLambda.get_client()
        response = lambda_client.invoke(FunctionName=function_name,
                                        InvocationType='RequestResponse')
        return json.loads(response['Payload'].read().decode('utf-8'))


class LocalStackS3:
    def get_client():
        return boto3.client('s3',
                            aws_access_key_id='',
                            aws_secret_access_key='',
                            region_name='us-east-1',
                            endpoint_url='http://localhost:4572',
                            config=CONFIG)

    def create_bucket(*, bucket: str):
        s3_c = LocalStackS3.get_client()
        buckets = [x['Name'] for x in s3_c.list_buckets()['Buckets']]

        if bucket in buckets:
            LocalStackS3.delete_bucket(bucket)

        s3_c.create_bucket(Bucket=bucket)

    def create_notification(*, bucket, function_arn, events: List[str]):
        s3_c = LocalStackS3.get_client()
        s3_c.put_bucket_notification_configuration(
            Bucket=bucket,
            NotificationConfiguration={
                'LambdaFunctionConfigurations': [{
                    'Id': 'test-event',
                    'LambdaFunctionArn': function_arn,
                    'Events': events,
                    'Filter': {
                        'Key': {
                            'FilterRules': [
                                {
                                    'Name': 'prefix',
                                    'Value': 'html/'
                                },
                            ]
                        }
                    }
                }]
            })

    def upload_object(*, path_to_file: str, bucket: str, key: str):
        s3_c = LocalStackS3.get_client()

        with codecs.open(path_to_file, "r", "utf-8") as handle:
            file_to_upload = handle.read()

        get_resp = s3_c.put_object(Bucket=bucket, Body=file_to_upload, Key=key)

    def list_buckets():
        s3_c = LocalStackS3.get_client()
        resp = s3_c.list_buckets()
        if 'Contents' in resp:
            return resp['Contents']

    def list_bucket_objects(bucket_name):
        s3_c = LocalStackS3.get_client()
        resp = s3_c.list_objects_v2(Bucket=bucket_name)
        if 'Contents' in resp:
            return resp['Contents']

    def delete_bucket(bucket_name):
        s3_client = LocalStackS3.get_client()
        bucket_objects = LocalStackS3.list_bucket_objects(bucket_name)
        if bucket_objects:
            for key in bucket_objects:
                s3_client.delete_object(Bucket=bucket_name, Key=key['Key'])

        s3_client.delete_bucket(Bucket=bucket_name)


class LocalStackSQS:
    def get_client():
        return boto3.client('sqs',
                            aws_access_key_id='',
                            aws_secret_access_key='',
                            region_name='us-east-1',
                            endpoint_url='http://localhost:4576',
                            config=CONFIG)

    def create_queue():
        sqs_c = LocalStackSQS.get_client()
        sqs_c.create_queue()


class LocalStackCloudwatch:
    def get_cloudwatch_client():

        return boto3.client('cloudwatch',
                            aws_access_key_id='',
                            aws_secret_access_key='',
                            region_name='us-east-1',
                            endpoint_url='http://localhost:4582',
                            config=CONFIG)


class LocalStackCloudwatchLogs:
    def get_cwlogs_client():

        return boto3.client('logs',
                            aws_access_key_id='',
                            aws_secret_access_key='',
                            region_name='us-east-1',
                            endpoint_url='http://localhost:4586',
                            config=CONFIG)

    def get_log_groups():

        cwlogs_c = LocalStackCloudwatchLogs.get_cwlogs_client()
        return cwlogs_c.describe_log_groups()

    def get_log_stream(log_group: str):

        cwlogs_c = LocalStackCloudwatchLogs.get_cwlogs_client()
        return cwlogs_c.describe_log_streams(logGroupName=log_group)

    def query(*, log_group: str, query_string: 'str'):
        cwlogs_c = LocalStackCloudwatchLogs.get_cwlogs_client()

        now = datetime.now()
        yesterday = now - timedelta(days=1)
        epoch_time_start = int(datetime.timestamp(yesterday))
        epoch_time_end = int(datetime.timestamp(now))

        response = cwlogs_c.start_query(logGroupName=log_group,
                                        startTime=epoch_time_start,
                                        endTime=epoch_time_end,
                                        queryString=query_string)


class LocalStackIAM:
    def get_iam_client():
        return boto3.client('iam',
                            aws_access_key_id='',
                            aws_secret_access_key='',
                            region_name='us-east-1',
                            endpoint_url='http://localhost:4593',
                            config=CONFIG)

    def get_role(*, role_name):
        iam_c = LocalStackIAM.get_iam_client()

        try:
            role = iam_c.get_role(role_name)
        except:
            role = None
        return role

    def create_role(*, role_name, policy):
        iam_c = LocalStackIAM.get_iam_client()

        try:
            LocalStackIAM.get_role_arn(role_name=role_name)
        except:
            iam_c.create_role(RoleName=role_name,
                              AssumeRolePolicyDocument=policy)

    def get_role_arn(*, role_name):
        iam_c = LocalStackIAM.get_iam_client()
        return iam_c.get_role(RoleName=role_name)['Role']['Arn']
