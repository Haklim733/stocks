"""
cdk construct for an IAM role

    - creates: IAM Role
    - arguments:
        - assumed_by : the AWS service that can assume the IAM Role (default
         Lambda)
        - managed_policies : the aws managed policies to attach to the role (default
         None)
"""

from aws_cdk import (
    aws_iam as iam,
    core,
)

import cdk_constants


class RoleConstruct(core.Construct):
    """CDK IAM Construct"""
    def __init__(self, scope: core.Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id)

        if 'assumed_by' in kwargs:
            assumed_by = kwargs.get('assumed_by')
        else:
            assumed_by = iam.ServicePrincipal(
                cdk_constants.ServicePrincipals.LAMBDA_)

        self.iam_role = iam.Role(
            self,
            id=id,
            assumed_by=assumed_by,
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    managed_policy_name=policy)
                for policy in kwargs.get('managed_policies')
            ])
