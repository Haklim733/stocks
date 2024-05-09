""" requires zip to be installed on the machine"""

from pathlib import Path
import subprocess as sp
from typing import Any, Optional
import boto3
from mypy_boto3_lambda import LambdaClient
from mypy_boto3_ssm import SSMClient


def dl_packages(
    zip_dir: str, path_to_req: str, files: Optional[list[str]] = None
) -> None:
    """
    downloads python packages  to zip_dir
    files: local modules that should be part of the layer
    """
    sp.run([f"rm -rf {zip_dir}"], shell=True)

    print(f"Creating a folder named python at {zip_dir}")
    Path(zip_dir).mkdir(parents=True, exist_ok=True)

    sp.run(
        [
            f"poetry run pip3 install -r { path_to_req } \
                --platform manylinux2014_x86_64 \
                --target={zip_dir} --upgrade --python-version 3.11 \
                --only-binary=:all:"
        ],
        shell=True,
    )

    if files:
        for file in files:
            sp.run([f"cp -r {file} {zip_dir}"], shell=True)


def zip_package(zip_dir: str, save_path: str) -> None:
    if Path(save_path).exists():
        sp.run([f"rm {save_path}"], shell=True)

    sp.run([f"zip -r {save_path} python"], shell=True, cwd=zip_dir)


def upload_packages(zipfile_path: str, bucket: str, path_to_save: str) -> Any:
    s3 = boto3.client("s3")
    s3.upload_file(zipfile_path, bucket, path_to_save)


def upload_layer(
    layer_name: str, bucket: str, key: str, region: str, **kwargs: Any
) -> Any:
    client: LambdaClient = boto3.client("lambda", region_name=region)
    response = client.publish_layer_version(
        LayerName=layer_name,
        Description="layer for use to save tables to Box",
        Content={
            "S3Bucket": bucket,
            "S3Key": key,
        },
        CompatibleRuntimes=["python3.9", "python3.10", "python3.11"],
        CompatibleArchitectures=[
            "x86_64",
        ],
    )
    return response


def upload_ssm(
    *, client: SSMClient, param_name: str, contents: str, description: str
) -> None:
    client.put_parameter(
        Name=param_name,
        Description=description,
        Value=contents,
        Type="String",
        Overwrite=True,
    )


if __name__ == "__main__":
    project = "stocks"
    project_root = Path(__file__).resolve().parents[1]
    zip_dir = Path(__file__).resolve().parents[1].joinpath("tmp/python")
    save_zip_path = project_root.joinpath("tmp/tdameritrade.zip").as_posix()

    dl_packages(
        zip_dir=zip_dir.as_posix(),
        path_to_req="",
        files=["stocks/tdameritrade.py"],
    )
    zip_package(zip_dir=zip_dir.parent.as_posix(), save_path=save_zip_path)

    # bucket = "dev-mytdameritrade"
    # key = "runtime/feeder_tickers/layer.zip"

    # upload_packages(zipfile_path=save_zip_path, bucket=bucket, path_to_save=key)

    # res = upload_layer(
    #     layer_name=f"{project}-lambda", bucket=bucket, key=key, region="us-east-1"
    # )
    # version_arn = res["LayerVersionArn"]
    # ssm_c = boto3.client("ssm", region_name="us-east-1")
    # upload_ssm(
    #     client=ssm_c,
    #     param_name=f"/{project}/custom-lambda-layer",
    #     contents=version_arn,
    #     description="latest layer version arn for use",
    # )
