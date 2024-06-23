import json
import pulumi
from pulumi import Config
from pulumi_aws import ecs, ec2, ecr, iam
from pulumi_docker import Image

config = Config()

# Get the MY_ENV_VAR environment variable
stage = config.require("stage")

# Create an ECR repository.
repo = ecr.Repository("stocks")

# Build and push the Docker image.
image = Image(
    "thetaDataTerminal",
    build="../docker/java",  # Path to the directory containing the Dockerfile
    image_name=repo.repository_url,
    registry={
        "server": repo.repository_url,
        "username": ecr.get_authorization_token().apply(lambda x: x.user_name),
        "password": ecr.get_authorization_token().apply(lambda x: x.password),
    },
)

default_vpc = ec2.get_vpc(default=True)
cluster = ecs.Cluster("thetaData", vpc=default_vpc.id)

# Create an ECR repository.
repo = ecr.Repository("my-repo")

# Create an IAM role that Fargate can use.
role = iam.Role(
    "thetaDataTerminal",
    assume_role_policy=json.dumps(
        {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Action": "sts:AssumeRole",
                    "Principal": {"Service": "ecs-tasks.amazonaws.com"},
                    "Effect": "Allow",
                    "Sid": "",
                }
            ],
        }
    ),
)

task_definition = ecs.TaskDefinition(
    "thetaDataTaskDef",
    family="thetatDataTaskDef",
    cpu="512",
    memory="512",
    network_mode="awsvpc",
    requires_compatibilities=["FARGATE"],
    execution_role_arn=role.arn,
    container_definitions=pulumi.Output.all(role.arn).apply(
        lambda _: json.dumps(
            [
                {
                    "name": "thetaDataTerminal",
                    "image": image.image_name,
                    "portMappings": [
                        {"containerPort": 80, "hostPort": 80, "protocol": "tcp"}
                    ],
                }
            ]
        )
    ),
)


group = ec2.SecurityGroup(
    "web-secgrp",
    description="Enable HTTP access",
    ingress=[
        {
            "protocol": "tcp",
            "from_port": 25510,
            "to_port": 25510,
            "security_groups": [lambda_endpoint.security_group_id],
        }
    ],
)

# Create a Fargate service.
fargate_service = ecs.Service(
    "thetaDataTerminal",
    cluster=cluster.arn,
    desired_count=1,
    launch_type="FARGATE",
    task_definition=task_definition.arn,
    network_configuration={
        "assign_public_ip": "true",
        "subnets": ["subnet-abcde012", "subnet-bcde012a", "subnet-fghi345a"],
        "security_groups": [group.id],
    },
    opts=pulumi.ResourceOptions(depends_on=[group]),
)

lambda_role = iam.Role(
    "lambdaRole",
    assume_role_policy=json.dumps(
        {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Action": "sts:AssumeRole",
                    "Principal": {"Service": "lambda.amazonaws.com"},
                    "Effect": "Allow",
                    "Sid": "",
                }
            ],
        }
    ),
)
