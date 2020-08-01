from datetime import datetime
import os
import boto3


SNS_C = boto3.client('sns')

def test_sns_topic():
    test_topic = SNS_C.create_topic(Name='test')
    SNS_C.publish(TopicArn=test_topic['TopicArn']
    )