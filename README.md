CKAN Store Updater [![Build Status](http://hercules.ls.fi.upm.es/jenkins/buildStatus/icon?job=ckan_storeupdater)](http://hercules.ls.fi.upm.es/jenkins/job/ckan_storeupdater/)
=====================

CKAN extension that allows users to publish datasets in the FIWARE Store (as offerings) in a simpler way. To do so, a new tab is added in the Datasets *Manage* menu that offers a form to set the basic options of the offering.

Offerings are **not** automatically published so the dataset creator must access this form and complete it in order to publish the dataset in the FIWARE Store.

**Note:** This software is intended to integrate a CKAN instance with the FIWARE Store so it won't probably work with other Stores.

Requirements
------------

* A CKAN instance able to connect to the Fi-Ware Store via HTTP(s)
* Fi-Ware Store v0.4 or higher
* [OAuth2 CKAN Extension](https://github.com/conwetlab/ckanext-oauth2/). This extension is needed since the requests sent to the Store must include the OAuth2 credentials to identify the user that is creating the offering.
* Optional: [CKAN Private Dataset Extension](https://github.com/conwetlab/ckanext-privatedatasets/)


Installation
------------
Install this extension in your CKAN is instance is as easy as intall any other CKAN extension.

* Download the source from this GitHub repo.
* Activate your virtual environment (generally by running `. /usr/lib/ckan/default/bin/activate`)
* Install the extension by running `python setup.py develop`
* Modify your configuration file (generally in `/etc/ckan/default/production.ini`) and add `storeupdater` in the `ckan.plugins` setting. 
* In the same config file, specify the location of Fi-Ware Store by adding the `ckan.storeupdater.store_url` setting.
* Restart your apache2 reserver (`sudo service apache2 restart`)
* That's All!

Tests
-----
This sofware contains a set of test to detect errors and failures. You can run this tests by running the following command:
```
nosetests --ckan --with-pylons=test.ini ckanext/storeupdater/tests/
```
**Note:** The `test.ini` file contains a link to the CKAN `test-core.ini` file. You will need to change that link to the real path of the file in your system (generally `/usr/lib/ckan/default/src/ckan/test-core.ini`). 

You can also generate coverage reports by running:
```
nosetests --ckan --with-xunit --with-pylons=test.ini ckanext/storeupdater/tests/ --with-coverage --cover-package=ckanext.storeupdater --cover-inclusive --cover-erase . --cover-xml

