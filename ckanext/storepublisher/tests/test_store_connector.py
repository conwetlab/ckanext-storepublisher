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

import ckanext.storepublisher.store_connector as store_connector

import json
import unittest

from mock import MagicMock
from nose_parameterized import parameterized

# Need to be defined here, since it will be used as tests parameter
ConnectionError = store_connector.requests.ConnectionError

DATASET = {
    'id': 'example_id',
    'title': u'Dataset A',
    'notes': 'Dataset description. This can be a very long field and can include markdown syntax'
}


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
BASE_SITE_URL = 'https://localhost:8474'
BASE_STORE_URL = 'https://store.example.com:7458'
CONNECTION_ERROR_MSG = 'It was impossible to connect with the Store'


class StoreConnectorTest(unittest.TestCase):

    def setUp(self):

        # Mocks
        self._toolkit = store_connector.plugins.toolkit
        store_connector.plugins.toolkit = MagicMock()
        store_connector.plugins.toolkit.NotAuthorized = self._toolkit.NotAuthorized

        self._model = store_connector.model
        store_connector.model = MagicMock()

        self._requests = store_connector.requests
        store_connector.requests = MagicMock()
        store_connector.requests.ConnectionError = ConnectionError    # Recover Exception

        self._OAuth2Session = store_connector.OAuth2Session

        self.config = {
            'ckan.site_url': BASE_SITE_URL,
            'ckan.storepublisher.store_url': BASE_STORE_URL,
            'ckan.storepublisher.repository': 'Example Repo'
        }

        self.instance = store_connector.StoreConnector(self.config)

        # Save controller functions since it will be mocked in some tests
        self._make_request = self.instance._make_request
        self._rollback = self.instance._rollback
        self._get_resource = self.instance._get_resource
        self._get_offering = self.instance._get_offering
        self._get_tags = self.instance._get_tags
        self._create_offering = self.instance.create_offering

    def tearDown(self):
        store_connector.plugins.toolkit = self._toolkit
        store_connector.requests = self._requests
        store_connector.OAuth2Session = self._OAuth2Session
        store_connector.model = self._model

        # Restore controller functions
        self.instance._make_request = self._make_request
        self.instance._rollback = self._rollback
        self.instance.create_offering = self._create_offering
        self.instance._get_resource = self._get_resource
        self.instance._get_offering = self._get_offering
        self.instance._get_tags = self._get_tags

    @parameterized.expand([
        ('%s' % BASE_SITE_URL,  '%s' % BASE_STORE_URL),
        ('%s/' % BASE_SITE_URL, '%s' % BASE_STORE_URL),
        ('%s' % BASE_SITE_URL,  '%s/' % BASE_STORE_URL),
        ('%s/' % BASE_SITE_URL, '%s/' % BASE_STORE_URL)
    ])
    def test_init(self, site_url, store_url):

        config = {
            'ckan.site_url': site_url,
            'ckan.storepublisher.store_url': store_url,
            'ckan.storepublisher.repository': 'Example Repo'
        }

        instance = store_connector.StoreConnector(config)
        self.assertEquals(BASE_SITE_URL, instance.site_url)
        self.assertEquals(BASE_STORE_URL, instance.store_url)

    @parameterized.expand([
        (DATASET['title'], DATASET['title']),
        (u'ábcdé! fgh?=monitor', 'abcde fgh monitor')
    ])
    def test_get_resource(self, initial_name, expected_name):
        dataset = DATASET.copy()
        dataset['title'] = initial_name
        resource = self.instance._get_resource(dataset)

        # Check the values
        self.assertEquals('Dataset %s - ID %s' % (expected_name, DATASET['id']), resource['name'])
        self.assertEquals(DATASET['notes'], resource['description'])
        self.assertEquals('1.0', resource['version'])
        self.assertEquals('dataset', resource['content_type'])
        self.assertEquals(True, resource['open'])
        self.assertEquals('%s/dataset/%s' % (BASE_SITE_URL, DATASET['id']), resource['link'])

    @parameterized.expand([
        (0,),
        (1,)
    ])
    def test_get_offering(self, price):
        user_nickname = 'smg'
        store_connector.plugins.toolkit.c.user = user_nickname
        offering_info = OFFERING_INFO_BASE.copy()
        offering_info['price'] = price
        resource = {'provider': 'test', 'name': 'resource_name', 'version': '1.0'}
        offering = self.instance._get_offering(offering_info, resource)

        # Check the values
        self.assertEquals(OFFERING_INFO_BASE['name'], offering['name'])
        self.assertEquals(OFFERING_INFO_BASE['version'], offering['version'])
        self.assertEquals('ckan.png', offering['image']['name'])
        self.assertEquals(OFFERING_INFO_BASE['image_base64'], offering['image']['data'])
        self.assertEquals([], offering['related_images'])
        self.assertEquals([resource], offering['resources'])
        self.assertEquals([], offering['applications'])
        self.assertEquals(OFFERING_INFO_BASE['description'], offering['offering_info']['description'])
        self.assertEquals(OFFERING_INFO_BASE['license_title'], offering['offering_info']['legal']['title'])
        self.assertEquals(OFFERING_INFO_BASE['license_description'], offering['offering_info']['legal']['text'])
        self.assertEquals(self.config['ckan.storepublisher.repository'], offering['repository'])
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
        returned_tags = self.instance._get_tags(OFFERING_INFO_BASE)['tags']
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
        usertoken = store_connector.plugins.toolkit.c.usertoken = {
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
            store_connector.plugins.toolkit.c.usertoken = newtoken
        store_connector.plugins.toolkit.c.usertoken_refresh = MagicMock(side_effect=refresh_function_side_effect)

        expected_headers = headers.copy()
        expected_headers['Accept'] = 'application/json'

        # Set the response status
        first_response = MagicMock()
        first_response.status_code = response_status
        first_response.text = '{"message": %s, "result": False}' % ERROR_MSG
        second_response = MagicMock()
        second_response.status_code = 201

        request = MagicMock()
        store_connector.OAuth2Session = MagicMock(return_value=request)
        req_method = MagicMock(side_effect=[first_response, second_response])
        setattr(request, method, req_method)

        # Call the function
        if response_status > 399 and response_status < 600 and response_status != 401:
            with self.assertRaises(Exception) as e:
                self.instance._make_request(method, url, headers, data)
                self.assertEquals(ERROR_MSG, e.message)
                store_connector.OAuth2Session.assert_called_once_with(token=usertoken)
                req_method.assert_called_once_with(url, headers=expected_headers, data=data)
        else:
            result = self.instance._make_request(method, url, headers, data)

            # If the first request returns a 401, the request is retried with a new access_token...
            if response_status != 401:
                self.assertEquals(first_response, result)
                req_method.assert_called_once_with(url, headers=expected_headers, data=data)
                store_connector.OAuth2Session.assert_called_once_with(token=usertoken)
                req_method.assert_called_once_with(url, headers=expected_headers, data=data)
            else:
                # Check that the token has been refreshed
                store_connector.plugins.toolkit.c.usertoken_refresh.assert_called_once_with()

                # Check that both tokens has been used
                self.assertEquals(usertoken, store_connector.OAuth2Session.call_args_list[0][1]['token'])
                self.assertEquals(newtoken, store_connector.OAuth2Session.call_args_list[1][1]['token'])

                # Check URL
                self.assertEquals(url, req_method.call_args_list[0][0][0])
                self.assertEquals(url, req_method.call_args_list[1][0][0])

                # Check headers
                self.assertEquals(expected_headers, req_method.call_args_list[0][1]['headers'])
                self.assertEquals(expected_headers, req_method.call_args_list[1][1]['headers'])

                # Check Data
                self.assertEquals(data, req_method.call_args_list[0][1]['data'])
                self.assertEquals(data, req_method.call_args_list[1][1]['data'])

                # Check response
                self.assertEquals(second_response, result)

    def test_make_request_exception(self):
        method = 'get'
        url = 'http://example.com'
        headers = {
            'Content-Type': 'application/json'
        }
        data = 'This is an example test...?'

        request = MagicMock()
        store_connector.OAuth2Session = MagicMock(return_value=request)
        req_method = MagicMock(side_effect=ConnectionError)
        setattr(request, method, req_method)

        # Call the function
        with self.assertRaises(ConnectionError):
            self.instance._make_request(method, url, headers, data)

    @parameterized.expand([
        (True, '',                                                                                        'provider_name', 'testResource', '1.0', True),
        (True,  '%s/search/resource/%s/%s/%s' % (BASE_STORE_URL, 'provider name', 'testResource', '1.0'), 'provider name', 'testResource', '1.0', False),
        (False, '',                                                                                       'provider_name', 'testResource', '1.0', False),
        (False, '%s/search/resource/%s/%s/%s' % (BASE_STORE_URL, 'provider name', 'testResource', '1.0'), 'provider name', 'testResource', '1.0', False),
    ])
    def test_update_acquire_url(self, private, acquire_url, resource_provider, resource_name, resource_version, should_update):
        c = store_connector.plugins.toolkit.c
        c.user = resource_provider
        package_update = MagicMock()
        store_connector.plugins.toolkit.get_action = MagicMock(return_value=package_update)

        # Call the method
        dataset = {
            'private': private,
            'acquire_url': acquire_url
        }
        resource = {
            'name': resource_name,
            'version': resource_version,
            'provider': resource_provider
        }
        expected_dataset = dataset.copy()
        new_name = resource['name'].replace(' ', '%20')
        expected_dataset['acquire_url'] = '%s/search/resource/%s/%s/%s' % (BASE_STORE_URL, resource['provider'], new_name, resource['version'])

        # Update Acquire URL
        self.instance._update_acquire_url(dataset, resource)

        # Check that the acquire URL has been updated
        if should_update:
            context = {'model': store_connector.model, 'session': store_connector.model.Session,
                       'user': c.user or c.author, 'auth_user_obj': c.userobj,
                       }
            package_update.assert_called_once_with(context, expected_dataset)
        else:
            self.assertEquals(0, package_update.call_count)

    @parameterized.expand([
        ([], None),
        ([{'link': '%s/dataset/%s' % (BASE_SITE_URL, DATASET['id']), 'state': 'active', 'name': 'a', 'version': '1.0'}], 0),
        ([{'link': '%s/dataset/%s' % (BASE_STORE_URL, DATASET['id']), 'state': 'active', 'name': 'a', 'version': '1.0'}], None),
        ([{'link': '%s/dataset/%s' % (BASE_SITE_URL, DATASET['id'] + 'a'), 'state': 'active', 'name': 'a', 'version': '1.0'}], None),
        ([{'link': '%s/dataset/%s' % (BASE_SITE_URL, DATASET['id']), 'state': 'deleted', 'name': 'a', 'version': '1.0'}], None),
        ([{'link': 'google.es', 'state': 'active'},
          {'link': 'apple.es', 'state': 'active'},
          {'link': '%s/dataset/%s' % (BASE_SITE_URL, DATASET['id']), 'state': 'deleted'}], None),
        ([{'link': 'google.es', 'state': 'active'},
          {'link': 'apple.es', 'state': 'active'},
          {'link': '%s/dataset/%s' % (BASE_STORE_URL, DATASET['id']), 'state': 'active'}], None),
        ([{'link': 'google.es', 'state': 'active'},
          {'link': 'apple.es', 'state': 'active'},
          {'link': '%s/dataset/%s' % (BASE_SITE_URL, DATASET['id']), 'state': 'active', 'name': 'a', 'version': '1.0'}], 2)

    ])
    def test_get_existing_resource(self, current_user_resources, id_correct_resource):
        # Set up the test and its dependencies
        req = MagicMock()
        req.json = MagicMock(return_value=current_user_resources)
        self.instance._make_request = MagicMock(return_value=req)
        self.instance._update_acquire_url = MagicMock()

        # Get the expected result
        if id_correct_resource is not None:
            expected_resource = {
                'provider': store_connector.plugins.toolkit.c.user,
                'name': current_user_resources[id_correct_resource]['name'],
                'version': current_user_resources[id_correct_resource]['version']
            }
        else:
            expected_resource = None

        # Call the function and check the result
        dataset = DATASET.copy()
        dataset['private'] = True
        self.assertEquals(expected_resource, self.instance._get_existing_resource(dataset))

        # Update Acquire URL method is called (when the dataset is registered as resource in the Store)
        if expected_resource is not None:
            self.instance._update_acquire_url.assert_called_once_with(dataset, current_user_resources[id_correct_resource])

    @parameterized.expand([
        (True,),
        (False,)
    ])
    def test_create_resource(self, private):
        c = store_connector.plugins.toolkit.c
        c.user = 'provider name'
        resource = {
            'provider': store_connector.plugins.toolkit.c.user,
            'name': 'resource name',
            'version': 'resource version',
            'link': 'example link'
        }

        expected_resource = {
            'provider': store_connector.plugins.toolkit.c.user,
            'name': resource['name'],
            'version': resource['version']
        }

        self.instance._get_resource = MagicMock(return_value=resource)
        self.instance._make_request = MagicMock()
        self.instance._update_acquire_url = MagicMock()

        # Call the function and check that we recieve the correct result
        dataset = DATASET.copy()
        dataset['private'] = private
        self.assertEquals(expected_resource, self.instance._create_resource(dataset))

        # Assert that the methods has been called
        self.instance._get_resource.assert_called_once_with(dataset)
        headers = {'Content-Type': 'application/json'}
        self.instance._make_request.assert_called_once_with('post', '%s/api/offering/resources' % BASE_STORE_URL, headers, json.dumps(resource))

        # Check that the acquire URL has been updated
        self.instance._update_acquire_url.assert_called_once_with(dataset, resource)

    @parameterized.expand([
        (True,),
        (False,)
    ])
    def test_rollback(self, offering_created):
        user_nickname = store_connector.plugins.toolkit.c.user = 'smg'
        # Configure mocks
        self.instance._make_request = MagicMock()
        # Call the function
        self.instance._rollback(OFFERING_INFO_BASE, offering_created)

        if offering_created:
            self.instance._make_request.assert_any_call('delete', '%s/api/offering/offerings/%s/%s/%s' % (BASE_STORE_URL,
                                                        user_nickname, OFFERING_INFO_BASE['name'], OFFERING_INFO_BASE['version']))

    @parameterized.expand([
        (True,  None),
        (False, None),
        (True,  [Exception(EXCEPTION_MSG)],                   EXCEPTION_MSG,        False),
        (False, [Exception(EXCEPTION_MSG)],                   EXCEPTION_MSG,        False),
        (True,  [ConnectionError(EXCEPTION_MSG)],             CONNECTION_ERROR_MSG, False),
        (False, [ConnectionError(EXCEPTION_MSG)],             CONNECTION_ERROR_MSG, False),
        (True,  [None, Exception(EXCEPTION_MSG)],             EXCEPTION_MSG,        True),
        (False, [None, Exception(EXCEPTION_MSG)],             EXCEPTION_MSG,        True),
        (True,  [None, ConnectionError(EXCEPTION_MSG)],       CONNECTION_ERROR_MSG, True),
        (False, [None, ConnectionError(EXCEPTION_MSG)],       CONNECTION_ERROR_MSG, True),
        (True,  [None, None, Exception(EXCEPTION_MSG)],       EXCEPTION_MSG,        True),
        (False, [None, None, Exception(EXCEPTION_MSG)],       EXCEPTION_MSG,        True),
        (True,  [None, None, ConnectionError(EXCEPTION_MSG)], CONNECTION_ERROR_MSG, True),
        (False, [None, None, ConnectionError(EXCEPTION_MSG)], CONNECTION_ERROR_MSG, True)
    ])
    def test_create_offering(self, resource_exists, make_req_side_effect, exception_text=None, offering_created=False):

        # Mock the plugin functions
        offering = {'offering': 1}
        resource = {'resource': 2}
        tags = {'tags': ['dataset']}
        resource = {
            'provider': 'provider name',
            'name': 'resource name',
            'version': 'resource version'
        }
        self.instance._get_resource = MagicMock(return_value=resource)
        self.instance._get_offering = MagicMock(return_value=offering)
        self.instance._get_tags = MagicMock(return_value=tags)
        self.instance._get_existing_resource = MagicMock(return_value=resource if resource_exists else None)
        self.instance._create_resource = MagicMock(return_value=resource)
        self.instance._rollback = MagicMock()
        self.instance._make_request = MagicMock(side_effect=make_req_side_effect)
        user_nickname = store_connector.plugins.toolkit.c.user = 'smg'

        # Call the function
        try:
            result = self.instance.create_offering(DATASET, OFFERING_INFO_BASE)

            # Verify that exceptions were not expected
            self.assertIsNone(exception_text)

            name = OFFERING_INFO_BASE['name'].replace(' ', '%20')
            expected_result = BASE_STORE_URL + '/offering/' + user_nickname + '/' + name + '/' + OFFERING_INFO_BASE['version']
            self.assertEquals(expected_result, result)

            self.instance._get_existing_resource.assert_called_once_with(DATASET)
            if not resource_exists:
                self.instance._create_resource.assert_called_once_with(DATASET)
            self.instance._get_offering.assert_called_once_with(OFFERING_INFO_BASE, resource)
            self.instance._get_tags.assert_called_once_with(OFFERING_INFO_BASE)

            def check_make_request_calls(call, method, url, headers, data):
                self.assertEquals(method, call[0][0])
                self.assertEquals(url, call[0][1])
                self.assertEquals(headers, call[0][2])
                self.assertEquals(data, call[0][3])

            call_list = self.instance._make_request.call_args_list
            base_url = '%s/api/offering' % BASE_STORE_URL
            headers = {'Content-Type': 'application/json'}
            pkg_name = OFFERING_INFO_BASE['name']
            version = OFFERING_INFO_BASE['version']
            check_make_request_calls(call_list[0], 'post', '%s/offerings' % base_url, headers, json.dumps(offering))
            check_make_request_calls(call_list[1], 'put', '%s/offerings/%s/%s/%s/tag' % (base_url, user_nickname, pkg_name, version), headers, json.dumps(tags))
            check_make_request_calls(call_list[2], 'post', '%s/offerings/%s/%s/%s/publish' % (base_url, user_nickname, pkg_name, version), headers, json.dumps({'marketplaces': []}))

        except store_connector.StoreException as e:
            self.instance._rollback.assert_called_once_with(OFFERING_INFO_BASE, offering_created)
            self.assertEquals(e.message, exception_text)
