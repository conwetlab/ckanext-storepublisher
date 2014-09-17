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

import ckanext.storepublisher.controllers.ui_controller as controller
import base64
import json
import os
import unittest

from mock import MagicMock
from nose_parameterized import parameterized


OFFERING_INFO_BASE = {
    'pkg_id': 'identifier',
    'name': 'Offering 1',
    'description': 'Dataset description. This can be a very long field and can include markdown syntax',
    'version': '1.7',
    'tags': ['tag1', 'tag2', 'tag3'],
    'license_title': 'Creative Commons',
    'license_description': 'This is an example description',
    'price': 1,
    'is_open': True,
    'image_base64': 'IMGB4/png/data'
}
EXCEPTION_MSG = 'Exception Message'
MISSING_ERROR = 'This filed is required to publish the offering'
CONNECTION_ERROR_MSG = 'It was impossible to connect with the Store'
BASE_SITE_URL = 'https://localhost:8474'
BASE_STORE_URL = 'https://store.example.com:7458'

# Need to be defined here, since it will be used as tests parameter
ConnectionError = controller.requests.ConnectionError

__dir__ = os.path.dirname(os.path.abspath(__file__))
filepath = os.path.join(__dir__, '../assets/logo-ckan.png')

with open(filepath, 'rb') as f:
    LOGO_CKAN_B64 = base64.b64encode(f.read())


class UIControllerTest(unittest.TestCase):

    def setUp(self):

        # Mocks
        self._toolkit = controller.plugins.toolkit
        controller.plugins.toolkit = MagicMock()
        controller.plugins.toolkit.NotAuthorized = self._toolkit.NotAuthorized

        self._model = controller.model
        controller.model = MagicMock()

        self._helpers = controller.helpers
        controller.helpers = MagicMock()

        self._base64 = controller.base64
        controller.base64 = MagicMock()

        self._requests = controller.requests
        controller.requests = MagicMock()
        controller.requests.ConnectionError = ConnectionError    # Recover Exception

        self._request = controller.request
        controller.request = MagicMock()

        self._config = controller.config
        controller.config = {
            'ckan.site_url': BASE_SITE_URL,
            'ckan.storepublisher.store_url': BASE_STORE_URL,
            'ckan.storepublisher.repository': 'Example Repo'
        }

        # Create the plugin
        self.instanceController = controller.PublishControllerUI()
        
        # Save controller functions since it will be mocked in some tests
        self._make_request = self.instanceController._make_request
        self._rollback = self.instanceController._rollback
        self._get_resource = self.instanceController._get_resource
        self._get_offering = self.instanceController._get_offering
        self._get_tags = self.instanceController._get_tags
        self._create_offering = self.instanceController.create_offering

    def tearDown(self):
        controller.plugins.toolkit = self._toolkit
        controller.requests = self._requests
        controller.base64 = self._base64
        controller.request = self._request
        controller.model = self._model
        controller.helper = self._helpers
        controller.config = self._config

        # Restore controller functions
        self.instanceController._make_request = self._make_request
        self.instanceController._rollback = self._rollback
        self.instanceController.create_offering = self._create_offering
        self.instanceController._get_resource = self._get_resource
        self.instanceController._get_offering = self._get_offering
        self.instanceController._get_tags = self._get_tags

    @parameterized.expand([
        ('%s' % BASE_SITE_URL,  '%s' % BASE_STORE_URL),
        ('%s/' % BASE_SITE_URL, '%s' % BASE_STORE_URL),
        ('%s' % BASE_SITE_URL,  '%s/' % BASE_STORE_URL),
        ('%s/' % BASE_SITE_URL, '%s/' % BASE_STORE_URL)
    ])
    def test_init(self, site_url, store_url):

        controller.config = {
            'ckan.site_url': site_url,
            'ckan.storepublisher.store_url': store_url,
            'ckan.storepublisher.repository': 'Example Repo'
        }

        instance = controller.PublishControllerUI()
        self.assertEquals(BASE_SITE_URL, instance.site_url)
        self.assertEquals(BASE_STORE_URL, instance.store_url)

    def test_get_resource(self):
        resource = self.instanceController._get_resource(OFFERING_INFO_BASE)

        # Check the values
        self.assertEquals(OFFERING_INFO_BASE['name'], resource['name'])
        self.assertEquals(OFFERING_INFO_BASE['description'], resource['description'])
        self.assertEquals(OFFERING_INFO_BASE['version'], resource['version'])
        self.assertEquals('dataset', resource['content_type'])
        self.assertEquals(OFFERING_INFO_BASE['is_open'], resource['open'])
        self.assertEquals('%s/dataset/%s' % (BASE_SITE_URL, OFFERING_INFO_BASE['pkg_id']), resource['link'])

    @parameterized.expand([
        (0,),
        (1,)
    ])
    def test_get_offering(self, price):
        user_nickname = 'smg'
        controller.plugins.toolkit.c.user = user_nickname
        offering_info = OFFERING_INFO_BASE.copy()
        offering_info['price'] = price
        offering = self.instanceController._get_offering(offering_info)

        # Check the values
        self.assertEquals(OFFERING_INFO_BASE['name'], offering['name'])
        self.assertEquals(OFFERING_INFO_BASE['version'], offering['version'])
        self.assertEquals('ckan.png', offering['image']['name'])
        self.assertEquals(OFFERING_INFO_BASE['image_base64'], offering['image']['data'])
        self.assertEquals([], offering['related_images'])
        self.assertEquals([{'provider': user_nickname, 'name': OFFERING_INFO_BASE['name'], 'version': OFFERING_INFO_BASE['version']}], offering['resources'])
        self.assertEquals([], offering['applications'])
        self.assertEquals(OFFERING_INFO_BASE['description'], offering['offering_info']['description'])
        self.assertEquals(OFFERING_INFO_BASE['license_title'], offering['offering_info']['legal']['title'])
        self.assertEquals(OFFERING_INFO_BASE['license_description'], offering['offering_info']['legal']['text'])
        self.assertEquals(controller.config['ckan.storepublisher.repository'], offering['repository'])
        self.assertEquals(OFFERING_INFO_BASE['is_open'], offering['open'])

        # Check price
        if price == 0:
            self.assertEquals('free', offering['offering_info']['pricing']['price_model'])
        else:
            self.assertEquals('single_payment', offering['offering_info']['pricing']['price_model'])
            self.assertEquals(price, offering['offering_info']['pricing']['price'])

    def test_get_tags(self):
        expected_tags = list(OFFERING_INFO_BASE['tags'])
        expected_tags.append('dataset')
        returned_tags = self.instanceController._get_tags(OFFERING_INFO_BASE)['tags']
        self.assertEquals(expected_tags, returned_tags)

    @parameterized.expand([
        ('get',    {},                    None,        200),
        ('post',   {},                    None,        200),
        ('put',    {},                    None,        200),
        ('delete', {},                    None,        200),
        ('get',    {},                    None,        400),
        ('post',   {},                    None,        402),
        ('put',    {},                    None,        457),
        ('delete', {},                    None,        499),
        ('get',    {},                    None,        500),
        ('post',   {},                    None,        502),
        ('put',    {},                    None,        557),
        ('delete', {},                    None,        599),
        ('get',    {'Content-Type': 'a'}, 'TEST DATA', 200),
        ('post',   {'Content-Type': 'b'}, 'TEST DATA', 200),
        ('put',    {'Content-Type': 'c'}, 'TEST DATA', 200),
        ('delete', {'Content-Type': 'd'}, 'TEST DATA', 200),
        ('get',    {},                    None,        401),
        ('post',   {},                    None,        401),
        ('put',    {},                    None,        401),
        ('delete', {},                    None,        401),
        ('get',    {'Content-Type': 'a'}, 'TEST DATA', 401),
        ('post',   {'Content-Type': 'b'}, 'TEST DATA', 401),
        ('put',    {'Content-Type': 'c'}, 'TEST DATA', 401),
        ('delete', {'Content-Type': 'd'}, 'TEST DATA', 401)
    ])
    def test_make_request(self, method, headers, data, response_status):
        url = 'http://example.com'
        ERROR_MSG = 'This is an example error!'

        # Set the environ
        usertoken = controller.plugins.toolkit.c.usertoken = {
            'token_type': 'bearer',
            'access_token': 'access_token',
            'refresh_token': 'refresh_token'
        }

        newtoken = {
            'token_type': 'bearer',
            'access_token': 'new_access_token',
            'refresh_token': 'new_refresh_token'
        }

        # Mock refresh_function
        def refresh_function_side_effect():
            controller.plugins.toolkit.c.usertoken = newtoken
        controller.plugins.toolkit.c.usertoken_refresh = MagicMock(side_effect=refresh_function_side_effect)

        expected_headers = headers.copy()
        expected_headers['Authorization'] = '%s %s' % (usertoken['token_type'], usertoken['access_token'])

        # Set the response status
        first_response = MagicMock()
        first_response.status_code = response_status
        first_response.text = '<error>%s</error>' % ERROR_MSG
        second_response = MagicMock()
        second_response.status_code = 201

        def req_method_side_effect(url, headers, data):
            if newtoken['access_token'] in headers['Authorization']:
                return second_response
            else:
                return first_response

        req_method = MagicMock(side_effect=req_method_side_effect)
        setattr(controller.requests, method, req_method)

        # Call the function
        if response_status > 399 and response_status < 600 and response_status != 401:
            with self.assertRaises(Exception) as e:
                self.instanceController._make_request(method, url, headers, data)
                self.assertEquals(ERROR_MSG, e.message)
        else:
            result = self.instanceController._make_request(method, url, headers, data)

            # If the first request returns a 401, the request is retried with a new access_token...
            if response_status != 401:
                self.assertEquals(first_response, result)
                req_method.assert_called_once_with(url, headers=expected_headers, data=data)
            else:
                # Check that the token has been refreshed
                controller.plugins.toolkit.c.usertoken_refresh.assert_called_once_with()

                # Check URL
                self.assertEquals(url, req_method.call_args_list[0][0][0])
                self.assertEquals(url, req_method.call_args_list[1][0][0])

                # Check headers
                expected_initial_headers = headers.copy()
                expected_initial_headers['Authorization'] = '%s %s' % (usertoken['token_type'], usertoken['access_token'])
                self.assertEquals(expected_initial_headers, req_method.call_args_list[0][1]['headers'])
                expected_final_headers = headers.copy()
                expected_final_headers['Authorization'] = '%s %s' % (newtoken['token_type'], newtoken['access_token'])
                self.assertEquals(expected_final_headers, req_method.call_args_list[1][1]['headers'])

                # Check Data
                self.assertEquals(data, req_method.call_args_list[0][1]['data'])
                self.assertEquals(data, req_method.call_args_list[1][1]['data'])

                # Check response
                self.assertEquals(second_response, result)

    def test_make_request_exception(self):
        # Set the environ
        usertoken = controller.plugins.toolkit.c.usertoken = {
            'token_type': 'bearer',
            'access_token': 'access_token',
            'refresh_token': 'refresh_token'
        }

        method = 'get'
        url = 'http://example.com'
        headers = {
            'Content-Type': 'application/json'
        }
        data = 'This is an example test...?'

        expected_headers = headers.copy()
        expected_headers['Authorization'] = '%s %s' % (usertoken['token_type'], usertoken['access_token'])

        req_method = MagicMock(side_effect=ConnectionError)
        setattr(controller.requests, method, req_method)

        # Call the function
        with self.assertRaises(ConnectionError):
            self.instanceController._make_request(method, url, headers, data)

    @parameterized.expand([
        (True,  True),
        (True,  False),
        (False, True),
        (False, False)
    ])
    def test_rollback(self, resource_created, offering_created):

        expected_number_calls = 0
        user_nickname = controller.plugins.toolkit.c.user = 'smg'
        # Configure mocks
        self.instanceController._make_request = MagicMock()
        # Call the function
        self.instanceController._rollback(resource_created, offering_created, OFFERING_INFO_BASE)

        if resource_created:
            self.instanceController._make_request.assert_any_call('delete', '%s/api/offering/resources/%s/%s/%s' % (BASE_STORE_URL,
                                                                  user_nickname, OFFERING_INFO_BASE['name'], OFFERING_INFO_BASE['version']))
            expected_number_calls += 1

        if offering_created:
            self.instanceController._make_request.assert_any_call('delete', '%s/api/offering/offerings/%s/%s/%s' % (BASE_STORE_URL,
                                                                  user_nickname, OFFERING_INFO_BASE['name'], OFFERING_INFO_BASE['version']))
            expected_number_calls += 1

        # Check that _make_request has been called the appropriate number of times
        self.assertEquals(expected_number_calls, self.instanceController._make_request.call_count)

    @parameterized.expand([
        (None,),
        ([Exception(EXCEPTION_MSG)],                         EXCEPTION_MSG),
        ([ConnectionError(EXCEPTION_MSG)],                   CONNECTION_ERROR_MSG),
        ([None, Exception(EXCEPTION_MSG)],                   EXCEPTION_MSG,        True, False),
        ([None, ConnectionError(EXCEPTION_MSG)],             CONNECTION_ERROR_MSG, True, False),
        ([None, None, Exception(EXCEPTION_MSG)],             EXCEPTION_MSG,        True, True),
        ([None, None, ConnectionError(EXCEPTION_MSG)],       CONNECTION_ERROR_MSG, True, True),
        ([None, None, None, Exception(EXCEPTION_MSG)],       EXCEPTION_MSG,        True, True),
        ([None, None, None, ConnectionError(EXCEPTION_MSG)], CONNECTION_ERROR_MSG, True, True)
    ])
    def test_create_offering(self, make_req_side_effect, expected_result=True, resource_created=False, offering_created=False):

        # Mock the plugin functions
        offering = {'offering': 1}
        resource = {'resource': 2}
        tags = {'tags': ['dataset']}
        self.instanceController._get_resource = MagicMock(return_value=resource)
        self.instanceController._get_offering = MagicMock(return_value=offering)
        self.instanceController._get_tags = MagicMock(return_value=tags)
        self.instanceController._rollback = MagicMock()
        self.instanceController._make_request = MagicMock(side_effect=make_req_side_effect)
        user_nickname = controller.plugins.toolkit.c.user = 'smg'

        # Call the function
        result = self.instanceController.create_offering(OFFERING_INFO_BASE)
        self.assertEquals(expected_result, result)

        # result == True if the offering was created properly
        if expected_result is True:

            self.instanceController._get_resource.assert_called_once_with(OFFERING_INFO_BASE)
            self.instanceController._get_offering.assert_called_once_with(OFFERING_INFO_BASE)
            self.instanceController._get_tags.assert_called_once_with(OFFERING_INFO_BASE)

            def check_make_request_calls(call, method, url, headers, data):
                self.assertEquals(method, call[0][0])
                self.assertEquals(url, call[0][1])
                self.assertEquals(headers, call[0][2])
                self.assertEquals(data, call[0][3])

            call_list = self.instanceController._make_request.call_args_list
            base_url = '%s/api/offering' % BASE_STORE_URL
            headers = {'Content-Type': 'application/json'}
            pkg_name = OFFERING_INFO_BASE['name']
            version = OFFERING_INFO_BASE['version']
            check_make_request_calls(call_list[0], 'post', '%s/resources' % base_url, headers, json.dumps(resource))
            check_make_request_calls(call_list[1], 'post', '%s/offerings' % base_url, headers, json.dumps(offering))
            check_make_request_calls(call_list[2], 'put', '%s/offerings/%s/%s/%s/tag' % (base_url, user_nickname, pkg_name, version), headers, json.dumps(tags))
            check_make_request_calls(call_list[3], 'post', '%s/offerings/%s/%s/%s/publish' % (base_url, user_nickname, pkg_name, version), headers, json.dumps({'marketplaces': []}))
        else:
            self.instanceController._rollback.assert_called_once_with(resource_created, offering_created, OFFERING_INFO_BASE)

    @parameterized.expand([
        (False, False, {},),
        # Test missing fields
        (True,  False, {'name': 'a', 'version': '1.0', 'pkg_id': 'package_id'},),
        (True,  False, {'version': '1.0', 'pkg_id': 'package_id'}),
        (True,  False, {'name': 'a', 'pkg_id': 'package_id'}),
        (True,  False, {'pkg_id': 'package_id'}),
        (True,  False, {'name': 'a', 'version': '1.0'}),
        # Test invalid prices
        (True,  False, {'name': 'a', 'version': '1.0', 'pkg_id': 'package_id', 'price': 'a'},),
        (True,  False, {'name': 'a', 'version': '1.0', 'pkg_id': 'package_id', 'price': '5.a'},),
        # Test open offerings (open offerings must not contain private datasets)
        (True,  False, {'name': 'a', 'version': '1.0', 'pkg_id': 'package_id', 'open': ''},),
        (True,  True,  {'name': 'a', 'version': '1.0', 'pkg_id': 'package_id', 'open': ''},),
        # Public datastets cannot be offering in paid offerings
        (True,  False, {'name': 'a', 'version': '1.0', 'pkg_id': 'package_id', 'price': '1.0'},),
        (True,  True,  {'name': 'a', 'version': '1.0', 'pkg_id': 'package_id', 'price': '1.0'},),
        # 'image_upload' == '' happens when the user has not selected a file, so the default one must be used
        (True,  False, {'name': 'a', 'version': '1.0', 'pkg_id': 'package_id', 'image_upload': ''},),
        (True,  False, {'name': 'a', 'version': '1.0', 'pkg_id': 'package_id', 'image_upload': MagicMock()},),
        # If 'update_acquire_url' is in the request content, the acquire_url should be updated
        # only when the offering has been published correctly
        (True,  False, {'name': 'a', 'version': '1.0', 'pkg_id': 'package_id', 'update_acquire_url': ''},),
        (True,  False, {'name': 'a', 'version': '1.0', 'pkg_id': 'package_id'},                               'Impossible to connect with the Store'),
        (True,  False, {'name': 'a', 'version': '1.0', 'pkg_id': 'package_id', 'update_acquire_url': ''},     'Impossible to connect with the Store'),
        # Requests with the fields not tested above
        # Test with and without tags
        (True,  False, {'name': 'a', 'version': '1.0', 'pkg_id': 'package_id', 'description': 'Example Description',
                        'license_title': 'cc', 'license_description': 'Desc', 'tag_string': 'tag1,tag2,tag3'}),
        (True,  False, {'name': 'a', 'version': '1.0', 'pkg_id': 'package_id', 'description': 'Example Description',
                        'license_title': 'cc', 'license_description': 'Desc', 'tag_string': ''}),
        # Request will all the fields
        (True,  False, {'name': 'A B C D', 'version': '1.0', 'pkg_id': 'package_id', 'description': 'Example Description',
                        'license_title': 'cc', 'license_description': 'Desc', 'tag_string': 'tag1,tag2,tag3',
                         'price': '1.1', 'image_upload': MagicMock(), 'update_acquire_url': ''}),
    ])
    def test_publish(self, allowed, private, post_content={}, create_offering_res=True):

        errors = {}
        current_package = {'tags': [{'name': 'tag1'}, {'name': 'tag2'}], 'private': private, 'acquire_url': 'http://example.com'}
        package_show = MagicMock(return_value=current_package)
        package_update = MagicMock()

        def _get_action_side_effect(action):
            if action == 'package_show':
                return package_show
            else:
                return package_update

        controller.plugins.toolkit.get_action = MagicMock(side_effect=_get_action_side_effect)
        controller.plugins.toolkit.check_access = MagicMock(side_effect=self._toolkit.NotAuthorized if allowed is False else None)
        controller.plugins.toolkit._ = self._toolkit._
        controller.request.POST = post_content
        self.instanceController.create_offering = MagicMock(return_value=create_offering_res)
        user = controller.plugins.toolkit.c.user
        pkg_id = 'dhjus2-fdsjwdf-fq-dsjager'

        expected_context = {'model': controller.model, 'session': controller.model.Session,
                            'user': controller.plugins.toolkit.c.user, 'auth_user_obj': controller.plugins.toolkit.c.userobj,
                            }

        # Call the function
        self.instanceController.publish(pkg_id)

        # Check that the check_access function has been called
        controller.plugins.toolkit.check_access.assert_called_once_with('package_update', expected_context, {'id': pkg_id})

        # Check that the abort function is called properly
        if not allowed:
            controller.plugins.toolkit.abort.assert_called_once_with(401, 'User %s not authorized to publish %s' % (user, pkg_id))
        else:

            # Get the list of tags
            tag_string = post_content.get('tag_string', '')
            tags = [] if tag_string == '' else tag_string.split(',')

            # Calculate errors
            if 'name' not in post_content:
                errors['Name'] = [MISSING_ERROR]
            
            if 'version' not in post_content:
                errors['Version'] = [MISSING_ERROR]

            if 'pkg_id' not in post_content:
                errors['Pkg_id'] = [MISSING_ERROR]

            price = post_content.get('price', '')
            if price != '':
                try:
                    real_price = float(post_content['price'])
                    if real_price > 0 and not private:
                        errors['Price'] = ['You cannot set a price to a dataset that is public since everyone can access it']
                except Exception:
                    errors['Price'] = ['"%s" is not a valid number' % price]
            else:
                real_price = 0.0

            if 'open' in post_content and private:
                errors['Open'] = ['Private Datasets cannot be offered as Open Offerings']

            if errors:
                # If the parameters are invalid, the function create_offering must not be called
                self.assertEquals(0, self.instanceController.create_offering.call_count)
            else:

                # Default image should be used if the users has not uploaded a image
                image_field = post_content.get('image_upload', '')
                if image_field != '':
                    controller.base64.b64encode.assert_called_once_with(image_field.file.read.return_value)
                    expected_image = controller.base64.b64encode.return_value
                else:
                    self.assertEquals(0, controller.base64.b64encode.call_count)
                    expected_image = LOGO_CKAN_B64

                expected_data = {
                    'name': post_content['name'],
                    'pkg_id': post_content['pkg_id'],
                    'version': post_content['version'],
                    'description': post_content.get('description', ''),
                    'license_title': post_content.get('license_title', ''),
                    'license_description': post_content.get('license_description', ''),
                    'is_open': 'open' in post_content,
                    'tags': tags,
                    'price': real_price,
                    'image_base64': expected_image,
                    'update_acquire_url': 'update_acquire_url' in post_content
                }

                self.instanceController.create_offering.assert_called_once_with(expected_data)

                if create_offering_res is True:

                    offering_name = post_content['name'].replace(' ', '%20')
                    offering_url = '%s/offering/%s/%s/%s' % (BASE_STORE_URL, user, offering_name, post_content['version'])

                    controller.helpers.flash_success.assert_called_once_with('Offering <a href="%s" target="_blank">' % offering_url +
                                                                             '%s</a> published correctly.' % post_content['name'],
                                                                             allow_html=True)
                    # If 'update_acquire_url' is in the request content and 'create_offering' does not fail,
                    # the package_update function should be called.
                    if 'update_acquire_url' in post_content:
                        expected_ds = current_package.copy()
                        expected_ds['acquire_url'] = offering_url
                        package_update.assert_called_once_with(expected_context, expected_ds)
                else:
                    errors['Store'] = [create_offering_res]
                    # The package should not be updated if the create_offering returns an error
                    # even if 'update_acquire_url' is present in the request content.
                    self.assertEquals(0, package_update.call_count)

        expected_pkg = current_package.copy()
        expected_pkg['tag_string'] = ','.join([tag['name'] for tag in current_package['tags']])
        self.assertEquals(expected_pkg, controller.plugins.toolkit.c.pkg_dict)
        self.assertEquals(errors, controller.plugins.toolkit.c.errors)

        controller.plugins.toolkit.render('package/publish.html')
