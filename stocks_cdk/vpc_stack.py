"""
Stack to deploy a vpc stack and ecs cluster inside the vpc.

    - creates subnets in public and isolated subnets. Private subnets were
    not added here because they cost money for NAT gateways and this vpc is
    not actively being used.

"""
import os
from aws_cdk import (
    aws_ec2 as ec2,
    aws_ecs as ecs,
    core,
)

TEST_ACCOUNT = os.environ['TEST_ACCOUNT']
PROD_ACCOUNT = os.environ['PROD_ACCOUNT']

class VpcStack(core.Stack):
    def __init__(self, app: core.App, id: str, **kwargs) -> None:
        super().__init__(app, id)

        self.vpc = ec2.Vpc(
            self,
            id=id,
            cidr="10.0.0.0/16",
            max_azs=4,
            #  nat_gateways=1,
            subnet_configuration=[
                ec2.SubnetConfiguration(name="public",
                                        cidr_mask=24,
                                        reserved=False,
                                        subnet_type=ec2.SubnetType.PUBLIC),
                #    ec2.SubnetConfiguration(
                #        name="private", cidr_mask=24,
                #        reserved=False, subnet_type=ec2.SubnetType.PRIVATE),
                ec2.SubnetConfiguration(name="isolated",
                                        cidr_mask=24,
                                        reserved=False,
                                        subnet_type=ec2.SubnetType.ISOLATED),
            ],
        )

        self.cluster = ecs.Cluster(self,
                                   'Cluster',
                                   vpc=self.vpc,
                                   cluster_name='StocksEcsCluster')
        self.ecs_security_group = ec2.SecurityGroup(self,
                                                    'ecs-task-sg',
                                                    vpc=self.vpc,
                                                    allow_all_outbound=True)


app = core.App()

VpcStack(app,
         'VpcStack-test',
         env=app.node.try_get_context(TEST_ACCOUNT),
         tags=app.node.try_get_context(TEST_ACCOUNT))

VpcStack(app,
         'VpcStack-prod',
         env=app.node.try_get_context(PROD_ACCOUNT),
         tags=app.node.try_get_context(PROD_ACCOUNT))

app.synth()
