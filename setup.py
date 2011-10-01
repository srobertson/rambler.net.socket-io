from setuptools import setup,find_packages

setup(
    name='rambler.net.socket-io',
    version = '0.7',
    description='Socket.IO support for Rambler',
    author='Scott Robertson',
    author_email='srobertson@codeit.com',
    packages = find_packages(),
    install_requires = ['rambler.net']
)
