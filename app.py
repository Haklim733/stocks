#!/usr/bin/env python3
import os
from aws_cdk import core
from stocks_cdk.pipelines_stack import StocksPipelineStack

S3_BUCKET = os.environ["PROD_BUCKET"]
S3_KEY = os.environ["PROD_KEY"]
USER_ARN = os.environ["PROD_USER_ARN"]
HOOK_URL = os.environ["PROD_FAIL_DEST"]
PROD_USER_ARN = os.environ["PROD_USER_ARN"]
ACCOUNT = os.environ["PROD_ACCOUNT"]
REGION = "us-east-1"

TEST = True
if TEST:
    S3_BUCKET = os.environ["TEST_BUCKET"]
    S3_KEY = os.environ["TEST_KEY"]
    USER_ARN = os.environ["TEST_USER_ARN"]
    HOOK_URL = os.environ["TEST_FAIL_DEST"]
    ACCOUNT = os.environ["TEST_ACCOUNT"]

app = core.App()

# backend_stack = SaveOptionsStack(scope=app, id='stocks-backend-saveoptions',
#                                    env={'region': 'us-east-1'})
# core.Tag.add(backend_stack, "project", 'stocks')
# core.Tag.add(backend_stack, "env", 'test')
pipeline_stack = StocksPipelineStack(scope=app, id="StocksPipelineStack")
core.Tag.add(pipeline_stack, "project", "stocks")
core.Tag.add(pipeline_stack, "env", "test")

app.synth()
