"""
construct for a lambda function with optional functionalities

    - creates:
        - Lambda function
        - CloudWatch Rule (if cron_expression arg is passed)
    - required arguments:
        - handler_code : the directory containing the lambda_function. All
        subdirectories will be deployed alongside it.
    - optional arguments:
        - managed_policies : aws managed policies to attach to the IAM role
        created to execute this function. This argument will take precedent
        over `iam_role` if both are passed (default None)
        - iam_role : an iam role to use to execute this function (default None)
        - layers : list of lambda layers to attach (default None)
        - environmental_variables : dictionary of environmental variables (
        default None)
        - duration : integer of the lambda's max execution duration,
        in seconds (default 300 seconds)
        - error_sns_topic_arn : the ARN of an SNS topic to send notification
        to if this lambda function fails (default None)
        - cron_expression : a string cron expression for when to run the
        lambda function, can be given either in a schedule or a rate*


* to construct cron expressions:
    https://docs.aws.amazon.com/AmazonCloudWatch/latest/events/ScheduledEvents.html

"""

from aws_cdk import (
    aws_events as events,
    aws_lambda as lambda_,
    aws_events_targets as targets,
    aws_sns as sns,
    aws_ssm as ssm,
    aws_lambda_destinations as destinations,
    aws_logs as logs,
    core,
)

from cdk_constants import ManagedPolicies
from .iam_role import RoleConstruct


class LambdaConstruct(core.Construct):
    """CDK Lambda Construct"""
    def __init__(self, scope: core.Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id)

        if 'managed_policies' in kwargs:
            iam_role = RoleConstruct(
                scope=scope,
                id=f'iam-{id}',
                managed_policies=kwargs.get('managed_policies') + [
                    ManagedPolicies.AWS_LAMBDA_BASIC_EXECUTION_ROLE]). \
                iam_role
        elif 'iam_role' in kwargs:
            iam_role = kwargs.get('iam_role')
        else:
            iam_role = RoleConstruct(
                scope=scope,
                id=f'iam-{id}',
                managed_policies=[ManagedPolicies.AWS_LAMBDA_BASIC_EXECUTION_ROLE]). \
                iam_role

        # access layers via /opt, access local /src directory via /var/task/src
        environmental_variables = {'PYTHONPATH': '/opt:/var/task/src'}

        layer_names = ['layer-c2dp']

        if 'layers' in kwargs:
            layer_names = layer_names + kwargs.get('layers')

        if 'reserved_concurrency' in kwargs:
            reserved_concurrency = kwargs.get('reserved_concurrency')
        else:
            reserved_concurrency = None

        layer_list = []
        for layer_parameter_name in layer_names:
            parameter_string_value = ssm.StringParameter.from_string_parameter_name(
                scope=self,
                id=f'parameter-{layer_parameter_name}',
                string_parameter_name=f'{layer_parameter_name}').string_value
            layer = lambda_.LayerVersion.from_layer_version_arn(
                scope=self,
                id=f'layer-version-{layer_parameter_name}',
                layer_version_arn=parameter_string_value)
            layer_list.append(layer)

        if 'environmental_variables' in kwargs:
            environmental_variables.update(
                kwargs.get('environmental_variables'))

        if 'duration' in kwargs:
            duration = kwargs.get('duration')
        else:
            duration = 300

        if 'memory_size' in kwargs:
            memory_size = kwargs.get('memory_size')
        else:
            memory_size = 128

        if 'error_sns_topic_arn' in kwargs:
            on_failure_topic = destinations.SnsDestination(
                sns.Topic.from_topic_arn(
                    scope=self,
                    id='snsTopic',
                    topic_arn=kwargs.get('error_sns_topic_arn')))
        else:
            on_failure_topic = None

        if 'retry_attempts' in kwargs:
            retry_attempts = kwargs.get('retry_attempts')
        else:
            retry_attempts = 0

        self.lambda_function = lambda_.Function(
            self,
            "Singleton",
            function_name=id,
            code=lambda_.Code.asset(path=kwargs.get('handler_code')),
            handler="lambda_function.lambda_handler",
            timeout=core.Duration.seconds(amount=duration),
            runtime=lambda_.Runtime.PYTHON_3_7,
            environment=environmental_variables,
            log_retention=logs.RetentionDays.ONE_MONTH,
            role=iam_role,
            memory_size=memory_size,
            retry_attempts=retry_attempts,
            layers=layer_list,
            on_failure=on_failure_topic,
            reserved_concurrent_executions=reserved_concurrency)

        if 'cron_expression' in kwargs:
            if type(kwargs.get('cron_expression')) == list:
                for index, cron_expression in enumerate(
                        kwargs.get('cron_expression')):
                    rule = events.Rule(self,
                                       f"Rule-{index}",
                                       schedule=events.Schedule.expression(
                                           expression=cron_expression))

                    rule.add_target(
                        targets.LambdaFunction(self.lambda_function))
            else:
                rule = events.Rule(
                    self,
                    "Rule",
                    schedule=events.Schedule.expression(
                        expression=kwargs.get('cron_expression')))

                rule.add_target(targets.LambdaFunction(self.lambda_function))
