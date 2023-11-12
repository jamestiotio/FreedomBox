# SPDX-License-Identifier: AGPL-3.0-or-later
"""FreedomBox app to manage users."""

import grp
import subprocess

import augeas
from django.utils.text import format_lazy
from django.utils.translation import gettext_lazy as _

from plinth import app as app_module
from plinth import cfg, menu
from plinth.config import DropinConfigs
from plinth.daemon import Daemon
from plinth.modules.diagnostics.check import DiagnosticCheck, Result
from plinth.package import Packages
from plinth.privileged import service as service_privileged

from . import privileged
from .components import UsersAndGroups

first_boot_steps = [
    {
        'id': 'users_firstboot',
        'url': 'users:firstboot',
        'order': 1
    },
]

_description = [
    _('Create and manage user accounts. These accounts serve as centralized '
      'authentication mechanism for most apps. Some apps further require a '
      'user account to be part of a group to authorize the user to access the '
      'app.'),
    format_lazy(
        _('Any user may login to {box_name} web interface to see a list of '
          'apps relevant to them in the home page. However, only users of '
          'the <em>admin</em> group may alter apps or system settings.'),
        box_name=_(cfg.box_name))
]


class UsersApp(app_module.App):
    """FreedomBox app for users and groups management."""

    app_id = 'users'

    _version = 5

    can_be_disabled = False

    def __init__(self):
        """Create components for the app."""
        super().__init__()

        info = app_module.Info(app_id=self.app_id, version=self._version,
                               is_essential=True, name=_('Users and Groups'),
                               icon='fa-users', description=_description,
                               manual_page='Users')
        self.add(info)

        menu_item = menu.Menu('menu-users', info.name, None, info.icon,
                              'users:index', parent_url_name='system')
        self.add(menu_item)

        packages = Packages('packages-users', [
            'ldapscripts', 'ldap-utils', 'libnss-ldapd', 'libpam-ldapd',
            'nscd', 'nslcd', 'samba-common-bin', 'slapd', 'tdb-tools'
        ])
        self.add(packages)

        dropin_configs = DropinConfigs('dropin-configs-users', [
            '/etc/apache2/includes/freedombox-auth-ldap.conf',
        ])
        self.add(dropin_configs)

        daemon = Daemon('daemon-users', 'slapd', listen_ports=[(389, 'tcp4'),
                                                               (389, 'tcp6')])
        self.add(daemon)

        # Add the admin group
        groups = {'admin': _('Access to all services and system settings')}
        users_and_groups = UsersAndGroups('users-and-groups-admin',
                                          groups=groups)
        self.add(users_and_groups)

    def diagnose(self):
        """Run diagnostics and return the results."""
        results = super().diagnose()

        results.append(_diagnose_ldap_entry('dc=thisbox'))
        results.append(_diagnose_ldap_entry('ou=people'))
        results.append(_diagnose_ldap_entry('ou=groups'))

        config = privileged.get_nslcd_config()
        results.append(_diagnose_nslcd_config(config, 'uri', 'ldapi:///'))
        results.append(_diagnose_nslcd_config(config, 'base', 'dc=thisbox'))
        results.append(_diagnose_nslcd_config(config, 'sasl_mech', 'EXTERNAL'))

        results.extend(_diagnose_nsswitch_config())

        return results

    def setup(self, old_version):
        """Install and configure the app."""
        super().setup(old_version)
        if not old_version:
            privileged.first_setup()

        privileged.setup()
        privileged.create_group('freedombox-share')


def _diagnose_ldap_entry(search_item):
    """Diagnose that an LDAP entry exists."""
    check_id = f'users-ldap-entry-{search_item}'
    result = Result.FAILED

    try:
        subprocess.check_output(
            ['ldapsearch', '-x', '-b', 'dc=thisbox', search_item])
        result = Result.PASSED
    except subprocess.CalledProcessError:
        pass

    template = _('Check LDAP entry "{search_item}"')
    description = format_lazy(template, search_item=search_item)
    parameters = {'search_item': search_item}

    return DiagnosticCheck(check_id, description, result, parameters)


def _diagnose_nslcd_config(config, key, value):
    """Diagnose that nslcd has a configuration."""
    check_id = f'users-nslcd-config-{key}'
    try:
        result = Result.PASSED if config[key] == value else Result.FAILED
    except KeyError:
        result = Result.FAILED

    template = _('Check nslcd config "{key} {value}"')
    description = format_lazy(template, key=key, value=value)
    parameters = {'key': key, 'value': value}

    return DiagnosticCheck(check_id, description, result, parameters)


def _diagnose_nsswitch_config():
    """Diagnose that Name Service Switch is configured to use LDAP."""
    nsswitch_conf = '/etc/nsswitch.conf'
    aug = augeas.Augeas(flags=augeas.Augeas.NO_LOAD +
                        augeas.Augeas.NO_MODL_AUTOLOAD)
    aug.transform('Nsswitch', nsswitch_conf)
    aug.set('/augeas/context', '/files' + nsswitch_conf)
    aug.load()

    results = []
    for database in ['passwd', 'group', 'shadow']:
        check_id = f'users-nsswitch-config-{database}'
        result = Result.FAILED
        for match in aug.match('database'):
            if aug.get(match) != database:
                continue

            for service_match in aug.match(match + '/service'):
                if 'ldap' == aug.get(service_match):
                    result = Result.PASSED
                    break

            break

        template = _('Check nsswitch config "{database}"')
        description = format_lazy(template, database=database)
        parameters = {'database': database}

        results.append(
            DiagnosticCheck(check_id, description, result, parameters))

    return results


def get_last_admin_user():
    """If there is only one admin user return its name else return None."""
    admin_users = privileged.get_group_users('admin')
    if len(admin_users) == 1 and admin_users[0]:
        return admin_users[0]

    return None


def add_user_to_share_group(username, service=None):
    """Add user to the freedombox-share group."""
    try:
        group_members = grp.getgrnam('freedombox-share').gr_mem
    except KeyError:
        group_members = []
    if username not in group_members:
        privileged.add_user_to_group(username, 'freedombox-share')
        if service:
            service_privileged.try_restart(service)
