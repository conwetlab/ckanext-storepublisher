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
import os
import unittest

from mock import MagicMock
from nose_parameterized import parameterized


MISSING_ERROR = 'This filed is required to publish the offering'

__dir__ = os.path.dirname(os.path.abspath(__file__))
filepath = os.path.join(__dir__, '../assets/logo-ckan.png')

with open(filepath, 'rb') as f:
    LOGO_CKAN_B64 = base64.b64encode(f.read())


class UIControllerTest(unittest.TestCase):

    def setUp(self):

        self._toolkit = controller.plugins.toolkit
        controller.plugins.toolkit = MagicMock()
        controller.plugins.toolkit.NotAuthorized = self._toolkit.NotAuthorized

        self._request = controller.request
        controller.request = MagicMock()

        self._helpers = controller.helpers
        controller.helpers = MagicMock()

        self._base64 = controller.base64
        controller.base64 = MagicMock()

        self._StoreConnector = controller.StoreConnector
        self._store_connector_instance = MagicMock()
        controller.StoreConnector = MagicMock(return_value=self._store_connector_instance)

        # Create the plugin
        self.instanceController = controller.PublishControllerUI()

    def tearDown(self):
        controller.StoreConnector = self._StoreConnector

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
        (True,  False, {'name': 'a', 'version': '1.0', 'pkg_id': 'package_id'},                               controller.StoreException('Impossible to connect with the Store')),
        (True,  False, {'name': 'a', 'version': '1.0', 'pkg_id': 'package_id', 'update_acquire_url': ''},     controller.StoreException('Impossible to connect with the Store')),
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
    def test_publish(self, allowed, private, post_content={}, create_offering_res='http://some_url.com'):

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
        self._store_connector_instance.create_offering = MagicMock(side_effect=[create_offering_res])
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
                self.assertEquals(0, self._store_connector_instance.create_offering.call_count)
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
                    'image_base64': expected_image
                }

                self._store_connector_instance.create_offering.assert_called_once_with(current_package, expected_data)

                if isinstance(create_offering_res, Exception):
                    errors['Store'] = [create_offering_res.message]
                    # The package should not be updated if the create_offering returns an error
                    # even if 'update_acquire_url' is present in the request content.
                    self.assertEquals(0, package_update.call_count)

                else:
                    controller.helpers.flash_success.assert_called_once_with('Offering <a href="%s" target="_blank">' % create_offering_res +
                                                                             '%s</a> published correctly.' % post_content['name'],
                                                                             allow_html=True)

        expected_pkg = current_package.copy()
        expected_pkg['tag_string'] = ','.join([tag['name'] for tag in current_package['tags']])
        self.assertEquals(expected_pkg, controller.plugins.toolkit.c.pkg_dict)
        self.assertEquals(errors, controller.plugins.toolkit.c.errors)

        controller.plugins.toolkit.render('package/publish.html')
