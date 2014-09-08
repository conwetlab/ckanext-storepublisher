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

import ckan.plugins as plugins


class StoreUpdater(plugins.SingletonPlugin):

    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IRoutes, inherit=True)

    def update_config(self, config):
        # Add this plugin's templates dir to CKAN's extra_template_paths, so
        # that CKAN will use this plugin's custom templates.
        plugins.toolkit.add_template_directory(config, 'templates')

        # Register this plugin's fanstatic directory with CKAN.
        plugins.toolkit.add_resource('fanstatic', 'storeupdater')

    def before_map(self, m):
        # DataSet acquired notification
        m.connect('dataset_publish', '/dataset/publish/{id}', action='publish',
                  controller='ckanext.storeupdater.controllers.ui_controller:PublishControllerUI',
                  ckan_icon='shopping-cart')
        return m
