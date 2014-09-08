# -*- coding: utf-8 -*-

# Copyright (c) 2014 CoNWeT Lab., Universidad Politécnica de Madrid

# This file is part of CKAN Store Updater Extension.

# CKAN Store Updater Extension is free software: you can redistribute it and/or
# modify it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# CKAN Store Updater Extension is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.

# You should have received a copy of the GNU Affero General Public License
# along with CKAN Store Updater Extension.  If not, see <http://www.gnu.org/licenses/>.

import ckanext.storeupdater.controllers.ui_controller as controller
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
ConnectionError = controller.requests.ConnectionError   # Needed since it will be risen
CONNECTION_ERROR_MSG = 'It was impossible to connect with the Store'


class UIControllerTest(unittest.TestCase):

    def setUp(self):

        # Mocks
        self._toolkit = controller.plugins.toolkit
        controller.plugins.toolkit = MagicMock()

        self._requests = controller.requests
        controller.requests = MagicMock()
        controller.requests.ConnectionError = ConnectionError    # Recover Exception

        self._config = controller.config
        controller.config = {
            'ckan.site_url': 'https://localhost:8474',
            'ckan.storeupdater.store_url': 'https://store.example.com:7458'
        }

        # Create the plugin
        self.instanceController = controller.PublishControllerUI()
        # Save the functions and restore them later since it will be mocked in some tests
        self._make_request = self.instanceController._make_request
        self._rollback = self.instanceController._rollback
        self._get_resource = self.instanceController._get_resource
        self._get_offering = self.instanceController._get_offering
        self._get_tags = self.instanceController._get_tags
        self._create_offering = self.instanceController.create_offering

    def tearDown(self):
        controller.plugins.toolkit = self._toolkit
        controller.plugins.requests = self._requests
        controller.config = self._config

        self.instanceController._make_request = self._make_request
        self.instanceController._rollback = self._rollback
        self.instanceController.create_offering = self._create_offering
        self.instanceController._get_resource = self._get_resource
        self.instanceController._get_offering = self._get_offering
        self.instanceController._get_tags = self._get_tags

    def read_ckan_logo_b64(self):
        __dir__ = os.path.dirname(os.path.abspath(__file__))
        filepath = os.path.join(__dir__, '../assets/logo-ckan.png')

        with open(filepath, 'rb') as f:
            b64image = base64.b64encode(f.read())
        return b64image

    def test_get_resource(self):
        resource = self.instanceController._get_resource(OFFERING_INFO_BASE)

        # Check the values
        self.assertEquals(OFFERING_INFO_BASE['name'], resource['name'])
        self.assertEquals(OFFERING_INFO_BASE['description'], resource['description'])
        self.assertEquals(OFFERING_INFO_BASE['version'], resource['version'])
        self.assertEquals('dataset', resource['content_type'])
        self.assertEquals(OFFERING_INFO_BASE['is_open'], resource['open'])
        self.assertEquals('%s/dataset/%s' % (controller.config['ckan.site_url'], OFFERING_INFO_BASE['pkg_id']), resource['link'])

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
        self.assertEquals('Local', offering['repository'])
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

        def refresh_function_side_effect():
            controller.plugins.toolkit.c.usertoken = newtoken
        controller.plugins.toolkit.c.usertoken_refresh = MagicMock(side_effect=refresh_function_side_effect)

        expected_headers = headers.copy()
        expected_headers['Authorization'] = '%s %s' % (usertoken['token_type'], usertoken['access_token'])

        # Set the response status
        first_response = MagicMock()
        first_response.status_code = response_status
        first_response.text = '<error>This is an example error!</error>'
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
        if response_status > 399 and response_status != 401:
            self.assertRaises(Exception, self.instanceController._make_request, (method, url, headers, data))
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

        req_method = MagicMock(side_effect=Exception)
        setattr(controller.requests, method, req_method)

        # Call the function
        self.assertRaises(Exception, self.instanceController._make_request, (method, url, headers, data))

    @parameterized.expand([
        (True,  True),
        (True,  False),
        (False, True),
        (False, False)
    ])
    def test_rollback(self, resource_created, offering_created):

        user_nickname = controller.plugins.toolkit.c.user = 'smg'
        # Configure mocks
        self.instanceController._make_request = MagicMock()
        # Call the function
        self.instanceController._rollback(resource_created, offering_created, OFFERING_INFO_BASE)

        if resource_created:
            self.instanceController._make_request.assert_called_with('delete', '%s/api/offering/resources/%s/%s/%s' % (controller.config['ckan.storeupdater.store_url'],
                                                                     user_nickname, OFFERING_INFO_BASE['name'], OFFERING_INFO_BASE['version']))
        if offering_created:
            self.instanceController._make_request.assert_any_call('delete', '%s/api/offering/offerings/%s/%s/%s' % (controller.config['ckan.storeupdater.store_url'],
                                                                  user_nickname, OFFERING_INFO_BASE['name'], OFFERING_INFO_BASE['version']))

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

        # result == True if the offering was created properly
        if expected_result is True:

            self.assertEquals(expected_result, result)

            self.instanceController._get_resource.assert_called_once_with(OFFERING_INFO_BASE)
            self.instanceController._get_offering.assert_called_once_with(OFFERING_INFO_BASE)
            self.instanceController._get_tags.assert_called_once_with(OFFERING_INFO_BASE)

            def check_make_request_calls(call, method, url, headers, data):
                self.assertEquals(method, call[0][0])
                self.assertEquals(url, call[0][1])
                self.assertEquals(headers, call[0][2])
                self.assertEquals(data, call[0][3])

            call_list = self.instanceController._make_request.call_args_list
            store_url = controller.config['ckan.storeupdater.store_url']
            base_url = '%s/api/offering' % store_url
            headers = {'Content-Type': 'application/json'}
            pkg_name = OFFERING_INFO_BASE['name']
            version = OFFERING_INFO_BASE['version']
            check_make_request_calls(call_list[0], 'post', '%s/resources' % base_url, headers, json.dumps(resource))
            check_make_request_calls(call_list[1], 'post', '%s/offerings' % base_url, headers, json.dumps(offering))
            check_make_request_calls(call_list[2], 'put', '%s/offerings/%s/%s/%s/tag' % (base_url, user_nickname, pkg_name, version), headers, json.dumps(tags))
            check_make_request_calls(call_list[3], 'post', '%s/offerings/%s/%s/%s/publish' % (base_url, user_nickname, pkg_name, version), headers, json.dumps({'marketplaces': []}))
        else:
            self.assertEquals(expected_result, result)
            self.instanceController._rollback.assert_called_once_with(resource_created, offering_created, OFFERING_INFO_BASE)

