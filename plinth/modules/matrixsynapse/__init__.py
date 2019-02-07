#
# This file is part of FreedomBox.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
"""
FreedomBox app to configure matrix-synapse server.
"""

import json
import logging
import os

from django.urls import reverse_lazy
from django.utils.translation import ugettext_lazy as _
from ruamel.yaml.util import load_yaml_guess_indent

from plinth import service as service_module
from plinth import action_utils, actions, frontpage
from plinth.menu import main_menu
from plinth.utils import YAMLFile

from .manifest import backup, clients

version = 4

managed_services = ['matrix-synapse']

managed_packages = ['matrix-synapse', 'matrix-synapse-ldap3']

name = _('Matrix Synapse')

short_description = _('Chat Server')

description = [
    _('<a href="https://matrix.org/docs/guides/faq.html">Matrix</a> is an new '
      'ecosystem for open, federated instant messaging and VoIP. Synapse is a '
      'server implementing the Matrix protocol. It provides chat groups, '
      'audio/video calls, end-to-end encryption, multiple device '
      'synchronization and does not require phone numbers to work. Users on a '
      'given Matrix server can converse with users on all other Matrix '
      'servers via federation.'),
    _('To communicate, you can use the '
      '<a href="https://matrix.org/docs/projects/">available clients</a> '
      'for mobile, desktop and the web. <a href="https://riot.im/">Riot</a> '
      'client is recommended.')
]

clients = clients

service = None

manual_page = 'MatrixSynapse'

logger = logging.getLogger(__name__)

SERVER_NAME_PATH = "/etc/matrix-synapse/conf.d/server_name.yaml"
CONFIG_FILE_PATH = '/etc/matrix-synapse/homeserver.yaml'


def init():
    """Initialize the matrix-synapse module."""
    menu = main_menu.get('apps')
    menu.add_urlname(name, 'matrixsynapse', 'matrixsynapse:index',
                     short_description)

    global service
    setup_helper = globals()['setup_helper']
    if setup_helper.get_state() != 'needs-setup':
        service = service_module.Service('matrix-synapse', name, ports=[
            'matrix-synapse-plinth'
        ], is_external=True, is_enabled=is_enabled, enable=enable,
                                         disable=disable)
        if is_enabled():
            add_shortcut()


def setup(helper, old_version=None):
    """Install and configure the module."""
    helper.install(managed_packages)
    global service
    if service is None:
        service = service_module.Service('matrix-synapse', name, ports=[
            'matrix-synapse-plinth'
        ], is_external=True, is_enabled=is_enabled, enable=enable,
                                         disable=disable)

    helper.call('post', actions.superuser_run, 'matrixsynapse',
                ['post-install'])
    helper.call('post', service.notify_enabled, None, True)
    helper.call('post', add_shortcut)


def add_shortcut():
    """Add a shortcut to the frontpage."""
    frontpage.add_shortcut('matrixsynapse', name, details=description,
                           short_description=short_description,
                           configure_url=reverse_lazy('matrixsynapse:index'),
                           login_required=True)


def is_setup():
    """Return whether the Matrix Synapse server is setup."""
    return os.path.exists(SERVER_NAME_PATH)


def is_enabled():
    """Return whether the module is enabled."""
    return action_utils.service_is_enabled('matrix-synapse')


def enable():
    """Enable the module."""
    actions.superuser_run('matrixsynapse', ['enable'])
    add_shortcut()


def disable():
    """Enable the module."""
    actions.superuser_run('matrixsynapse', ['disable'])
    frontpage.remove_shortcut('matrixsynapse')


def diagnose():
    """Run diagnostics and return the results."""
    results = []

    results.append(action_utils.diagnose_port_listening(8008, 'tcp4'))
    results.append(action_utils.diagnose_port_listening(8448, 'tcp4'))
    results.extend(
        action_utils.diagnose_url_on_all('https://{host}/_matrix',
                                         check_certificate=False))

    return results


def get_configured_domain_name():
    """Return the currently configured domain name."""
    if not is_setup():
        return None

    with open(SERVER_NAME_PATH) as config_file:
        config, _, _ = load_yaml_guess_indent(config_file)

    return config['server_name']


def get_public_registration_status():
    """Return whether public registration is enabled."""
    output = actions.superuser_run('matrixsynapse',
                                   ['public-registration', 'status'])
    return output.strip() == 'enabled'


def has_valid_certificate():
    """Return whether the configured domain name has a valid
    Let's Encrypt certificate."""
    domain_name = get_configured_domain_name()
    status = actions.superuser_run('letsencrypt', ['get-status'])
    status = json.loads(status)
    if domain_name in status['domains']:
        return status['domains'][domain_name][
            'certificate_available'] == "true"
    return False
