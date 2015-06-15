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

import ckanext.storepublisher.plugin as plugin

import unittest

from mock import MagicMock
from nose_parameterized import parameterized


class PluginTest(unittest.TestCase):

    def setUp(self):

        # Mocks
        self._toolkit = plugin.plugins.toolkit
        plugin.plugins.toolkit = MagicMock()
        self._StoreConnector = plugin.StoreConnector
        self._store_connector_instance = MagicMock()
        plugin.StoreConnector = MagicMock(return_value=self._store_connector_instance)

        # Create the plugin
        self.storePublisher = plugin.StorePublisher()

    def tearDown(self):
        plugin.plugins.toolkit = self._toolkit
        plugin.StoreConnector = self._StoreConnector

    @parameterized.expand([
        (plugin.plugins.IConfigurer,),
        (plugin.plugins.IRoutes,),
        (plugin.plugins.IPackageController,),
    ])
    def test_implementation(self, interface):
        self.assertTrue(interface.implemented_by(plugin.StorePublisher))

    def test_config(self):
        # Call the method
        config = {'config1': 'abcdef', 'config2': '12345'}
        self.storePublisher.update_config(config)

        # Check that the config has been updated
        plugin.plugins.toolkit.add_template_directory.assert_called_once_with(config, 'templates')
        plugin.plugins.toolkit.add_resource.assert_called_once_with('fanstatic', 'storepublisher')

    def test_map(self):
        # Call the method
        m = MagicMock()
        self.storePublisher.before_map(m)

        # Test that the connect method has been called
        m.connect.assert_called_once_with('dataset_publish', '/dataset/publish/{id}', action='publish',
                                          controller='ckanext.storepublisher.controllers.ui_controller:PublishControllerUI',
                                          ckan_icon='shopping-cart')

    def test_after_delete(self):
        dataset = MagicMock()
        action = MagicMock(return_value=dataset)
        plugin.plugins.toolkit.get_action = MagicMock(return_value=action)

        # Call the function
        context = {'user': MagicMock()}
        dataset_info = {'pkg_id': 'example-pkg-id'}
        self.storePublisher.after_delete(context, dataset_info)

        # Verifications
        self._store_connector_instance.delete_attached_resources.assert_called_once_with(dataset)
        action.assert_called_once_with(context, dataset_info)
        plugin.plugins.toolkit.get_action.assert_called_once_with('package_show')
