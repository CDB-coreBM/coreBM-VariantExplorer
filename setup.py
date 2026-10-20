from setuptools import setup, find_packages

setup(
    name="coreBM-Variant_explorer",
    version="1.3.0",
    description="Clinical long-read sequencing (ONT) variant interpretation platform with SNV, SV, DNA methylation profiling, and tandem repeat expansions.",
    author="coreBM",
    packages=find_packages(),
    include_package_data=True,
    package_data={
        "variant_explorer": ["data/*.json", "templates/**/*.html", "static/**/*"],
    },
    install_requires=[
        "flask>=2.2.0",
        "jinja2>=3.1.0",
        "werkzeug>=2.2.0",
        "pysam>=0.17.0",
        "numpy>=1.20.0",
        "requests>=2.25.0",
    ],
    entry_points={
        "console_scripts": [
            "variant-explorer=variant_explorer.app:main",
        ],
    },
)
