from aws_cdk import core, aws_codedeploy as codedeploy, aws_lambda as lambda_


class LambdaStack(core.Stack):
    def __init__(self, app: core.App, id: str, **kwargs):
        super().__init__(app, id, **kwargs)

        self.lambda_code = lambda_.Code.from_cfn_parameters()

        func = lambda_.Function(self, "Lambda",
                                code=self.lambda_code,
                                handler="lambda_function.lambda_handler",
                                runtime=lambda_.Runtime.PYTHON_3_7,
                                )

        alias = lambda_.Alias(self, "LambdaAlias", alias_name="Prod",
                              version=func.latest_version)

        codedeploy.LambdaDeploymentGroup(self, "DeploymentGroup",
                                         alias=alias,
                                         deployment_config=
                                         codedeploy.LambdaDeploymentConfig.LINEAR_10_PERCENT_EVERY_1_MINUTE
                                         )
