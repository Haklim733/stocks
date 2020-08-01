"""
Stack to create s3 bucket for court data collection.

    - bucket name is determined based on the environment.
    - objects in buckets are versioned.
    - all other security defaults kept to ensure no public access.

"""
import os
from aws_cdk import (
    aws_s3 as s3,
    core,
)


class S3Stack(core.Stack):
    def __init__(self, app: core.App, id: str, tags: dict, **kwargs) -> None:
        super().__init__(app, id)

        if tags['stack'] == 'prod':
            bucket_name = S3_BUCKET
        elif tags['stack'] == 'test':
            bucket_name = S3_TEST_BUCKET

        s3.Bucket(self, 'bucket', bucket_name=bucket_name, versioned=True)


app = core.App()

S3Stack(app,
        'S3Stack-test',
        env=app.node.try_get_context(,
            ),
        tags=app.node.try_get_context(''))
S3Stack(app,
        'S3Stack-prod',
        env=app.node.try_get_context(''),
        tags=app.node.try_get_context(''))

app.synth()
