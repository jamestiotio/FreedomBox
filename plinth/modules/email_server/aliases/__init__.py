# SPDX-License-Identifier: AGPL-3.0-or-later
"""Manage email aliases."""

import contextlib
import pwd
import sqlite3

from plinth import actions

from . import models


@contextlib.contextmanager
def _get_cursor():
    """Return a DB cursor as context manager."""
    # Turn ON autocommit mode
    db_path = '/var/lib/postfix/freedombox-aliases/aliases.sqlite3'
    connection = sqlite3.connect(db_path, isolation_level=None)
    connection.row_factory = sqlite3.Row
    try:
        cursor = connection.cursor()
        yield cursor
    finally:
        connection.close()


def get(uid):
    """Get all aliases of a user."""
    query = 'SELECT name, value, status FROM alias WHERE value=?'
    with _get_cursor() as cursor:
        rows = cursor.execute(query, (uid, ))
        return [models.Alias(**row) for row in rows]


def exists(name):
    """Return whether alias is already taken."""
    try:
        pwd.getpwnam(name)
        return True
    except KeyError:
        pass

    with _get_cursor() as cursor:
        query = 'SELECT COUNT(*) FROM alias WHERE name=?'
        cursor.execute(query, (name, ))
        return cursor.fetchone()[0] != 0


def put(uid, name):
    """Insert if not exists a new alias."""
    query = 'INSERT INTO alias (name, value, status) VALUES (?, ?, ?)'
    with _get_cursor() as cursor:
        try:
            cursor.execute(query, (name, uid, 1))
        except sqlite3.IntegrityError:
            pass  # Alias exists, rare since we are already checking


def delete(uid, aliases):
    """Delete a set of aliases."""
    query = 'DELETE FROM alias WHERE value=? AND name=?'
    parameter_seq = ((uid, name) for name in aliases)
    with _get_cursor() as cursor:
        cursor.execute('BEGIN')
        cursor.executemany(query, parameter_seq)
        cursor.execute('COMMIT')


def enable(uid, aliases):
    """Enable a list of aliases."""
    return _set_status(uid, aliases, 1)


def disable(uid, aliases):
    """Disable a list of aliases."""
    return _set_status(uid, aliases, 0)


def _set_status(uid, aliases, status):
    """Set the status value of a list of aliases."""
    query = 'UPDATE alias SET status=? WHERE value=? AND name=?'
    parameter_seq = ((status, uid, name) for name in aliases)
    with _get_cursor() as cursor:
        cursor.execute('BEGIN')
        cursor.executemany(query, parameter_seq)
        cursor.execute('COMMIT')


def first_setup():
    """Create the database file and schema inside it."""
    actions.superuser_run('email_server', ['-i', 'aliases', 'setup'])

    # Create schema if not exists
    query = '''
PRAGMA journal_mode=WAL;
BEGIN;
CREATE TABLE IF NOT EXISTS alias (
    name TEXT NOT NULL,
    value INTEGER NOT NULL,
    status INTEGER NOT NULL,
    PRIMARY KEY (name)
);
COMMIT;
'''
    with _get_cursor() as cursor:
        cursor.executescript(query)
