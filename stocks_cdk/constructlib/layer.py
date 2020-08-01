"""cdk construct for a lambda layer

    - creates:
        - lambda layer version
        - string parameter to point to the lambda layer version

    - required arguments:
        - layer_code : the directory to package in the layer

    - notes:
        -deploys an uncompressed local directory to s3, which is then
        converted into a lambda layer
        -the StringParameter construct is created to avoid issues when
        updating layers. An application using the layer will read the string
        parameter to get pointed to the right layer.

"""

from datetime import datetime

from aws_cdk import (
    aws_lambda as lambda_,
    aws_ssm as ssm,
    core,
)


class LayerConstruct(core.Construct):
    """lambda layer construct

    :param id: a string of the id of the construct, used as the layer version name
    :param runtimes: a list of runtimes [OPTIONAL: default python3.7]
    :param layer_code: directory containing the uncompressed files to be used in the layer

    :returns: None
    """
    def __init__(self, scope: core.Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id)

        if 'runtimes' in kwargs:
            runtimes = kwargs.get('runtimes')
        else:
            runtimes = [lambda_.Runtime.PYTHON_3_7]

        parameter_name = f'layer-{id}'

        now = datetime.now().isoformat().split(r'.')[0]

        self.layer_version = \
            lambda_.LayerVersion(
                scope=self,
                id='layer',
                code=lambda_.Code.from_asset(
                    path=kwargs.get('layer_code'), exclude=["*.zip"]),
                compatible_runtimes=runtimes,
                description=f"deployed: {now}"
            )

        self.parameter_name = \
            ssm.StringParameter(
                scope=self,
                id='VersionArn',
                parameter_name=parameter_name,
                string_value=self.layer_version.layer_version_arn) \
                .parameter_name
