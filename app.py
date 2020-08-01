#!/usr/bin/env python3
import os
from aws_cdk import core
from stocks_cdk.stocks_cdk_stack import StocksBackendStack

app = core.App()

backend_stack = StocksBackendStack(scope=app, id='stocksbackend', 
                                   env={'region': 'us-east-1'})
core.Tag.add(backend_stack, "project", 'stocks')
core.Tag.add(backend_stack, "stack", 'StocksBackendStack')
core.Tag.add(backend_stack, "env", 'test')

app.synth()
