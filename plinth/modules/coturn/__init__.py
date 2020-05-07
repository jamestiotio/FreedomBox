# SPDX-License-Identifier: AGPL-3.0-or-later
"""
FreedomBox app to configure Coturn server.
"""

import json
import pathlib

from django.utils.translation import ugettext_lazy as _

from plinth import actions
from plinth import app as app_module
from plinth import menu
from plinth.daemon import Daemon
from plinth.modules import names
from plinth.modules.firewall.components import Firewall
from plinth.modules.letsencrypt.components import LetsEncrypt
from plinth.modules.users.components import UsersAndGroups

from .manifest import backup  # noqa, pylint: disable=unused-import

version = 1

managed_services = ['coturn']

managed_packages = ['coturn']

managed_paths = [pathlib.Path('/etc/coturn/')]

_description = [
    _('Coturn is a server to facilitate audio/video calls and conferences by '
      'providing an implementation of TURN and STUN protocols. WebRTC, SIP '
      'and other communication servers can use it to establish a call between '
      'parties who are otherwise unable connect to each other.'),
    _('It is not meant to be used directly by users. Servers such as '
      'matrix-synapse need to be configured with the details provided here.'),
]

port_forwarding_info = [
    ('UDP', 3478),
    ('TCP', 3478),
    ('UDP', 3479),
    ('TCP', 3479),
    ('UDP', 5349),
    ('TCP', 5349),
    ('UDP', 5350),
    ('TCP', 5350),
    # XXX: Add relay ports here
]

app = None


class CoturnApp(app_module.App):
    """FreedomBox app for Coturn."""

    app_id = 'coturn'

    def __init__(self):
        """Create components for the app."""
        super().__init__()

        info = app_module.Info(app_id=self.app_id, version=version,
                               name=_('Coturn'), icon_filename='coturn',
                               short_description=_('VoIP Helper'),
                               description=_description, manual_page='Coturn')
        self.add(info)

        menu_item = menu.Menu('menu-coturn', info.name, info.short_description,
                              info.icon_filename, 'coturn:index',
                              parent_url_name='apps', advanced=True)
        self.add(menu_item)

        firewall = Firewall('firewall-coturn', info.name,
                            ports=['coturn-freedombox'], is_external=True)
        self.add(firewall)

        letsencrypt = LetsEncrypt(
            'letsencrypt-coturn', domains=get_domains,
            daemons=managed_services, should_copy_certificates=True,
            private_key_path='/etc/coturn/certs/pkey.pem',
            certificate_path='/etc/coturn/certs/cert.pem',
            user_owner='turnserver', group_owner='turnserver',
            managing_app='coturn')
        self.add(letsencrypt)

        daemon = Daemon(
            'daemon-coturn', managed_services[0],
            listen_ports=[(3478, 'udp4'), (3478, 'udp6'), (3478, 'tcp4'),
                          (3478, 'tcp6'), (3479, 'udp4'), (3479, 'udp6'),
                          (3479, 'tcp4'), (3479, 'tcp6'), (5349, 'udp4'),
                          (5349, 'udp6'), (5349, 'tcp4'), (5349, 'tcp6'),
                          (5350, 'udp4'), (5350, 'udp6'), (5350, 'tcp4'),
                          (5350, 'tcp6')])
        self.add(daemon)

        users_and_groups = UsersAndGroups('users-and-groups-coturn',
                                          reserved_usernames=['turnserver'])
        self.add(users_and_groups)


def init():
    """Initialize the Coturn module."""
    global app
    app = CoturnApp()

    setup_helper = globals()['setup_helper']
    if setup_helper.get_state() != 'needs-setup' and app.is_enabled():
        app.set_enabled(True)


def setup(helper, old_version=None):
    """Install and configure the module."""
    helper.install(managed_packages)
    helper.call('post', actions.superuser_run, 'coturn', ['setup'])
    helper.call('post', app.enable)
    app.get_component('letsencrypt-coturn').setup_certificates()


def get_available_domains():
    """Return an iterator with all domains able to have a certificate."""
    return (domain.name for domain in names.components.DomainName.list()
            if domain.domain_type.can_have_certificate)


def get_domain():
    """Read TLS domain from config file select first available if none."""
    config = get_config()
    if config['realm']:
        return get_config()['realm']

    domain = next(get_available_domains(), None)
    set_domain(domain)

    return domain


def get_domains():
    """Return a list with the configured domains."""
    domain = get_domain()
    if domain:
        return [domain]

    return []


def set_domain(domain):
    """Set the TLS domain by writing a file to data directory."""
    if domain:
        actions.superuser_run('coturn', ['set-domain', domain])


def get_config():
    """Return the coturn server configuration."""
    output = actions.superuser_run('coturn', ['get-config'])
    return json.loads(output)
