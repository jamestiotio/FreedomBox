# SPDX-License-Identifier: AGPL-3.0-or-later
"""Configure Radicale."""

import os

import augeas

from plinth import action_utils
from plinth.actions import privileged

CONFIG_FILE = '/etc/radicale/config'
LOG_PATH = '/var/log/radicale'


@privileged
def configure(rights_type: str):
    """Set the radicale rights type to a particular value."""
    if rights_type == 'owner_only':
        # Default rights file is equivalent to owner_only.
        rights_type = 'from_file'

    aug = load_augeas()
    aug.set('/files' + CONFIG_FILE + '/rights/type', rights_type)
    aug.save()

    action_utils.service_try_restart('uwsgi')


@privileged
def fix_paths():
    """Fix log path to work around a bug."""
    # Workaround for bug in radicale's uwsgi script (#931201)
    if not os.path.exists(LOG_PATH):
        os.makedirs(LOG_PATH)


def load_augeas():
    """Initialize Augeas."""
    aug = augeas.Augeas(flags=augeas.Augeas.NO_LOAD +
                        augeas.Augeas.NO_MODL_AUTOLOAD)

    # INI file lens
    aug.set('/augeas/load/Puppet/lens', 'Puppet.lns')
    aug.set('/augeas/load/Puppet/incl[last() + 1]', CONFIG_FILE)

    aug.load()
    return aug
