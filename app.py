#!/usr/bin/env python3

from aws_cdk import core

from stocks_cdk.stocks_cdk_stack import StocksCdkStack


app = core.App()
StocksCdkStack(app, "stocks-cdk")

app.synth()
