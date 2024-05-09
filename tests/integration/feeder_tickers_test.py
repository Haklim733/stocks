# TODO: figure out integration tests using pulumi
import boto3
import json
from pathlib import Path
import random
from typing import Optional
from pulumi import Config, export
from pulumi.automation import (
    create_stack,
    create_or_select_stack,
    CommandError,
    ConfigMap,
    ConfigValue,
    EngineEvent,
    LocalWorkspace,
    LocalWorkspaceOptions,
    OpType,
    PluginInfo,
    ProjectSettings,
    PulumiCommand,
    StackSummary,
    Stack,
    StackSettings,
    StackAlreadyExistsError,
    fully_qualified_stack_name,
)

extensions = ["json", "yaml", "yml"]


def get_test_path(*paths):
    return Path(__file__).resolve().parents[2].joinpath(*paths)


def normalize_config_key(key: str, project_name: str):
    parts = key.split(":")
    if len(parts) < 2:
        return f"{project_name}:{key}"


def found_plugin(plugin_list: list[PluginInfo], name: str, version: str) -> bool:
    for plugin in plugin_list:
        if plugin.name == name and plugin.version == version:
            return True
    return False


def get_test_suffix() -> int:
    return int(100000 + random() * 900000)


def get_stack(stack_list: list[StackSummary], name: str) -> Optional[StackSummary]:
    for stack in stack_list:
        if stack.name == name:
            return stack
    return None


class TestLocalWorkspace:
    def test_project_settings(self):
        for ext in extensions:
            ws = LocalWorkspace(work_dir=get_test_path("", ext))
            settings = ws.project_settings()
            self.assertEqual(settings.name, "stocks")
            self.assertEqual(settings.runtime, "python")

    def test_stack_settings(self):
        for ext in extensions:
            ws = LocalWorkspace(work_dir=get_test_path("", ext))
            settings = ws.stack_settings("dev")
            self.assertEqual(settings.secrets_provider, "abc")
            self.assertEqual(settings.config["plain"], "plain")
            self.assertEqual(settings.config["secure"].secure, "secret")

        config = {
            "cool": "sup",
            "foo": {"secure": "thisisasecret"},
        }
        settings_with_only_config = StackSettings(config=config)
        self.assertEqual(settings_with_only_config._serialize(), {"config": config})

    def test_stack_functions(self):
        project_settings = ProjectSettings(name="python_test", runtime="python")
        ws = LocalWorkspace(project_settings=project_settings)
        stack_1_name = f"python_int_test_first_{get_test_suffix()}"
        stack_2_name = f"python_int_test_second_{get_test_suffix()}"

        # Create a stack
        ws.create_stack(stack_1_name)
        stacks = ws.list_stacks()
        stack_1 = get_stack(stacks, stack_1_name)

        # Check the stack exists
        self.assertIsNotNone(stack_1)
        # Check that it's current
        self.assertTrue(stack_1.current)


def test_feeder_tickers_lambda():
    # Create a Lambda client
    lambda_client = boto3.client("lambda")

    stack_ref = pulumi.StackReference(f"stocks/{pulumi.get_stack()}")

    # Get the stack outputs
    queue_url = stack_ref.get_output("queue_url")
    lambda_name = stack_ref.get_output("feederLambdaName").apply(lambda v: str(v))

    # Invoke the Lambda function
    response = lambda_client.invoke(
        FunctionName=lambda_name, InvocationType="RequestResponse"
    )

    assert response["ResponseMetadata"]["HTTPStatusCode"] == 200

    # Parse the response
    response_payload = json.loads(response["Payload"].read())

    # Create an SQS client
    sqs_client = boto3.client("sqs")

    # Receive messages from the SQS queue
    messages = sqs_client.receive_message(
        QueueUrl="QUEUE_URL", MaxNumberOfMessages=400  # Replace with your SQS queue URL
    )

    # Check if the messages were sent to the SQS queue
    assert "Messages" in messages
    assert len(messages["Messages"]) > 0

    # Check if the messages match the response payload
    for message in messages["Messages"]:
        assert message["Body"] == response_payload
