# SPDX-License-Identifier: AGPL-3.0-or-later
"""
FreedomBox app for power controls.
"""

from django.utils.translation import gettext_lazy as _

from plinth import app as app_module
from plinth.modules.backups.components import BackupRestore

from . import manifest

_description = [_('Restart or shut down the system.')]

app = None


class PowerApp(app_module.App):
    """FreedomBox app for power controls."""

    app_id = 'power'

    _version = 1

    def __init__(self):
        """Create components for the app."""
        super().__init__()

        info = app_module.Info(app_id=self.app_id, version=self._version,
                               is_essential=True, name=_('Power'),
                               description=_description, manual_page='Power')
        self.add(info)

        backup_restore = BackupRestore('backup-restore-power',
                                       **manifest.backup)
        self.add(backup_restore)

        # not in menu, see issue #834
