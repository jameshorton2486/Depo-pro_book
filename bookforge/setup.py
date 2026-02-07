from setuptools import setup, find_packages

setup(
    name="bookforge",
    version="2.0.0",
    description="BookForge v2 - Multi-AI book writing pipeline",
    packages=find_packages(),
    install_requires=[],
    entry_points={
        "console_scripts": [
            "bookforge=bookforge:cli",
        ]
    },
)
