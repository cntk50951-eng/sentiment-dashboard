"""
Sentiment Dashboard Setup
Minimal setup.py for Render compatibility
"""

from setuptools import setup, find_packages

setup(
    name="sentiment-dashboard",
    version="1.0.0",
    description="AI-Powered Investment Intelligence Platform",
    author="OpenClaw AI",
    packages=find_packages(),
    python_requires=">=3.10,<3.11",
    install_requires=[
        "fastapi==0.103.2",
        "uvicorn[standard]==0.23.2",
        "pydantic==1.10.13",
        "python-dotenv==1.0.0",
        "requests==2.31.0",
        "structlog==23.1.0",
    ],
)
