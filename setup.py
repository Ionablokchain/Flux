from setuptools import setup, find_packages

setup(
    name="flux-lang",
    version="1.0.0",
    description="Flux – Temporal programming language for Nihilo OS",
    author="Nihilo Collective",
    packages=find_packages(),
    include_package_data=True,
    entry_points={
        "console_scripts": [
            "fluxc = flux.fluxc.cli:main",
            "tvm = flux.tvm.cli:main",
            "fluxdbg = flux.debugger.repl:main",
        ]
    },
    python_requires=">=3.12",
    install_requires=[],
    extras_require={"dev": ["pytest", "flake8"]},
)