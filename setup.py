"""Setup configuration for AWS Cost Sentinel."""

from setuptools import setup, find_packages
from pathlib import Path

# Read long description from README
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text()

# Read requirements
requirements = (this_directory / "requirements.txt").read_text().splitlines()
requirements = [r.strip() for r in requirements if r.strip() and not r.startswith('#')]

setup(
    name="aws-cost-sentinel",
    version="1.0.0",
    author="AWS Cost Sentinel Contributors",
    author_email="realahmad001@gmail.com",
    description="Stop AWS bill surprises. Get instant alerts when your costs spike.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/ahmad0303/aws-cost-sentinel",
    project_urls={
        "Bug Tracker": "https://github.com/ahmad0303/aws-cost-sentinel/issues",
        "Documentation": "https://github.com/ahmad0303/aws-cost-sentinel/wiki",
        "Source Code": "https://github.com/ahmad0303/aws-cost-sentinel",
    },
    packages=find_packages(include=['src', 'src.*']),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: System Administrators",
        "Topic :: System :: Monitoring",
        "Topic :: Office/Business :: Financial",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.9",
    install_requires=requirements,
    extras_require={
        "dev": [
            "boto3>=1.42.0",
            "pytest>=8.0.0",
            "pytest-cov>=4.1.0",
            "moto[ce,s3,ec2,rds,sts]>=5.0.0",
            "black>=24.1.1",
            "flake8>=7.0.0",
            "mypy>=1.8.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "cost-sentinel=src.sentinel:main",
            # NOTE: sentinel-cli.py must be renamed to sentinel_cli.py
            # for this entry point to work. Hyphens are invalid in
            # Python module names.
            "sentinel=sentinel_cli:main",
        ],
    },
    include_package_data=True,
    package_data={
        "": ["config.yaml.example", ".env.example"],
    },
    keywords=[
        "aws",
        "cost",
        "monitoring",
        "alerts",
        "finops",
        "cloud",
        "budget",
        "anomaly-detection",
        "machine-learning",
    ],
    license="MIT",
    zip_safe=False,
)