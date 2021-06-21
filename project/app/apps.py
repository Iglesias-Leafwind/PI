## @package app
#  this model contains project configuration
#
#  More details.
from django.apps import AppConfig


class ProjectConfig(AppConfig):
    default_auto_field = 'django.db.features.BigAutoField'
    name = 'project'
