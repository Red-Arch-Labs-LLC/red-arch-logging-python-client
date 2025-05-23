from setuptools import setup, find_packages

setup(
    name="redarch-logging-client",
    version="0.1.10",
    packages=find_packages(),
    install_requires=["requests", "PyJWT"],
    author="Jeremy Blair",
    author_email="jeremy@redarchlabs.com",
    description="Lightweight python log client for centralized Go logging API",
    classifiers=["Programming Language :: Python :: 3"],
)
