import setuptools

with open("README.md") as fp:
    long_description = fp.read()

setuptools.setup(
    name="stocks_cdk",
    version="0.2.2",
    description=
    "An CDK Python app to download stock data using TDAMERITRADE API",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Lim Lee",
    package_dir={"": "stocks_cdk"},
    packages=setuptools.find_packages(where="stocks_cdk"),
    install_requires=[
        "aws-cdk.core==1.56.0",
    ],
    python_requires=">=3.8",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: JavaScript",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.8",
        "Topic :: Software Development :: Code Generators",
        "Topic :: Utilities",
        "Typing :: Typed",
    ],
)
