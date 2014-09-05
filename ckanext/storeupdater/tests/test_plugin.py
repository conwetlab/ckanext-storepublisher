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

import ckanext.storeupdater.plugin as plugin
import base64
import json
import os
import unittest

from mock import MagicMock
from nose_parameterized import parameterized

PKG_DICT = {
    'name': 'example-dataset',
    'title': 'Example Dataset',
    'notes': 'Dataset description. This can be a very long field and can include markdown syntax',
    'license_id': 'cc'
}


class PluginTest(unittest.TestCase):

    def setUp(self):

        # Mocks
        self._toolkit = plugin.plugins.toolkit
        plugin.plugins.toolkit = MagicMock()

        self._requests = plugin.requests
        plugin.requests = MagicMock()

        self._config = plugin.config
        plugin.config = {
            'ckan.site_url': 'https://localhost:8474',
            'ckan.storeupdater.store_url': 'https://store.example.com:7458'
        }

        # Create the plugin
        self.storeUpdater = plugin.StoreUpdater()
        # Save the functions and restore them later since it will be mocked in some tests
        self._make_request = self.storeUpdater._make_request
        self._get_resource = self.storeUpdater._get_resource
        self._get_offering = self.storeUpdater._get_offering
        self._get_tags = self.storeUpdater._get_tags
        self._delete_offering = self.storeUpdater.delete_offering
        self._create_offering = self.storeUpdater.create_offering

    def tearDown(self):
        plugin.plugins.toolkit = self._toolkit
        plugin.plugins.requests = self._requests
        plugin.config = self._config

        self.storeUpdater._make_request = self._make_request
        self.storeUpdater.delete_offering = self._delete_offering
        self.storeUpdater.create_offering = self._create_offering
        self.storeUpdater._get_resource = self._get_resource
        self.storeUpdater._get_offering = self._get_offering
        self.storeUpdater._get_tags = self._get_tags

    def read_ckan_logo_b64(self):
        __dir__ = os.path.dirname(os.path.abspath(__file__))
        filepath = os.path.join(__dir__, '../assets/logo-ckan.png')

        with open(filepath, 'rb') as f:
            b64image = base64.b64encode(f.read())
        return b64image

    def test_get_resource(self):
        resource = self.storeUpdater._get_resource(PKG_DICT)

        # Check the values
        self.assertEquals(PKG_DICT['title'], resource['name'])
        self.assertEquals(PKG_DICT['notes'], resource['description'])
        self.assertEquals('1.0', resource['version'])
        self.assertEquals('dataset', resource['content_type'])
        self.assertEquals(True, resource['open'])
        self.assertEquals('%s/dataset/%s' % (plugin.config['ckan.site_url'], PKG_DICT['name']), resource['link'])

    def test_get_offering(self):
        user_nickname = 'smg'
        plugin.plugins.toolkit.c.user = user_nickname
        offering = self.storeUpdater._get_offering(PKG_DICT)

        # Check the values
        self.assertEquals(PKG_DICT['title'], offering['name'])
        self.assertEquals('1.0', offering['version'])
        self.assertEquals('ckan.png', offering['image']['name'])
        self.assertEquals(self.read_ckan_logo_b64(), offering['image']['data'])
        self.assertEquals([], offering['related_images'])
        self.assertEquals([{'provider': user_nickname, 'name': PKG_DICT['title'], 'version': '1.0'}], offering['resources'])
        self.assertEquals([], offering['applications'])
        self.assertEquals(PKG_DICT['notes'], offering['offering_info']['description'])
        self.assertEquals('free', offering['offering_info']['pricing']['price_model'])
        self.assertEquals(PKG_DICT['license_id'], offering['offering_info']['legal']['title'])
        self.assertEquals('License definitions and additional information can be found at opendefinition.org', offering['offering_info']['legal']['text'])
        self.assertEquals('Local', offering['repository'])
        self.assertEquals(True, offering['open'])

    @parameterized.expand([
        (None,),
        ([],),
        (['tag1'],),
        (['tag1', 'tag2', 'tag3'],)
    ])
    def test_get_tags(self, tags):
        # Simulate the way CKAN gives the list of tags and call the function
        pkg_dict = {'tags': []}
        if tags is not None:
            for tag in tags:
                pkg_dict['tags'].append({'name': tag})
        returned_tags = self.storeUpdater._get_tags(pkg_dict)['tags']

        # Check returned tags
        expected_tags = list(tags) if tags is not None else []
        expected_tags.append('dataset')
        self.assertEquals(len(expected_tags), len(returned_tags))
        for tag in expected_tags:
            self.assertIn(tag, returned_tags)

    @parameterized.expand([
        ('get',    {},                    None,        200),
        ('post',   {},                    None,        200),
        ('put',    {},                    None,        200),
        ('delete', {},                    None,        200),
        ('get',    {},                    None,        400),
        ('post',   {},                    None,        400),
        ('put',    {},                    None,        400),
        ('delete', {},                    None,        400),
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
        usertoken = plugin.plugins.toolkit.c.usertoken = {
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
            plugin.plugins.toolkit.c.usertoken = newtoken
        plugin.plugins.toolkit.c.usertoken_refresh = MagicMock(side_effect=refresh_function_side_effect)

        expected_headers = headers.copy()
        expected_headers['Authorization'] = '%s %s' % (usertoken['token_type'], usertoken['access_token'])

        # Set the response status
        first_response = MagicMock()
        first_response.status_code = response_status
        second_response = MagicMock()
        second_response.status_code = 201

        def req_method_side_effect(url, headers, data):
            if newtoken['access_token'] in headers['Authorization']:
                return second_response
            else:
                return first_response

        req_method = MagicMock(side_effect=req_method_side_effect)
        setattr(plugin.requests, method, req_method)

        # Call the function
        result = self.storeUpdater._make_request(method, url, headers, data)

        # If the first request returns a 401, the request is retried with a new access_token...
        if response_status != 401:
            self.assertEquals(first_response, result)
            req_method.assert_called_once_with(url, headers=expected_headers, data=data)
        else:
            # Check that the token has been refreshed
            plugin.plugins.toolkit.c.usertoken_refresh.assert_called_once_with()

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
        usertoken = plugin.plugins.toolkit.c.usertoken = {
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
        setattr(plugin.requests, method, req_method)

        # Call the function
        self.storeUpdater._make_request(method, url, headers, data)

        # Assert that the function has been called
        req_method.assert_called_once_with(url, headers=expected_headers, data=data)

    @parameterized.expand([
        (True,),
        (False,)
    ])
    def test_delete_offering(self, private):
        # Configure the mocks
        package = {'title': 'Example Dataset', 'private': private}
        package_show = MagicMock(return_value=package)
        plugin.plugins.toolkit.get_action = MagicMock(return_value=package_show)
        user_nickname = plugin.plugins.toolkit.c.user = 'smg'
        self.storeUpdater._make_request = MagicMock()

        # Call the function
        context = {'model': MagicMock(), 'session': MagicMock()}
        pkg_dict = {'id': 'dataset_identifier'}
        self.storeUpdater.delete_offering(context, pkg_dict)

        if private:
            self.assertEquals(0, self.storeUpdater._make_request.call_count)
        else:
            # Assert that the request has been performed
            # assert_called_with checks the last call. The last call should be the one made to remove the resource so:
            self.storeUpdater._make_request.assert_called_with('delete', '%s/api/offering/resources/%s/%s/1.0' %
                                                               (plugin.config['ckan.storeupdater.store_url'], user_nickname, package['title']))
            self.storeUpdater._make_request.assert_any_call('delete', '%s/api/offering/offerings/%s/%s/1.0'
                                                            % (plugin.config['ckan.storeupdater.store_url'], user_nickname, package['title']))

    @parameterized.expand([
        (True,),
        (False,)
    ])
    def test_create_offering(self, private):

        # Mock the plugin functions
        offering = {'offering': 1}
        resource = {'resource': 2}
        tags = {'tags': ['dataset']}
        self.storeUpdater._get_resource = MagicMock(return_value=resource)
        self.storeUpdater._get_offering = MagicMock(return_value=offering)
        self.storeUpdater._get_tags = MagicMock(return_value=tags)
        user_nickname = plugin.plugins.toolkit.c.user = 'smg'
        self.storeUpdater._make_request = MagicMock()

        # Call the function
        context = {'model': MagicMock(), 'session': MagicMock()}
        pkg_dict = {'private': private, 'title': 'Example Dataset'}
        self.storeUpdater.create_offering(context, pkg_dict)

        # When an offering is privated, it should not be created...
        if private:
            self.assertEquals(0, self.storeUpdater._get_resource.call_count)
            self.assertEquals(0, self.storeUpdater._get_offering.call_count)
            self.assertEquals(0, self.storeUpdater._get_tags.call_count)
            self.assertEquals(0, self.storeUpdater._make_request.call_count)
        else:
            self.storeUpdater._get_resource.assert_called_once_with(pkg_dict)
            self.storeUpdater._get_offering.assert_called_once_with(pkg_dict)
            self.storeUpdater._get_tags.assert_called_once_with(pkg_dict)

            def check_make_request_calls(call, method, url, headers, data):
                self.assertEquals(method, call[0][0])
                self.assertEquals(url, call[0][1])
                self.assertEquals(headers, call[0][2])
                self.assertEquals(data, call[0][3])

            call_list = self.storeUpdater._make_request.call_args_list
            store_url = plugin.config['ckan.storeupdater.store_url']
            base_url = '%s/api/offering' % store_url
            headers = {'Content-Type': 'application/json'}
            pkg_name = pkg_dict['title']
            check_make_request_calls(call_list[0], 'post', '%s/resources' % base_url, headers, json.dumps(resource))
            check_make_request_calls(call_list[1], 'post', '%s/offerings' % base_url, headers, json.dumps(offering))
            check_make_request_calls(call_list[2], 'put', '%s/offerings/%s/%s/1.0/tag' % (base_url, user_nickname, pkg_name), headers, json.dumps(tags))
            check_make_request_calls(call_list[3], 'post', '%s/offerings/%s/%s/1.0/publish' % (base_url, user_nickname, pkg_name), headers, json.dumps({'marketplaces': []}))

    @parameterized.expand([
        (None,),
        ('http://store.example.com',),
    ])
    def test_after_create(self, store_url):

        # Configure the plugin
        plugin.config = {}
        if store_url is not None:
            plugin.config['ckan.storeupdater.store_url'] = store_url

        self.storeUpdater = plugin.StoreUpdater()
        self.storeUpdater.create_offering = MagicMock()

        # Call the function
        context = {'model': MagicMock(), 'session': MagicMock()}
        pkg_dict = {'private': True, 'title': 'Example Dataset'}
        result = self.storeUpdater.after_create(context, pkg_dict)

        # Assert that the function has been called
        if store_url:
            self.storeUpdater.create_offering.assert_called_with(context, pkg_dict)
        else:
            self.assertEquals(0, self.storeUpdater.create_offering.call_count)

        # Assert that the package hasn't changed
        self.assertEquals(pkg_dict, result)

    @parameterized.expand([
        (None,),
        ('http://store.example.com',),
    ])
    def test_after_delete(self, store_url):

        # Configure the plugin
        plugin.config = {}
        if store_url is not None:
            plugin.config['ckan.storeupdater.store_url'] = store_url

        self.storeUpdater = plugin.StoreUpdater()
        self.storeUpdater.delete_offering = MagicMock()

        # Call the function
        context = {'model': MagicMock(), 'session': MagicMock()}
        pkg_dict = {'private': True, 'title': 'Example Dataset'}
        result = self.storeUpdater.after_delete(context, pkg_dict)

        # Assert that the function has been called
        if store_url:
            self.storeUpdater.delete_offering.assert_called_with(context, pkg_dict)
        else:
            self.assertEquals(0, self.storeUpdater.delete_offering.call_count)

        # Assert that the package hasn't changed
        self.assertEquals(pkg_dict, result)

    @parameterized.expand([
        (None,),
        ('http://store.example.com',),
    ])
    def test_after_update(self, store_url):

        # Configure the plugin
        plugin.config = {}
        if store_url is not None:
            plugin.config['ckan.storeupdater.store_url'] = store_url

        self.storeUpdater = plugin.StoreUpdater()
        self.storeUpdater.create_offering = MagicMock()
        self.storeUpdater.delete_offering = MagicMock()

        # Call the function
        context = {'model': MagicMock(), 'session': MagicMock()}
        pkg_dict = {'private': True, 'title': 'Example Dataset'}
        result = self.storeUpdater.after_update(context, pkg_dict)

        # Assert that the function has been called
        if store_url:
            self.storeUpdater.create_offering.assert_called_with(context, pkg_dict)
            self.storeUpdater.delete_offering.assert_called_with(context, pkg_dict)
        else:
            self.assertEquals(0, self.storeUpdater.create_offering.call_count)
            self.assertEquals(0, self.storeUpdater.delete_offering.call_count)

        # Assert that the package hasn't changed
        self.assertEquals(pkg_dict, result)


