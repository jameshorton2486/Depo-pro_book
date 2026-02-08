from setuptools import find_packages, setup


INSTALL_REQUIRES = [
    "anthropic>=0.40.0",
    "click>=8.1.0",
    "google-genai>=0.6.0",
    "google-generativeai>=0.8.0",
    "openai>=1.50.0",
    "python-docx>=1.1.0",
    "python-dotenv>=1.0.0",
    "rich>=13.0.0",
    "textstat>=0.7.0",
    "weasyprint>=62.0",
]

setup(
    name="bookforge",
    version="2.0.0",
    description="BookForge v2 - Multi-AI book writing pipeline",
    packages=find_packages(),
    install_requires=INSTALL_REQUIRES,
    entry_points={
        "console_scripts": [
            "bookforge=bookforge:cli",
        ]
    },
)
