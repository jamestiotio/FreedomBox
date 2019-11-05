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
FreedomBox app to configure ejabberd server.
"""

import json
import logging
import pathlib

from django.urls import reverse_lazy
from django.utils.translation import ugettext_lazy as _

from plinth import action_utils, actions
from plinth import app as app_module
from plinth import cfg, frontpage, menu
from plinth.daemon import Daemon
from plinth.modules import config
from plinth.modules.apache.components import Webserver
from plinth.modules.firewall.components import Firewall
from plinth.modules.letsencrypt.components import LetsEncrypt
from plinth.signals import (domain_added, post_hostname_change,
                            pre_hostname_change)
from plinth.utils import format_lazy

from .manifest import backup, clients  # noqa, pylint: disable=unused-import

version = 3

managed_services = ['ejabberd']

managed_packages = ['ejabberd']

managed_paths = [pathlib.Path('/etc/ejabberd/')]

name = _('ejabberd')

icon_filename = 'ejabberd'

short_description = _('Chat Server')

description = [
    _('XMPP is an open and standardized communication protocol. Here '
      'you can run and configure your XMPP server, called ejabberd.'),
    format_lazy(
        _('To actually communicate, you can use the <a href="{jsxc_url}">'
          'web client</a> or any other <a href=\'https://xmpp.org/'
          'software/clients\' target=\'_blank\'>XMPP client</a>. '
          'When enabled, ejabberd can be accessed by any '
          '<a href="{users_url}"> user with a {box_name} login</a>.'),
        box_name=_(cfg.box_name), users_url=reverse_lazy('users:index'),
        jsxc_url=reverse_lazy('jsxc:index'))
]

clients = clients

reserved_usernames = ['ejabberd']

manual_page = 'ejabberd'

port_forwarding_info = [
    ('TCP', 5222),
    ('TCP', 5269),
    ('TCP', 5280),
]

logger = logging.getLogger(__name__)

app = None


class EjabberdApp(app_module.App):
    """FreedomBox app for ejabberd."""

    app_id = 'ejabberd'

    def __init__(self):
        """Create components for the app."""
        super().__init__()
        menu_item = menu.Menu('menu-ejabberd', name, short_description,
                              'ejabberd', 'ejabberd:index',
                              parent_url_name='apps')
        self.add(menu_item)

        shortcut = frontpage.Shortcut(
            'shortcut-ejabberd', name, short_description=short_description,
            icon=icon_filename, description=description,
            configure_url=reverse_lazy('ejabberd:index'), clients=clients,
            login_required=True)
        self.add(shortcut)

        firewall = Firewall('firewall-ejabberd', name,
                            ports=['xmpp-client', 'xmpp-server',
                                   'xmpp-bosh'], is_external=True)
        self.add(firewall)

        webserver = Webserver('webserver-ejabberd', 'jwchat-plinth')
        self.add(webserver)

        letsencrypt = LetsEncrypt(
            'letsencrypt-ejabberd', domains=get_domains, daemons=['ejabberd'],
            should_copy_certificates=True,
            private_key_path='/etc/ejabberd/letsencrypt/{domain}/ejabberd.pem',
            certificate_path='/etc/ejabberd/letsencrypt/{domain}/ejabberd.pem',
            user_owner='ejabberd', group_owner='ejabberd',
            managing_app='ejabberd')
        self.add(letsencrypt)

        daemon = Daemon('daemon-ejabberd', managed_services[0])
        self.add(daemon)


def init():
    """Initialize the ejabberd module"""
    global app
    app = EjabberdApp()

    setup_helper = globals()['setup_helper']
    if setup_helper.get_state() != 'needs-setup' and app.is_enabled():
        app.set_enabled(True)

    pre_hostname_change.connect(on_pre_hostname_change)
    post_hostname_change.connect(on_post_hostname_change)
    domain_added.connect(on_domain_added)


def setup(helper, old_version=None):
    """Install and configure the module."""
    domainname = config.get_domainname()
    logger.info('ejabberd service domainname - %s', domainname)

    helper.call('pre', actions.superuser_run, 'ejabberd',
                ['pre-install', '--domainname', domainname])
    # XXX: Configure all other domain names
    helper.install(managed_packages)
    helper.call('post',
                app.get_component('letsencrypt-ejabberd').setup_certificates,
                [domainname])
    helper.call('post', actions.superuser_run, 'ejabberd',
                ['setup', '--domainname', domainname])
    helper.call('post', app.enable)


def get_domains():
    """Return the list of domains that ejabberd is interested in.

    XXX: Retrieve the list from ejabberd configuration.

    """
    setup_helper = globals()['setup_helper']
    if setup_helper.get_state() == 'needs-setup':
        return []

    domain_name = config.get_domainname()
    if domain_name:
        return [domain_name]

    return []


def on_pre_hostname_change(sender, old_hostname, new_hostname, **kwargs):
    """
    Backup ejabberd database before hostname is changed.
    """
    del sender  # Unused
    del kwargs  # Unused
    setup_helper = globals()['setup_helper']
    if setup_helper.get_state() == 'needs-setup':
        return

    actions.superuser_run('ejabberd', [
        'pre-change-hostname', '--old-hostname', old_hostname,
        '--new-hostname', new_hostname
    ])


def on_post_hostname_change(sender, old_hostname, new_hostname, **kwargs):
    """Update ejabberd config after hostname change."""
    del sender  # Unused
    del kwargs  # Unused
    setup_helper = globals()['setup_helper']
    if setup_helper.get_state() == 'needs-setup':
        return

    actions.superuser_run('ejabberd', [
        'change-hostname', '--old-hostname', old_hostname, '--new-hostname',
        new_hostname
    ], run_in_background=True)


def on_domain_added(sender, domain_type, name, description='', services=None,
                    **kwargs):
    """Update ejabberd config after domain name change."""
    setup_helper = globals()['setup_helper']
    if setup_helper.get_state() == 'needs-setup':
        return

    conf = actions.superuser_run('ejabberd', ['get-configuration'])
    conf = json.loads(conf)
    if name not in conf['domains']:
        actions.superuser_run('ejabberd', ['add-domain', '--domainname', name])
        app.get_component('letsencrypt-ejabberd').setup_certificates()


def diagnose():
    """Run diagnostics and return the results."""
    results = []

    results.append(action_utils.diagnose_port_listening(5222, 'tcp4'))
    results.append(action_utils.diagnose_port_listening(5222, 'tcp6'))
    results.append(action_utils.diagnose_port_listening(5269, 'tcp4'))
    results.append(action_utils.diagnose_port_listening(5269, 'tcp6'))
    results.append(action_utils.diagnose_port_listening(5443, 'tcp4'))
    results.append(action_utils.diagnose_port_listening(5443, 'tcp6'))
    results.extend(action_utils.diagnose_url_on_all('http://{host}/bosh/'))

    return results
