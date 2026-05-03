from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="doorno402",
    version="0.4.0",
    description="The security layer your agent needs — x402 payment middleware",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Kal-MrNobody",
    url="https://github.com/Kal-MrNobody/DoorNo.402",
    packages=find_packages(),
    python_requires=">=3.10",
    install_requires=[
        "httpx>=0.24.0",
        "web3>=6.0.0",
        "eth-account>=0.9.0",
        "colorama>=0.4.6",
        "python-dotenv>=1.0.0",
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
