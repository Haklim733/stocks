from pulumi_aws import apigateway

# Create a REST API
rest_api = apigateway.RestApi("stocksApi")

# Create a resource
resource = apigateway.Resource(
    "MyResource",
    rest_api=rest_api.id,
    parent_id=rest_api.root_resource_id,
    path_part="mypath",
)

# Create a method
method = apigateway.Method(
    "MyMethod",
    rest_api=rest_api.id,
    resource_id=resource.id,
    http_method="GET",
    authorization="NONE",
)

# Create an integration
integration = apigateway.Integration(
    "MyIntegration",
    rest_api=rest_api.id,
    resource_id=resource.id,
    http_method=method.http_method,
    type="MOCK",
)
