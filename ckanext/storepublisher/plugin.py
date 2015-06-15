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

import ckan.plugins as plugins

from store_connector import StoreConnector
from pylons import config


class StorePublisher(plugins.SingletonPlugin):

    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IPackageController, inherit=True)
    plugins.implements(plugins.IRoutes, inherit=True)

    def __init__(self, name=None):
        self._store_connector = StoreConnector(config)

    def update_config(self, config):
        # Add this plugin's templates dir to CKAN's extra_template_paths, so
        # that CKAN will use this plugin's custom templates.
        plugins.toolkit.add_template_directory(config, 'templates')

        # Register this plugin's fanstatic directory with CKAN.
        plugins.toolkit.add_resource('fanstatic', 'storepublisher')

    def before_map(self, m):
        # Publish data offering controller
        m.connect('dataset_publish', '/dataset/publish/{id}', action='publish',
                  controller='ckanext.storepublisher.controllers.ui_controller:PublishControllerUI',
                  ckan_icon='shopping-cart')
        return m

    ######################################################################
    ######################### IPACKAGECONTROLLER #########################
    ######################################################################

    def after_delete(self, context, pkg_dict):

        dataset = plugins.toolkit.get_action('package_show')(context, pkg_dict)
        self._store_connector.delete_attached_resources(dataset)

        return pkg_dict
