from setuptools import setup, find_packages
import sys, os

version = '0.1'

setup(
    name='ckanext-storeupdater',
    version=version,
    description="CKAN extension to publish public datasets automatically in the Fi-Ware Store (as offerings)",
    long_description='''
    ''',
    classifiers=[], # Get strings from http://pypi.python.org/pypi?%3Aaction=list_classifiers
    keywords='',
    author='Aitor Magan',
    author_email='amagan@conwet.com',
    url='',
    license='',
    packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
    namespace_packages=['ckanext', 'ckanext.storeupdater'],
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        # -*- Extra requirements: -*-
    ],
    entry_points='''
        [ckan.plugins]
        # Add plugins here, e.g.
        storeupdater=ckanext.storeupdater.plugin:StoreUpdater
    ''',
)