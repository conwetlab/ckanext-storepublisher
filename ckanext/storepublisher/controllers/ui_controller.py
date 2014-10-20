# -*- coding: utf-8 -*-

# Copyright (c) 2014 CoNWeT Lab., Universidad Politécnica de Madrid

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

import base64
import ckan.lib.base as base
import ckan.lib.helpers as helpers
import ckan.model as model
import ckan.plugins as plugins
import json
import logging
import os
import re
import requests

from ckan.common import request
from pylons import config

log = logging.getLogger(__name__)

__dir__ = os.path.dirname(os.path.abspath(__file__))
filepath = os.path.join(__dir__, '../assets/logo-ckan.png')

with open(filepath, 'rb') as f:
    LOGO_CKAN_B64 = base64.b64encode(f.read())


class PublishControllerUI(base.BaseController):

    def __init__(self, name=None):
        self.site_url = self._get_url('ckan.site_url')
        self.store_url = self._get_url('ckan.storepublisher.store_url')
        self.repository = config.get('ckan.storepublisher.repository')

    def _get_url(self, config_property):
        url = config.get(config_property)
        url = url[:-1] if url.endswith('/') else url
        return url

    def _get_dataset_url(self, dataset):
        return '%s/dataset/%s' % (self.site_url, dataset['id'])

    def _get_resource(self, dataset):
        resource = {}
        resource['name'] = 'Dataset %s - ID %s' % (dataset['title'], dataset['id'])
        resource['description'] = dataset['notes']
        resource['version'] = '1.0'
        resource['content_type'] = 'dataset'
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
            'pricing': {},
            'legal': {
                'title': offering_info['license_title'],
                'text': offering_info['license_description']
            }
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
            final_headers['Authorization'] = '%s %s' % (usertoken['token_type'], usertoken['access_token'])

            req_method = getattr(requests, method)
            req = req_method(url, headers=final_headers, data=data)

            return req

        req = _get_headers_and_make_request(method, url, headers, data)

        # When a 401 status code is got, we should refresh the token and retry the request.
        if req.status_code == 401:
            log.info('%s(%s): returned 401. Has the token expired? Retrieving new token and retrying...' % (method, url))
            plugins.toolkit.c.usertoken_refresh()
            # Update the header 'Authorization'
            req = _get_headers_and_make_request(method, url, headers, data)

        log.info('%s(%s): %s %s' % (method, url, req.status_code, req.text))

        status_code_first_digit = req.status_code / 100
        invalid_first_digits = [4, 5]

        if status_code_first_digit in invalid_first_digits:
            errors = re.findall('<error>(.*)</error>', req.text)
            error_msg = errors[0] if errors else 'Unknown Error: %s' % req.text
            raise Exception(error_msg)

        return req

    def _generate_resource_info(self, resource):
        return {
            'provider': plugins.toolkit.c.user,
            'name': resource.get('name'),
            'version': resource.get('version')
        }

    def _get_existing_resource(self, dataset):
        dataset_url = self._get_dataset_url(dataset)
        req = self._make_request('get', '%s/api/offering/resources' % self.store_url)
        resources = req.json()

        def _valid_resources_filter(resource):
            return resource.get('state') != 'deleted' and resource.get('link', '') == dataset_url

        valid_resources = filter(_valid_resources_filter, resources)

        if len(valid_resources) > 0:
            resource = valid_resources.pop(0)
            return self._generate_resource_info(resource)
        else:
            return None

    def _create_resource(self, dataset):
        # Set needed variables
        c = plugins.toolkit.c
        tk = plugins.toolkit
        context = {'model': model, 'session': model.Session,
                   'user': c.user or c.author, 'auth_user_obj': c.userobj,
                   }

        # Create the resource
        resource = self._get_resource(dataset)
        headers = {'Content-Type': 'application/json'}
        self._make_request('post', '%s/api/offering/resources' % self.store_url, headers, json.dumps(resource))

        # Update the Acquire URL automatically
        user_nickname = c.user
        name = resource['name'].replace(' ', '%20')
        resource_url = '%s/search/resource/%s/%s/%s' % (self.store_url, user_nickname, name, resource['version'])
        dataset['acquire_url'] = resource_url
        tk.get_action('package_update')(context, dataset)
        log.info('Acquire URL updated correctly to %s' % resource_url)

        # Return the resource
        return self._generate_resource_info(resource)

    def _rollback(self, offering_info, offering_created):

        user_nickname = plugins.toolkit.c.user

        try:
            # Delete the offering only if it was created
            if offering_created:
                self._make_request('delete', '%s/api/offering/offerings/%s/%s/%s' % (self.store_url, user_nickname, offering_info['name'], offering_info['version']))
        except Exception as e:
            log.warn('Rollback failed %s' % e)

    def create_offering(self, dataset, offering_info):

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
            self._make_request('post', '%s/api/offering/offerings' % self.store_url, headers, json.dumps(offering))
            offering_created = True
            # Attach tags to the offerings
            self._make_request('put', '%s/api/offering/offerings/%s/%s/%s/tag' % (self.store_url, user_nickname, offering_name, offering_version),
                               headers, json.dumps(tags))
            # Publish offering
            self._make_request('post', '%s/api/offering/offerings/%s/%s/%s/publish' % (self.store_url, user_nickname, offering_name, offering_version),
                               headers, json.dumps({'marketplaces': []}))

            # True = Offering created correctly
            return True
        except requests.ConnectionError as e:
            log.warn(e)
            self._rollback(offering_info, offering_created)
            return 'It was impossible to connect with the Store'
        except Exception as e:
            log.warn(e)
            self._rollback(offering_info, offering_created)
            return e.message    # Return the error message

    def publish(self, id, offering_info=None, errors=None):

        c = plugins.toolkit.c
        tk = plugins.toolkit
        context = {'model': model, 'session': model.Session,
                   'user': c.user or c.author, 'auth_user_obj': c.userobj,
                   }

        # Check that the user is able to update the dataset.
        # Otherwise, he/she won't be able to publish the offering
        try:
            tk.check_access('package_update', context, {'id': id})
        except tk.NotAuthorized:
            log.warn('User %s not authorized to publish %s in the FIWARE Store' % (c.user, id))
            tk.abort(401, tk._('User %s not authorized to publish %s') % (c.user, id))

        # Get the dataset and set template variables
        # It's assumed that the user can view a package if he/she can update it
        dataset = tk.get_action('package_show')(context, {'id': id})
        c.pkg_dict = dataset
        c.errors = {}

        # Tag string is needed in order to set the list of tags in the form
        if 'tag_string' not in c.pkg_dict:
            tags = [tag['name'] for tag in c.pkg_dict.get('tags', [])]
            c.pkg_dict['tag_string'] = ','.join(tags)

        # when the data is provided
        if request.POST:
            offering_info = {}
            offering_info['pkg_id'] = request.POST.get('pkg_id', '')
            offering_info['name'] = request.POST.get('name', '')
            offering_info['description'] = request.POST.get('description', '')
            offering_info['license_title'] = request.POST.get('license_title', '')
            offering_info['license_description'] = request.POST.get('license_description', '')
            offering_info['version'] = request.POST.get('version', '')
            offering_info['is_open'] = 'open' in request.POST

            # Get tags
            # ''.split(',') ==> ['']
            tag_string = request.POST.get('tag_string', '')
            offering_info['tags'] = [] if tag_string == '' else tag_string.split(',')

            # Read image
            # 'image_upload' == '' if the user has not set a file
            image_field = request.POST.get('image_upload', '')

            if image_field != '':
                offering_info['image_base64'] = base64.b64encode(image_field.file.read())
            else:
                offering_info['image_base64'] = LOGO_CKAN_B64

            # Convert price into float (it's given as string)
            price = request.POST.get('price', '')
            if price == '':
                offering_info['price'] = 0.0
            else:
                try:
                    offering_info['price'] = float(price)
                except Exception:
                    log.warn('%r is not a valid price' % price)
                    c.errors['Price'] = ['"%s" is not a valid number' % price]

            # Set offering. In this way, we recover the values introduced previosly
            # and the user does not have to introduce them again
            c.offering = offering_info

            # Check that all the required fields are provided
            required_fields = ['pkg_id', 'name', 'version']
            for field in required_fields:
                if not offering_info[field]:
                    log.warn('Field %r was not provided' % field)
                    c.errors[field.capitalize()] = ['This filed is required to publish the offering']

            # Private datasets cannot be offered as open offerings
            if dataset['private'] is True and offering_info['is_open']:
                log.warn('User tried to create an open offering for a private dataset')
                c.errors['Open'] = ['Private Datasets cannot be offered as Open Offerings']

            # Public datasets cannot be offered with price
            if 'price' in offering_info and dataset['private'] is False and offering_info['price'] != 0.0:
                log.warn('User tried to create a paid offering for a public dataset')
                c.errors['Price'] = ['You cannot set a price to a dataset that is public since everyone can access it']

            if not c.errors:

                result = self.create_offering(dataset, offering_info)
                if result is True:

                    user_nickname = tk.c.user
                    # Offering names can include spaces, but URLs should not include them
                    name = offering_info['name'].replace(' ', '%20')
                    offering_url = '%s/offering/%s/%s/%s' % (self.store_url, user_nickname, name, offering_info['version'])

                    helpers.flash_success(tk._('Offering <a href="%s" target="_blank">%s</a> published correctly.' %
                                               (offering_url, offering_info['name'])), allow_html=True)

                    # FIX: When a redirection is performed, the success message is not shown
                    # response.status_int = 302
                    # response.location = '/dataset/%s' % id
                else:
                    c.errors['Store'] = [result]

        return tk.render('package/publish.html')
