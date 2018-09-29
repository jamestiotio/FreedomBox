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

@apps @mumble @backups
Feature: Mumble Voice Chat
  Run Mumble voice chat server.

Background:
  Given I'm a logged in user
  Given the mumble application is installed

Scenario: Enable mumble application
  Given the mumble application is disabled
  When I enable the mumble application
  Then the mumble service should be running

Scenario: Disable mumble application
  Given the mumble application is enabled
  When I disable the mumble application
  Then the mumble service should not be running

# TODO: Improve this to actually check that data such as rooms, identity or
# certificates are restored.
Scenario: Backup and restore mumble
  Given the mumble application is enabled
  When I create a backup of the mumble app data
  And I export the mumble app data backup
  And I restore the mumble app data backup
  Then the mumble service should be running
