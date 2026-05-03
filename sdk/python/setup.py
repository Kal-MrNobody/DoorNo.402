from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="doorno402",
    version="0.3.0",
    author="Kal-MrNobody",
    author_email="",
    description="Security middleware for x402 payments in AI agents",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Kal-MrNobody/DoorNo.402",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.10",
    install_requires=[
        "httpx>=0.24.0",
        "web3>=6.0.0",
        "eth-account>=0.9.0",
        "colorama>=0.4.6",
        "python-dotenv>=1.0.0",
    ],
)
