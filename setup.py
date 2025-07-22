from setuptools import setup

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name='PySerialInterface',
    version='v1.0.8',
    description='SerialInterface script to communicate with devices over UART',
    long_description=long_description,
    long_description_content_type="text/markdown",
    url='https://github.com/krakul/PySerialInterface',
    packages=['PySerialInterface'],
    install_requires=[
        'dataclasses',
        'dataclasses-json',
        'pyserial'
    ],
    license='MIT',
    classifiers=[
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.6',
)
