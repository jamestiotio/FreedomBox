# SPDX-License-Identifier: AGPL-3.0-or-later
"""Helper for security configuration."""

import os

from plinth.actions import privileged

ACCESS_CONF_FILE = '/etc/security/access.d/50freedombox.conf'
ACCESS_CONF_FILE_OLD = '/etc/security/access.conf'
ACCESS_CONF_SNIPPET = '-:ALL EXCEPT root fbx plinth (admin) (sudo):ALL'
OLD_ACCESS_CONF_SNIPPET = '-:ALL EXCEPT root fbx (admin) (sudo):ALL'
ACCESS_CONF_SNIPPETS = [OLD_ACCESS_CONF_SNIPPET, ACCESS_CONF_SNIPPET]


@privileged
def enable_restricted_access():
    """Restrict console login to users in admin or sudo group."""
    try:
        os.mkdir(os.path.dirname(ACCESS_CONF_FILE))
    except FileExistsError:
        pass

    with open(ACCESS_CONF_FILE, 'w', encoding='utf-8') as conffile:
        conffile.write(ACCESS_CONF_SNIPPET + '\n')


@privileged
def disable_restricted_access():
    """Don't restrict console login to users in admin or sudo group."""
    with open(ACCESS_CONF_FILE_OLD, 'r', encoding='utf-8') as conffile:
        lines = conffile.readlines()

    with open(ACCESS_CONF_FILE_OLD, 'w', encoding='utf-8') as conffile:
        for line in lines:
            if line.strip() not in ACCESS_CONF_SNIPPETS:
                conffile.write(line)

    try:
        os.remove(ACCESS_CONF_FILE)
    except OSError:
        pass


def get_restricted_access_enabled():
    """Return whether restricted access is enabled."""
    with open(ACCESS_CONF_FILE_OLD, 'r', encoding='utf-8') as conffile:
        if any(line.strip() in ACCESS_CONF_SNIPPETS
               for line in conffile.readlines()):
            return True

    try:
        with open(ACCESS_CONF_FILE, 'r', encoding='utf-8') as conffile:
            return any(line.strip() in ACCESS_CONF_SNIPPETS
                       for line in conffile.readlines())
    except FileNotFoundError:
        return False
