#!/usr/bin/env python3
"""
Stack that includes error processing mechanisms:
    - lambda function to send dead letter queue messages to slack
    - lambda function to send other error messages to slack
"""
import os
from aws_cdk import (
    core,
    aws_lambda_event_sources as lambda_event_sources,
    aws_sqs as sqs,
)

from cdk_constants import ManagedPolicies
from constructlib.lambda_function import LambdaConstruct

EMAIL = os.environ['EMAIL']
PROD_ACCOUNT = os.environ['PROD_ACCOUNT']
TEST_ACCOUNT = os.environ['TEST_ACCOUNT']


class SnsStack(core.Stack):
    def __init__(self, app: core.App, id: str, *, tags: dict,
                 **kwargs) -> None:
        super().__init__(app, id)

        maintainer_emails = [EMAIL]

        role_policies = [
            ManagedPolicies.AMAZON_SNS_FULL_ACCESS
        ]

app = core.App()

SnsStack(app,
         'SnsStack-test',
         env=,
         tags=app.node.try_get_context(TEST_ACCOUNT))

SnsStack(app,
         'SnsStack-prod',
         env=app.node.try_get_context(PROD_ACCOUNT),
         tags=app.node.try_get_context(PROD_ACCOUNT))

app.synth()
