# SPDX-License-Identifier: AGPL-3.0-or-later
"""
FreedomBox app for system diagnostics.
"""

import collections
import logging
import pathlib
import threading

import psutil
from django.utils.translation import gettext_lazy as _
from django.utils.translation import gettext_noop

from plinth import app as app_module
from plinth import cfg, daemon, glib, menu
from plinth import operation as operation_module
from plinth.modules.apache.components import diagnose_url_on_all
from plinth.modules.backups.components import BackupRestore

from . import manifest

_description = [
    _('The system diagnostic test will run a number of checks on your '
      'system to confirm that applications and services are working as '
      'expected.')
]

logger = logging.Logger(__name__)

running_task = None

current_results = {}

results_lock = threading.Lock()
running_task_lock = threading.Lock()


class DiagnosticsApp(app_module.App):
    """FreedomBox app for diagnostics."""

    app_id = 'diagnostics'

    _version = 1

    can_be_disabled = False

    def __init__(self):
        """Create components for the app."""
        super().__init__()
        info = app_module.Info(app_id=self.app_id, version=self._version,
                               is_essential=True, name=_('Diagnostics'),
                               icon='fa-heartbeat', description=_description,
                               manual_page='Diagnostics')
        self.add(info)

        menu_item = menu.Menu('menu-diagnostics', info.name, None, info.icon,
                              'diagnostics:index', parent_url_name='system')
        self.add(menu_item)

        backup_restore = BackupRestore('backup-restore-diagnostics',
                                       **manifest.backup)
        self.add(backup_restore)

    @staticmethod
    def post_init():
        """Perform post initialization operations."""
        # Check periodically for low RAM space
        interval = 180 if cfg.develop else 3600
        glib.schedule(interval, _warn_about_low_ram_space)

        # Run diagnostics once a day
        interval = 180 if cfg.develop else 86400
        glib.schedule(interval, _start_background_diagnostics)

    def setup(self, old_version):
        """Install and configure the app."""
        super().setup(old_version)
        self.enable()

    def diagnose(self):
        """Run diagnostics and return the results."""
        results = super().diagnose()
        results.append(daemon.diagnose_port_listening(8000, 'tcp4'))
        results.extend(
            diagnose_url_on_all('http://{host}/plinth/',
                                check_certificate=False))

        return results


def start_task():
    """Start the run task in a separate thread."""
    global running_task
    with running_task_lock:
        if running_task:
            raise Exception('Task already running')

        running_task = threading.Thread(target=run_on_all_enabled_modules)

    running_task.start()


def run_on_all_enabled_modules():
    """Run diagnostics on all the enabled modules and store the result."""
    global current_results

    # Four result strings returned by tests, mark for translation and
    # translate later.
    gettext_noop('passed')
    gettext_noop('failed')
    gettext_noop('error')
    gettext_noop('warning')

    apps = []

    with results_lock:
        current_results = {
            'apps': [],
            'results': collections.OrderedDict(),
            'progress_percentage': 0
        }

        for app in app_module.App.list():
            # Don't run diagnostics on apps have not been setup yet.
            # However, run on apps that need an upgrade.
            if app.needs_setup():
                continue

            if not app.is_enabled():
                continue

            if not app.has_diagnostics():
                continue

            apps.append((app.app_id, app))
            app_name = app.info.name or app.app_id
            current_results['results'][app.app_id] = {'name': app_name}

        current_results['apps'] = apps

    for current_index, (app_id, app) in enumerate(apps):
        app_results = {
            'diagnosis': None,
            'exception': None,
        }

        try:
            app_results['diagnosis'] = app.diagnose()
        except Exception as exception:
            logger.exception('Error running %s diagnostics - %s', app_id,
                             exception)
            app_results['exception'] = str(exception)

        with results_lock:
            current_results['results'][app_id].update(app_results)
            current_results['progress_percentage'] = \
                int((current_index + 1) * 100 / len(apps))

    global running_task
    with running_task_lock:
        running_task = None


def _get_memory_info_from_cgroups():
    """Return information about RAM usage from cgroups."""
    cgroups_memory_path = pathlib.Path('/sys/fs/cgroup/memory')
    memory_limit_file = cgroups_memory_path / 'memory.limit_in_bytes'
    memory_usage_file = cgroups_memory_path / 'memory.usage_in_bytes'
    memory_stat_file = cgroups_memory_path / 'memory.stat'

    try:
        memory_total = int(memory_limit_file.read_text())
        memory_usage = int(memory_usage_file.read_text())
        memory_stat_lines = memory_stat_file.read_text().split('\n')
    except OSError:
        return {}

    memory_inactive = int([
        line.rsplit(maxsplit=1)[1] for line in memory_stat_lines
        if line.startswith('total_inactive_file')
    ][0])
    memory_used = memory_usage - memory_inactive

    return {
        'total_bytes': memory_total,
        'percent_used': memory_used * 100 / memory_total,
        'free_bytes': memory_total - memory_used
    }


def _get_memory_info():
    """Return RAM usage information."""
    memory_info = psutil.virtual_memory()

    cgroups_memory_info = _get_memory_info_from_cgroups()
    if cgroups_memory_info and cgroups_memory_info[
            'total_bytes'] < memory_info.total:
        return cgroups_memory_info

    return {
        'total_bytes': memory_info.total,
        'percent_used': memory_info.percent,
        'free_bytes': memory_info.available
    }


def _warn_about_low_ram_space(request):
    """Warn about insufficient RAM space."""
    from plinth.notification import Notification

    memory_info = _get_memory_info()
    if memory_info['free_bytes'] < 1024**3:
        # Translators: This is the unit of computer storage Mebibyte similar to
        # Megabyte.
        memory_available_unit = gettext_noop('MiB')
        memory_available = memory_info['free_bytes'] / 1024**2
    else:
        # Translators: This is the unit of computer storage Gibibyte similar to
        # Gigabyte.
        memory_available_unit = gettext_noop('GiB')
        memory_available = memory_info['free_bytes'] / 1024**3

    show = False
    if memory_info['percent_used'] > 90:
        severity = 'error'
        advice_message = gettext_noop(
            'You should disable some apps to reduce memory usage.')
        show = True
    elif memory_info['percent_used'] > 75:
        severity = 'warning'
        advice_message = gettext_noop(
            'You should not install any new apps on this system.')
        show = True

    if not show:
        try:
            Notification.get('diagnostics-low-ram-space').delete()
        except KeyError:
            pass
        return

    message = gettext_noop(
        # xgettext:no-python-format
        'System is low on memory: {percent_used}% used, {memory_available} '
        '{memory_available_unit} free. {advice_message}')
    title = gettext_noop('Low Memory')
    data = {
        'app_icon': 'fa-heartbeat',
        'app_name': 'translate:' + gettext_noop('Diagnostics'),
        'percent_used': f'{memory_info["percent_used"]:.1f}',
        'memory_available': f'{memory_available:.1f}',
        'memory_available_unit': 'translate:' + memory_available_unit,
        'advice_message': 'translate:' + advice_message
    }
    actions = [{'type': 'dismiss'}]
    Notification.update_or_create(id='diagnostics-low-ram-space',
                                  app_id='diagnostics', severity=severity,
                                  title=title, message=message,
                                  actions=actions, data=data, group='admin')


def _start_background_diagnostics(request):
    """Start daily diagnostics as a background operation."""
    operation = operation_module.manager.new(
        'diagnostics', gettext_noop('Running background diagnostics'),
        _run_background_diagnostics, [], show_message=False,
        show_notification=False)
    operation.join()


def _run_background_diagnostics():
    """Run diagnostics and notify for failures."""
    from plinth.notification import Notification

    # In case diagnostics are already running, skip the background run for
    # today.
    global running_task
    with running_task_lock:
        if running_task:
            logger.warning('Diagnostics are already running, skip background '
                           'diagnostics for today.')
            return

        # Set something in the global so we won't be interrupted.
        running_task = 'background'

    run_on_all_enabled_modules()
    with results_lock:
        results = current_results['results']

    with running_task_lock:
        running_task = None

    exception_count = 0
    error_count = 0
    failure_count = 0
    warning_count = 0
    for _app_id, app_data in results.items():
        if app_data['exception']:
            exception_count += 1

        for _test, result in app_data['diagnosis']:
            if result == 'error':
                error_count += 1
            elif result == 'failed':
                failure_count += 1
            elif cfg.develop and result == 'warning':
                warning_count += 1

    notification_id = 'diagnostics-background'
    if exception_count > 0:
        severity = 'error'
        issue_count = exception_count
        if exception_count > 1:
            issue_type = 'translate:exceptions'
        else:
            issue_type = 'translate:exception'

    elif error_count > 0:
        severity = 'error'
        issue_count = error_count
        if error_count > 1:
            issue_type = 'translate:errors'
        else:
            issue_type = 'translate:error'

    elif failure_count > 0:
        severity = 'error'
        issue_count = failure_count
        if failure_count > 1:
            issue_type = 'translate:failures'
        else:
            issue_type = 'translate:failure'

    elif warning_count > 0:
        severity = 'warning'
        issue_count = warning_count
        if warning_count > 1:
            issue_type = 'translate:warnings'
        else:
            issue_type = 'translate:warning'

    else:
        # Don't display a notification if there are no issues.
        return

    message = gettext_noop(
        # xgettext:no-python-format
        'Background diagnostics completed with {issue_count} {issue_type}')
    title = gettext_noop(
        # xgettext:no-python-format
        'Background diagnostics results')
    data = {
        'app_icon': 'fa-heartbeat',
        'issue_count': issue_count,
        'issue_type': issue_type,
    }
    actions = [{
        'type': 'link',
        'class': 'primary',
        'text': gettext_noop('Go to diagnostics results'),
        'url': 'diagnostics:index'
    }, {
        'type': 'dismiss'
    }]
    note = Notification.update_or_create(id=notification_id,
                                         app_id='diagnostics',
                                         severity=severity, title=title,
                                         message=message, actions=actions,
                                         data=data, group='admin')
    note.dismiss(False)
