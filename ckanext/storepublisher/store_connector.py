# -*- coding: utf-8 -*-

# Copyright (c) 2015 CoNWeT Lab., Universidad Politécnica de Madrid

# This file is part of CKAN Store Publisher Extension.

# CKAN Store Publisher Extension is free software: you can redistribute it and/or
# modify it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# CKAN Store Publisher Extension is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.

# You should have received a copy of the GNU Affero General Public License
# along with CKAN Store Publisher Extension.  If not, see <http://www.gnu.org/licenses/>.

import ckan.model as model
import ckan.plugins as plugins
import json
import logging
import re
import requests

from unicodedata import normalize
from requests_oauthlib import OAuth2Session

log = logging.getLogger(__name__)


def slugify(text, delim=' '):
    """Generates an slightly worse ASCII-only slug."""
    _punct_re = re.compile(r'[\t !"#$%&\'()*/<=>?@\[\\\]`{|},.:]+')
    result = []
    for word in _punct_re.split(text):
        word = normalize('NFKD', word).encode('ascii', 'ignore')
        word = word.decode('utf-8')
        if word:
            result.append(word)

    return delim.join(result)


class StoreException(Exception):
    pass


class StoreConnector(object):

    def __init__(self, config):
        self.site_url = self._get_url(config, 'ckan.site_url')
        self.store_url = self._get_url(config, 'ckan.storepublisher.store_url')
        self.repository = config.get('ckan.storepublisher.repository')

    def _get_url(self, config, config_property):
        url = config.get(config_property, '')
        url = url[:-1] if url.endswith('/') else url
        return url

    def _get_dataset_url(self, dataset):
        return '%s/dataset/%s' % (self.site_url, dataset['id'])

    def _get_resource(self, dataset):
        resource = {}
        resource['name'] = slugify('Dataset %s - ID %s' % (dataset['title'], dataset['id']))
        resource['description'] = dataset['notes']
        resource['version'] = '1.0'
        resource['content_type'] = 'dataset'
        resource['resource_type'] = 'API'
        # Open resources can be offered in Non-open Offerings
        resource['open'] = True
        resource['link'] = self._get_dataset_url(dataset)

        return resource

    def _get_offering(self, offering_info, resource):
        offering = {}
        offering['name'] = offering_info['name']
        offering['version'] = offering_info['version']
        offering['notification_url'] = '%s/api/action/dataset_acquired' % self.site_url
        offering['image'] = {
            'name': 'ckan.png',
            'data': offering_info['image_base64']
        }
        offering['related_images'] = []
        offering['resources'] = []
        offering['resources'].append(resource)
        offering['applications'] = []
        offering['offering_info'] = {
            'description': offering_info['description'],
            'pricing': {}
        }

        # Set license
        if offering_info['license_title'] or offering_info['license_description']:
            offering['offering_info']['legal'] = {
                'title': offering_info['license_title'],
                'text': offering_info['license_description']
            }

        # Set price
        if offering_info['price'] == 0.0:
            offering['offering_info']['pricing']['price_model'] = 'free'
        else:
            offering['offering_info']['pricing']['price_model'] = 'single_payment'
            offering['offering_info']['pricing']['price'] = offering_info['price']

        offering['repository'] = self.repository
        offering['open'] = offering_info['is_open']

        return offering

    def _get_tags(self, offering_info):
        new_tags = list(offering_info['tags'])
        new_tags.append('dataset')

        return {'tags': list(new_tags)}

    def _make_request(self, method, url, headers={}, data=None):

        def _get_headers_and_make_request(method, url, headers, data):
            # Include access token in the request
            usertoken = plugins.toolkit.c.usertoken
            final_headers = headers.copy()
            # Receive the content in JSON to parse the errors easily
            final_headers['Accept'] = 'application/json'
            # OAuth2Session
            oauth_request = OAuth2Session(token=usertoken)

            req_method = getattr(oauth_request, method)
            req = req_method(url, headers=final_headers, data=data)

            return req

        req = _get_headers_and_make_request(method, url, headers, data)

        # When a 401 status code is got, we should refresh the token and retry the request.
        if req.status_code == 401:
            log.info('%s(%s): returned 401. Token expired? Request will be retried with a refresehd token' % (method, url))
            plugins.toolkit.c.usertoken_refresh()
            # Update the header 'Authorization'
            req = _get_headers_and_make_request(method, url, headers, data)

        log.info('%s(%s): %s %s' % (method, url, req.status_code, req.text))

        status_code_first_digit = req.status_code / 100
        invalid_first_digits = [4, 5]

        if status_code_first_digit in invalid_first_digits:
            result = req.json()
            error_msg = result['message']
            raise Exception(error_msg)

        return req

    def _update_acquire_url(self, dataset, resource):
        # Set needed variables
        c = plugins.toolkit.c
        tk = plugins.toolkit
        context = {'model': model, 'session': model.Session,
                   'user': c.user or c.author, 'auth_user_obj': c.userobj,
                   }

        if dataset['private']:
            user_nickname = c.user
            name = resource['name'].replace(' ', '%20')
            resource_url = '%s/search/resource/%s/%s/%s' % (self.store_url, user_nickname,
                                                            name, resource['version'])

            if dataset.get('acquire_url', '') != resource_url:
                dataset['acquire_url'] = resource_url
                tk.get_action('package_update')(context, dataset)
                log.info('Acquire URL updated correctly to %s' % resource_url)

    def _generate_resource_info(self, resource):
        return {
            'provider': plugins.toolkit.c.user,
            'name': resource.get('name'),
            'version': resource.get('version')
        }

    def _get_existing_resources(self, dataset):
        dataset_url = self._get_dataset_url(dataset)
        req = self._make_request('get', '%s/api/offering/resources' % self.store_url)
        resources = req.json()

        def _valid_resources_filter(resource):
            return resource.get('state') != 'deleted' and resource.get('link', '') == dataset_url

        return filter(_valid_resources_filter, resources)

    def _get_existing_resource(self, dataset):

        valid_resources = self._get_existing_resources(dataset)

        if len(valid_resources) > 0:
            resource = valid_resources.pop(0)
            self._update_acquire_url(dataset, resource)
            return self._generate_resource_info(resource)
        else:
            return None

    def _create_resource(self, dataset):
        # Create the resource
        resource = self._get_resource(dataset)
        headers = {'Content-Type': 'application/json'}
        self._make_request('post', '%s/api/offering/resources' % self.store_url,
                           headers, json.dumps(resource))

        self._update_acquire_url(dataset, resource)

        # Return the resource
        return self._generate_resource_info(resource)

    def _rollback(self, offering_info, offering_created):

        user_nickname = plugins.toolkit.c.user

        try:
            # Delete the offering only if it was created
            if offering_created:
                self._make_request('delete', '%s/api/offering/offerings/%s/%s/%s' % (self.store_url,
                                   user_nickname, offering_info['name'], offering_info['version']))
        except Exception as e:
            log.warn('Rollback failed %s' % e)

    def delete_attached_resources(self, dataset):
        '''
        Method to delete all the resources (and offerings) that containts the given
        dataset.

        :param dataset: The dataset whose attached offerings and resources want to be
            deleted from the Store
        :type dataset: dict
        '''

        resources = self._get_existing_resources(dataset)
        user_nickname = plugins.toolkit.c.user

        for resource in resources:
            try:
                name = resource['name'].replace(' ', '%20')
                version = resource['version']
                self._make_request('delete', '%s/api/offering/resources/%s/%s/%s' %
                                             (self.store_url, user_nickname, name, version))
            except requests.ConnectionError as e:
                log.warn(e)
            except Exception as e:
                log.warn(e)

    def create_offering(self, dataset, offering_info):
        '''
        Method to create an offering in the store that will contain the given dataset.
        The method will check if there is a resource in the Store that contains the
        dataset. If so, this resource will be used to create the offering. Otherwise
        a new resource will be created.
        Once that the resource is ready, a new offering will be created and the resource
        will be bounded.

        :param dataset: The dataset that will be include in the offering
        :type dataset: dict

        :param offering_info: A dict that contains additional info for the offering: name,
            description, license, offering version, price, image
        :type offering_info: dict

        :returns: The URL of the offering that contains the dataset
        :rtype: string

        :raises StoreException: When the store cannot be connected or when the Store
            returns some errors
        '''

        user_nickname = plugins.toolkit.c.user

        log.info('Creating Offering %s' % offering_info['name'])
        offering_created = False

        # Make the request to the server
        headers = {'Content-Type': 'application/json'}

        try:
            # Get the resource. If it does not exist, it will be created
            resource = self._get_existing_resource(dataset)
            if resource is None:
                resource = self._create_resource(dataset)

            offering = self._get_offering(offering_info, resource)
            tags = self._get_tags(offering_info)
            offering_name = offering_info['name']
            offering_version = offering_info['version']

            # Create the offering
            self._make_request('post', '%s/api/offering/offerings' % self.store_url,
                               headers, json.dumps(offering))
            offering_created = True

            # Attach tags to the offerings
            self._make_request('put', '%s/api/offering/offerings/%s/%s/%s/tag' %
                                      (self.store_url, user_nickname, offering_name,
                                       offering_version),
                               headers, json.dumps(tags))

            # Publish offering
            self._make_request('post', '%s/api/offering/offerings/%s/%s/%s/publish' %
                                       (self.store_url, user_nickname, offering_name,
                                        offering_version),
                               headers, json.dumps({'marketplaces': []}))

            # Return offering URL
            name = offering_info['name'].replace(' ', '%20')
            return '%s/offering/%s/%s/%s' % (self.store_url, user_nickname, name,
                                             offering_info['version'])
        except requests.ConnectionError as e:
            log.warn(e)
            self._rollback(offering_info, offering_created)
            raise StoreException('It was impossible to connect with the Store')
        except Exception as e:
            log.warn(e)
            self._rollback(offering_info, offering_created)
            raise StoreException(e.message)
