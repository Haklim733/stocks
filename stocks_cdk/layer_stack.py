"""
Stack that deploys lambda layers from local directories:
    - the layers/ directory is not kept in the c2dp repository due to size
    constraints
"""
import os
from aws_cdk import (
    core, )
from constructlib.layer import LayerConstruct

PROD_ACCOUNT = os.environ['PROD_ACCOUNT']
TEST_ACCOUNT = os.environ['TEST_ACCOUNT']


class StocksLayerStack(core.Stack):
    """create all layers in the environment"""
    def __init__(self, scope: core.Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id)

        self.stocks_layer_construct = LayerConstruct(
            self, 'stocks', layer_code='stocks_cdk/layers/')


app = core.App()

StocksLayerStack(app,
                 'Stocks-LayerStack-test',
                 env=app.node.try_get_context(PROD_ACCOUNT),
                 tags=app.node.try_get_context(PROD_ACCOUNT))
StocksLayerStack(app,
                 'Stocks-LayerStack-prod',
                 env=app.node.try_get_context(TEST_ACCOUNT),
                 tags=app.node.try_get_context(TEST_ACCOUNT))

app.synth()
