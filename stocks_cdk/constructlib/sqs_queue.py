"""
cdk construct for an sqs queue
    -creates: a SQS Queue

    -detects whether to create a FIFO queue if '.fifo' is in the queue name
    -if the queue is FIFO, content-based deduplication is enabled

    - required arguments:
        - queue_name : the queue name

    - optional arguments:
        -dead_letter_queue_arn : the arn of the queue to target for dead letter
        queue processing (default - None)
        -visibility timeout : the default visibility timeout for messages in
        the queue, given in seconds (default - 21600 seconds, 6 hours)
        -fifo : whether the queue is a fifo queue (default - True)
        -max_receive_count : for queues that include a dead letter queue,
        the maximum number of times a message is received before being sent
        to the dead letter queue (default - 12)
"""

from aws_cdk import (
    aws_sqs as sqs,
    core,
)


class SqsQueueConstruct(core.Construct):
    """SQS Queue Construct"""
    def __init__(self, app: core.Construct, id: str, **kwargs) -> None:
        super().__init__(app, id)

        self.queue_name = kwargs.get('queue_name')

        if 'visibility_timeout' in kwargs:
            visibility_timeout = kwargs.get('visibility_timeout')
        else:
            visibility_timeout = 21600  # 6 hours

        if '.fifo' in self.queue_name:
            content_based_dedup = True
        else:
            content_based_dedup = None

        if 'dead_letter_queue_arn' in kwargs:
            if 'max_receive_count' in kwargs:
                max_receive_count = kwargs.get('max_receive_count')
            else:
                max_receive_count = 12

            dead_letter_queue = sqs.DeadLetterQueue(
                queue=sqs.Queue.from_queue_arn(
                    scope=self,
                    id='dead-letter-queue',
                    queue_arn=kwargs.get('dead_letter_queue_arn')),
                max_receive_count=max_receive_count)
        else:
            dead_letter_queue = None

        self.queue = sqs.Queue(scope=self,
                               id=self.queue_name,
                               queue_name=self.queue_name,
                               visibility_timeout=core.Duration.seconds(
                                   amount=visibility_timeout),
                               dead_letter_queue=dead_letter_queue,
                               content_based_deduplication=content_based_dedup)
