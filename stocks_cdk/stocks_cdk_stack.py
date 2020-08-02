
'''this script is to create the back end process to download data using the TDAMERITRADE API '''
from pathlib import Path
import json
import os
from aws_cdk import (core, aws_lambda as _lambda, aws_iam as iam, aws_events as events, aws_s3_assets as s3assets, aws_s3 as s3,
                     aws_logs as logs, aws_events_targets as events_targets)
from cdk_constants import ManagedPolicies
import pandas as pd

S3_BUCKET = os.environ['PROD_BUCKET']
S3_KEY = os.environ['PROD_KEY']
USER_ARN = os.environ['PROD_USER_ARN']
HOOK_URL = os.environ['PROD_FAIL_DEST']
PROD_USER_ARN = os.environ['PROD_USER_ARN']

TEST = True
if TEST:
    S3_BUCKET = os.environ['TEST_BUCKET']
    S3_KEY = os.environ['TEST_KEY']
    USER_ARN = os.environ['TEST_USER_ARN']
    HOOK_URL = os.environ['TEST_FAIL_DEST']

# with open('static/options_tickers.json', 'r') as handle:
#     tickers = json.load(handle)
#     tickers.sort()

# cols_type = pd.read_csv('static/cols_types.csv')
# cols_type = cols_type.set_index('column').type.to_dict()

class StocksBackendStack(core.Stack):
    def __init__(self, *, scope: core.Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        role_policies = [
            ManagedPolicies.AMAZON_S3_FULL_ACCESS,
            # ManagedPolicies.AMAZON_SNS_FULL_ACCESS,
            ManagedPolicies.AWS_LAMBDA_BASIC_EXECUTION_ROLE
        ]

        lambda_resource = iam.ServicePrincipal(
            'lambda.amazonaws.com')

        _lambda_role = iam.Role(self,
                            id="LambdaRole",
                            assumed_by=lambda_resource,
                            managed_policies=[
                                iam.ManagedPolicy.from_aws_managed_policy_name(
                                    managed_policy_name=policy)
                                for policy in role_policies
                            ])
        # 
        #S3 Resource
        stocks_bucket = s3.Bucket(self, id="Bucket",
                                  bucket_name=S3_BUCKET, versioned=False, block_public_access=s3.BlockPublicAccess(block_public_acls=True,
                                                                                                                   block_public_policy=True,
                                                                                                                   ignore_public_acls=True,
                                                                                                                   restrict_public_buckets=True),
                                  server_access_logs_prefix='logs/',
                                  access_control=s3.BucketAccessControl.LOG_DELIVERY_WRITE
                                  )
        
        bucket_policy = iam.PolicyStatement(actions=["s3:*"],
                            resources=[stocks_bucket.bucket_arn], principals= [iam.ArnPrincipal(USER_ARN).grant_principal, iam.ArnPrincipal(PROD_USER_ARN).grant_principal],
                            sid=f'{S3_BUCKET}-USER_ACCESS')
        #allows prod user to access bucket in test
        
        # tickers = s3assets.Asset(stocks_bucket, 
        #          path=Path(__file__).resolve().parent.parent / 'options_tickers.json')
        # col_types = s3assets.Asset(stocks_bucket,
        #          path=Path(__file__).resolve().parent.parent / 'cols_type.json')
                
        #lambda layers 
        save_options_layer = _lambda.LayerVersion(self, id="LambdaPythonPackage", 
                             code=_lambda.Code.from_asset('layers/stocks_lambda_layer.zip'),
                             compatible_runtimes=[_lambda.Runtime.PYTHON_3_8],
                             description = 'python awswrangler, requests, and loguru, pandas-market-calendar packages',
                             layer_version_name = 'stocks-python-layer')
        
        vars_layer = _lambda.LayerVersion(self, id="LambdaStaticFile", 
                             code=_lambda.Code.from_asset('layers/static/'),
                             compatible_runtimes=[_lambda.Runtime.PYTHON_3_8],
                             description = 'python awswrangler, requests, and loguru, pandas-market-calendar packages',
                             layer_version_name = 'stocks-static-layer')
        
        env_vars = {'FAIL_NOTIFICATION_DEST': HOOK_URL,
                    'S3_BUCKET': S3_BUCKET,
                    'S3_KEY': S3_KEY}
        
        save_options_lambda = _lambda.Function(
            self,
            'SaveOptionsData',
            function_name='save_options_data',
            runtime=_lambda.Runtime.PYTHON_3_8,
            code=_lambda.Code.asset(path='stocks_cdk'),
            handler="lambda_save_options.lambda_handler",
            timeout=core.Duration.seconds(amount=360),
            environment=env_vars,
            log_retention=logs.RetentionDays.ONE_MONTH,
            role=_lambda_role,
            memory_size=1280,
            retry_attempts=2,
            layers=[save_options_layer, vars_layer],
            reserved_concurrent_executions=1)

        #lambda to change events scheudle -1/+1 for daylight savings time changes 
        dst_change_lambda = _lambda.Function(
            self,
            'DSTChangeLambda',
            function_name='DSTChangeLambda',
            runtime=_lambda.Runtime.PYTHON_3_8,
            code=_lambda.Code.asset(path='stocks_cdk'),
            handler="dst_change_lambda.lambda_handler",
            timeout=core.Duration.seconds(amount=120),
            environment={'FAIL_NOTIFICATION_DEST': HOOK_URL},
            log_retention=logs.RetentionDays.ONE_MONTH,
            role=_lambda_role,
            memory_size=512,
            retry_attempts=2,
            reserved_concurrent_executions=1)
        
        #scheduling lambda function
        dst_cron = {
           'spring':
               {
                   'intraday': "cron(0 14-20 ? * SUN *)", 
                   'market-open': 'cron(30 13 ? * MON-FRI *)',
                   'market-close': 'cron(45 19 ? * MON-FRI *)',
                   'dst-trigger': 'cron(0 23 ? 3 1#2 *)'
               },
            'fall':
                {
                    'intraday': 'cron(0 15-21 ? * MON-FRI *)',
                    'market-open': 'cron(30 14 ? * MON-FRI *)',
                    'market-close': 'cron(45 20 ? * MON-FRI *)',
                    'dst-trigger': 'cron(0 23 ? 11 2#1 *)'
                }
        }
        
        event_rules_d = {} 
        
        for key in dst_cron:
            for key2 in dst_cron[key]:
                description = f'{key2} ({key})'
                rule_name = f'{key}-{key2}'
                
                target = events_targets.LambdaFunction(save_options_lambda)
                
                if key2 == 'dst-trigger':
                    target = events_targets.LambdaFunction(dst_change_lambda)
               
                enable_rule = False 
                
                if key == 'spring':
                    enable_rule = True
                
                event_rule = events.Rule(scope=self,
                    id=rule_name,
                    enabled = enable_rule,
                    description=description,
                    rule_name=rule_name,
                    schedule=events.Schedule.expression(expression=dst_cron[key][key2]),
                    targets=[target])
                
                event_rules_d.update({key: {key2: event_rule}})
