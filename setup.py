from setuptools import setup, find_packages

setup(
    name="coreBM-Variant_explorer",
    version="1.0.0",
    description="Clinical long-read sequencing (ONT) variant interpretation platform with SNV, SV, and DNA methylation profiling.",
    author="coreBM",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "flask>=2.2.0",
        "jinja2>=3.1.0",
        "werkzeug>=2.2.0",
    ],
    entry_points={
        "console_scripts": [
            "variant-explorer=variant_explorer.app:main",
        ],
    },
)
