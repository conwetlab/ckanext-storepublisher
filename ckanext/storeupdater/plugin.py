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
