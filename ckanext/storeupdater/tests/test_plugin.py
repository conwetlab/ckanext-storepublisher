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

import unittest

from mock import MagicMock
from nose_parameterized import parameterized


class PluginTest(unittest.TestCase):

    def setUp(self):

        # Mocks
        self._toolkit = plugin.plugins.toolkit
        plugin.plugins.toolkit = MagicMock()

        # Create the plugin
        self.storeUpdater = plugin.StoreUpdater()

    def tearDown(self):
        plugin.plugins.toolkit = self._toolkit

    @parameterized.expand([
        (plugin.plugins.IConfigurer,),
        (plugin.plugins.IRoutes,),
    ])
    def test_implementation(self, interface):
        self.assertTrue(interface.implemented_by(plugin.StoreUpdater))

    def test_map(self):
        # Call the method
        m = MagicMock()
        self.storeUpdater.before_map(m)

        # Test that the connect method has been called
        m.connect.assert_called_once_with('dataset_publish', '/dataset/publish/{id}', action='publish',
                                          controller='ckanext.storeupdater.controllers.ui_controller:PublishControllerUI',
                                          ckan_icon='shopping-cart')
