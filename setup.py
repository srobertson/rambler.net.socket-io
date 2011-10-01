from setuptools import setup,find_packages

setup(
    name='rambler.net.socket-io',
    version = '0.7',
    description='Socket.IO support for Rambler',
    author='Scott Robertson',
    author_email='srobertson@codeit.com',
   
    install_requires = ['rambler.net'],
    namespace_packages = ['rambler.net'],
    packages = find_packages(),
)
