"""cdk construct for a fargate task definition
    - creates:
        - IAM role to execute the task
        - Task Definition
        - s3 Docket Image Asset from a local directory
        - Adds docker image to task definition as a container
        - Adds event rule to schedule the task definition
    - required arguments:
        - script_path : the path to the directory to deploy in the task
        definition
        - sns_topic : an SNS topic construct to send errors to
        - schedule : a cron expression for the CloudWatch rule to use to
        trigger a task using the task definition
        - cluster : the ecs cluster to place the task in
        - ecs_security_group : the security group to apply to the task

"""

from cdk_constants import ManagedPolicies, ServicePrincipals

from aws_cdk import (
    aws_ecs as ecs,
    aws_ecr_assets as ecr_assets,
    aws_iam as iam,
    aws_events as events,
    aws_events_targets as events_targets,
    core,
)

from .iam_role import RoleConstruct


class FargateTaskDefinitionConstruct(core.Construct):
    """cdk construct for Elastic Container Service Fargate Task Definition"""
    def __init__(self, app: core.Construct, id: str, **kwargs) -> None:
        super().__init__(app, id)

        iam_role = RoleConstruct(
            scope=self,
            id='role',
            assumed_by=iam.ServicePrincipal(ServicePrincipals.ECS_TASKS),
            managed_policies=[ManagedPolicies.AMAZON_S3_FULL_ACCESS])\
            .iam_role

        self.task_definition = ecs.FargateTaskDefinition(scope=self,
                                                         id='task_definition',
                                                         task_role=iam_role)

        # build a new docker image and push to Elastic Container Registry
        self.docker_image_asset = ecr_assets.DockerImageAsset(
            scope=self,
            id='image_asset',
            directory=
            '../src',  # points to the directory containing `Dockerfile`
            build_args={'SCRIPTPATH': kwargs.get('script_path')}  # points to
            # the task specific source code
        )

        # get the image from the built docker image asset
        self.docker_image = ecs.ContainerImage.from_docker_image_asset(
            asset=self.docker_image_asset)

        # add container to task definition
        self.task_definition.add_container(
            id='container',
            image=self.docker_image,
            logging=ecs.LogDriver.aws_logs(stream_prefix='fargatetask'),
            environment={'sns_topic': kwargs.get('sns_topic').topic_name})

        kwargs.get('sns_topic').grant_publish(self.task_definition.task_role)

        kwargs.get('sns_topic').grant_publish(self.task_definition.task_role)

        events.Rule(scope=self,
                    id="rule",
                    description="trigger for fargate task",
                    enabled=True,
                    schedule=kwargs.get('schedule'),
                    targets=[
                        events_targets.EcsTask(
                            cluster=kwargs.get('cluster'),
                            task_definition=self.task_definition,
                            security_group=kwargs.get('ecs_security_group'),
                        )
                    ])
