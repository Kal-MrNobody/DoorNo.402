from setuptools import setup, find_packages

setup(
    name="doorno402",
    version="0.3.0",
    packages=find_packages(),
    install_requires=[
        "web3",
        "eth-account",
        "colorama",
        "httpx",
        "python-dotenv",
    ],
)
