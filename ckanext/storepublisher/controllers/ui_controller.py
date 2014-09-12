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
        self.site_url = config.get('ckan.site_url')
        self.store_url = config.get('ckan.storepublisher.store_url')
        self.repository = config.get('ckan.storepublisher.repository')

    def _get_resource(self, data):
        resource = {}
        resource['name'] = data['name']
        resource['description'] = data['description']
        resource['version'] = data['version']
        resource['content_type'] = 'dataset'
        resource['open'] = data['is_open']
        resource['link'] = '%s/dataset/%s' % (self.site_url, data['pkg_id'])

        return resource

    def _get_offering(self, data):
        user_nickname = plugins.toolkit.c.user

        offering = {}
        offering['name'] = data['name']
        offering['version'] = data['version']
        offering['notification_url'] = '%s/api/action/dataset_acquired' % self.site_url
        offering['image'] = {
            'name': 'ckan.png',
            'data': data['image_base64']
        }
        offering['related_images'] = []
        offering['resources'] = []
        offering['resources'].append({'provider': user_nickname, 'name': data['name'], 'version': data['version']})
        offering['applications'] = []
        offering['offering_info'] = {
            'description': data['description'],
            'pricing': {},
            'legal': {
                'title': data['license_title'],
                'text': data['license_description']
            }
        }

        # Set price
        if data['price'] == 0.0:
            offering['offering_info']['pricing']['price_model'] = 'free'
        else:
            offering['offering_info']['pricing']['price_model'] = 'single_payment'
            offering['offering_info']['pricing']['price'] = data['price']

        offering['repository'] = self.repository
        offering['open'] = data['is_open']

        return offering

    def _get_tags(self, data):
        new_tags = list(data['tags'])
        new_tags.append('dataset')

        return {'tags': list(new_tags)}

    def _make_request(self, method, url, headers={}, data=None):

        # Include access token in the request
        usertoken = plugins.toolkit.c.usertoken
        final_headers = headers.copy()
        final_headers['Authorization'] = '%s %s' % (usertoken['token_type'], usertoken['access_token'])

        req_method = getattr(requests, method)

        req = req_method(url, headers=final_headers, data=data)

        # When a 401 status code is got, we should refresh the token and retry the request.
        if req.status_code == 401:
            log.info('%s(%s): returned 401. Has the token expired? Retrieving new token and retrying...' % (method, url))
            plugins.toolkit.c.usertoken_refresh()
            # Update the header 'Authorization'
            usertoken = plugins.toolkit.c.usertoken
            final_headers = headers.copy()
            final_headers['Authorization'] = '%s %s' % (usertoken['token_type'], usertoken['access_token'])
            # Retry the request
            req = req_method(url, headers=final_headers, data=data)

        log.info('%s(%s): %s %s' % (method, url, req.status_code, req.text))

        status_code_first_digit = req.status_code / 100
        invalid_first_digits = [4, 5]

        if status_code_first_digit in invalid_first_digits:
            errors = re.findall('<error>(.*)</error>', req.text)
            error_msg = errors[0] if errors else 'Unknown Error: %s' % req.text
            raise Exception(error_msg)

        return req

    def _rollback(self, resource_created, offering_created, data):

        user_nickname = plugins.toolkit.c.user

        try:
            # Delete the offering only if it was created
            if offering_created:
                self._make_request('delete', '%s/api/offering/offerings/%s/%s/%s' % (self.store_url, user_nickname, data['name'], data['version']))
            # Delete the resource only if it was created
            if resource_created:
                self._make_request('delete', '%s/api/offering/resources/%s/%s/%s' % (self.store_url, user_nickname, data['name'], data['version']))
        except Exception as e:
            log.warn('Rollback failed %s' % e)

    def create_offering(self, data):

        user_nickname = plugins.toolkit.c.user

        log.info('Creating Offering %s' % data['name'])
        resource = self._get_resource(data)
        offering = self._get_offering(data)
        tags = self._get_tags(data)
        offering_created = resource_created = False

        # Make the request to the server
        headers = {'Content-Type': 'application/json'}

        try:
            self._make_request('post', '%s/api/offering/resources' % self.store_url, headers, json.dumps(resource))     # Create the resource
            resource_created = True
            self._make_request('post', '%s/api/offering/offerings' % self.store_url, headers, json.dumps(offering))     # Create the offering
            offering_created = True
            self._make_request('put', '%s/api/offering/offerings/%s/%s/%s/tag' % (self.store_url, user_nickname, data['name'], data['version']),
                               headers, json.dumps(tags))                                                               # Attach tags to the offering
            self._make_request('post', '%s/api/offering/offerings/%s/%s/%s/publish' % (self.store_url, user_nickname, data['name'], data['version']),
                               headers, json.dumps({'marketplaces': []}))                                               # Publish the offering

            return True         # True = Offering created correctly
        except requests.ConnectionError as e:
            log.warn(e)
            self._rollback(resource_created, offering_created, data)
            return 'It was impossible to connect with the Store'
        except Exception as e:
            log.warn(e)
            self._rollback(resource_created, offering_created, data)
            return e.message    # Return the error message

    def publish(self, id, data=None, errors=None):

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
            data = {}
            data['pkg_id'] = request.POST.get('pkg_id', '')
            data['name'] = request.POST.get('name', '')
            data['description'] = request.POST.get('description', '')
            data['license_title'] = request.POST.get('license_title', '')
            data['license_description'] = request.POST.get('license_description', '')
            data['version'] = request.POST.get('version', '')
            data['is_open'] = 'open' in request.POST
            data['update_acquire_url'] = 'update_acquire_url' in request.POST

            # Get tags
            # ''.split(',') ==> ['']
            tag_string = request.POST.get('tag_string', '')
            data['tags'] = [] if tag_string == '' else tag_string.split(',')

            # Read image
            # 'image_upload' == '' if the user has not set a file
            image_field = request.POST.get('image_upload', '')

            if image_field != '':
                data['image_base64'] = base64.b64encode(image_field.file.read())
            else:
                data['image_base64'] = LOGO_CKAN_B64

            # Convert price into float (it's given as string)
            price = request.POST.get('price', '')
            if price == '':
                data['price'] = 0.0
            else:
                try:
                    data['price'] = float(price)
                except Exception:
                    log.warn('%r is not a valid price' % price)
                    c.errors['Price'] = ['"%s" is not a valid number' % price]

            # Set offering. In this way, we recover the values introduced previosly
            # and the user does not have to introduce them again
            c.offering = data

            # Check that all the required fields are provided
            required_fields = ['pkg_id', 'name', 'version']
            for field in required_fields:
                if not data[field]:
                    log.warn('Field %r was not provided' % field)
                    c.errors[field.capitalize()] = ['This filed is required to publish the offering']

            # Private datasets cannot be offered as open offerings
            if dataset['private'] is True and data['is_open']:
                log.warn('User tried to create an open offering for a private dataset')
                c.errors['Open'] = ['Private Datasets cannot be offered as Open Offerings']

            # Public datasets cannot be offered with price
            if 'price' in data and dataset['private'] is False and data['price'] != 0.0:
                log.warn('User tried to create a paid offering for a public dataset')
                c.errors['Price'] = ['You cannot set a price to a dataset that is public since everyone can access it']

            if not c.errors:

                result = self.create_offering(data)
                if result is True:
                    # Update acquire URL (only if the user want to)
                    if data['update_acquire_url'] and 'acquire_url' in dataset:
                        user_nickname = tk.c.user
                        # Offering names can include spaces, but URLs should not include them
                        name = data['name'].replace(' ', '%20')
                        dataset['acquire_url'] = '%s/offering/%s/%s/%s' % (self.store_url, user_nickname, name, data['version'])
                        tk.get_action('package_update')(context, dataset)
                        log.info('Acquire URL updated correctly')

                    helpers.flash_success(tk._('Offering %s published correctly' % data['name']))

                    # FIX: When a redirection is performed, the success message is not shown
                    # response.status_int = 302
                    # response.location = '/dataset/%s' % id
                else:
                    c.errors['Store'] = [result]

        return tk.render('package/publish.html')
