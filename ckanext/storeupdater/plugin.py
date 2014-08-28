from pylons import config

import ckan.plugins as plugins
import base64
import json
import logging
import os
import requests

log = logging.getLogger(__name__)
DEFAULT_VERSION = '1.0'

__dir__ = os.path.dirname(os.path.abspath(__file__))
filepath = os.path.join(__dir__, 'assets/logo-ckan.png')

with open(filepath, 'rb') as f:
    LOGO_CKAN_B64 = base64.b64encode(f.read())


class StoreUpdater(plugins.SingletonPlugin):

    plugins.implements(plugins.IPackageController, inherit=True)

    def __init__(self, name=None):
        log.debug('Init StoreUpdater plugin')
        self.site_url = config.get('ckan.site_url')
        self.store_url = config.get('ckan.store_updater.store_url')

    def _get_resource(self, pkg_dict):
        resource = {}
        name = pkg_dict.get('name', '')
        resource['name'] = pkg_dict.get('title', '')
        resource['description'] = pkg_dict.get('notes', '')
        resource['version'] = DEFAULT_VERSION
        resource['content_type'] = 'dataset'
        resource['open'] = True
        resource['link'] = '%s/dataset/%s' % (self.site_url, name)

        return resource

    def _get_offering(self, pkg_dict):
        user_nickname = plugins.toolkit.c.user

        offering = {}
        offering['name'] = pkg_dict.get('title', '')
        offering['version'] = DEFAULT_VERSION
        offering['image'] = {
            'name': 'ckan.png',
            'data': LOGO_CKAN_B64
        }
        offering['related_images'] = []
        offering['resources'] = []
        offering['resources'].append({'provider': user_nickname, 'name': pkg_dict.get('title', ''), 'version': DEFAULT_VERSION})
        offering['applications'] = []
        offering['offering_info'] = {
            'description': pkg_dict.get('notes', ''),
            'pricing': {
                'price_model': 'free'
            },
            'legal': {
                'title': pkg_dict.get('license_id', 'Not License Specified'),
                'text': 'License definitions and additional information can be found at opendefinition.org'
            }
        }
        offering['repository'] = 'Local'
        offering['open'] = True

        return offering

    def _get_tags(self, pkg_dict):
        pkg_tags = pkg_dict.get('tags', [])
        tags = set()            # Avoid duplicates
        tags.add('dataset')     # Needed to show the offering in the dataset tab.

        for tag in pkg_tags:
            tags.add(tag['name'])

        return {'tags': list(tags)}

    def _make_request(self, method, url, headers={}, data=None):

        # Include access token in the request
        usertoken = plugins.toolkit.c.usertoken
        final_headers = headers.copy()
        final_headers['Authorization'] = '%s %s' % (usertoken['token_type'], usertoken['access_token'])

        req_method = getattr(requests, method)

        try:
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
            return req
        except Exception as e:
            log.error('%s(%s): %s: %s' % (method, url, type(e).__name__, str(e)))

    def delete_offering(self, context, pkg_dict):
        user_nickname = plugins.toolkit.c.user
        package = plugins.toolkit.get_action('package_show')(context, pkg_dict)
        pkg_last_name = package.get('title')
        log.info('Deleting Offering %s' % pkg_last_name)

        if not package.get('private', False):
            # If the offering was private, it was not published
            self._make_request('delete', '%s/api/offering/offerings/%s/%s/%s' % (self.store_url, user_nickname, pkg_last_name, DEFAULT_VERSION))    # Delete offering
            self._make_request('delete', '%s/api/offering/resources/%s/%s/%s' % (self.store_url, user_nickname, pkg_last_name, DEFAULT_VERSION))    # Delete resource

    def create_offering(self, context, pkg_dict):

        user_nickname = plugins.toolkit.c.user
        private = pkg_dict.get('private', False)

        # Non-private datasets are always searchable
        if not private:
            log.info('Creating Offering %s' % pkg_dict['title'])
            pkg_name = pkg_dict.get('title')
            resource = self._get_resource(pkg_dict)
            offering = self._get_offering(pkg_dict)
            tags = self._get_tags(pkg_dict)

            # Make the request to the server
            headers = {'Content-Type': 'application/json'}

            self._make_request('post', '%s/api/offering/resources' % self.store_url, headers, json.dumps(resource))     # Create the resource
            self._make_request('post', '%s/api/offering/offerings' % self.store_url, headers, json.dumps(offering))     # Create the offering
            self._make_request('put', '%s/api/offering/offerings/%s/%s/%s/tag' % (self.store_url, user_nickname, pkg_name, DEFAULT_VERSION),
                               headers, json.dumps(tags))                                                               # Attach tags to the offering
            self._make_request('post', '%s/api/offering/offerings/%s/%s/%s/publish' % (self.store_url, user_nickname, pkg_name, DEFAULT_VERSION),
                               headers, json.dumps({'marketplaces': []}))                                               # Publish the offering
        else:
            log.info('Offering not created since the dataset %s is private' % pkg_dict['title'])

    def after_create(self, context, pkg_dict):
        if self.store_url:
            self.create_offering(context, pkg_dict)  # Create the offering
        return pkg_dict

    def after_update(self, context, pkg_dict):
        # Delete the previous offering. We need to create a new one since the store does not allow
        # to update published offerings. Open offerings are deleted permanently, so we can create a
        # new offering with the same name and version
        if self.store_url:
            self.delete_offering(context, pkg_dict)  # Delete the offering
            self.create_offering(context, pkg_dict)  # Recreate the offering
        return pkg_dict

    def after_delete(self, context, pkg_dict):
        if self.store_url:
            self.delete_offering(context, pkg_dict)  # Delete the offering
        return pkg_dict
