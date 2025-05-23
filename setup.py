from setuptools import setup

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name='PySerialInterface',
    version='v0.0.1',
    description='SerialInterface script to communicate with devices over UART',
    long_description=long_description,
    url='https://github.com/krakul/PySerialInterface',
    packages=['PySerialInterface'],
    install_requires=['dataclasses', 'dataclasses-json',
                      'pyserial'],
)
