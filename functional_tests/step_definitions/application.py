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

import pytest
import splinter
from pytest_bdd import given, parsers, then, when

from support import application


@given(parsers.parse('the {app_name:w} application is installed'))
def application_is_installed(browser, app_name):
    application.install(browser, app_name)


@given(parsers.parse('the {app_name:w} application is enabled'))
def application_is_enabled(browser, app_name):
    application.enable(browser, app_name)


@given(parsers.parse('the {app_name:w} application is disabled'))
def application_is_disabled(browser, app_name):
    application.disable(browser, app_name)


@given(parsers.parse('the network time application is enabled'))
def ntp_is_enabled(browser):
    application.enable(browser, 'ntp')


@given(parsers.parse('the network time application is disabled'))
def ntp_is_disabled(browser):
    application.disable(browser, 'ntp')


@when(parsers.parse('I set the time zone to {time_zone:S}'))
def time_zone_set(browser, time_zone):
    application.time_zone_set(browser, time_zone)


@then(parsers.parse('the time zone should be {time_zone:S}'))
def time_zone_assert(browser, time_zone):
    assert time_zone == application.time_zone_get(browser)


@given(parsers.parse('the service discovery application is enabled'))
def avahi_is_enabled(browser):
    application.enable(browser, 'avahi')


@given(parsers.parse('the service discovery application is disabled'))
def avahi_is_disabled(browser):
    application.disable(browser, 'avahi')


@when(parsers.parse('I enable the {app_name:w} application'))
def enable_application(browser, app_name):
    application.enable(browser, app_name)


@when(parsers.parse('I disable the {app_name:w} application'))
def disable_application(browser, app_name):
    application.disable(browser, app_name)


@when(parsers.parse('I enable the network time application'))
def enable_ntp(browser):
    application.enable(browser, 'ntp')


@when(parsers.parse('I disable the network time application'))
def disable_ntp(browser):
    application.disable(browser, 'ntp')


@when(parsers.parse('I enable the service discovery application'))
def enable_avahi(browser):
    application.enable(browser, 'avahi')


@when(parsers.parse('I disable the service discovery application'))
def disable_avahi(browser):
    application.disable(browser, 'avahi')


@given(
    parsers.parse('the domain name for {app_name:w} is set to {domain_name:S}')
)
def select_domain_name(browser, app_name, domain_name):
    application.select_domain_name(browser, app_name, domain_name)


@given('the shadowsocks application is configured')
def configure_shadowsocks(browser):
    application.configure_shadowsocks(browser, 'some.shadow.tunnel',
                                      'fakepassword')


@when(
    parsers.parse(
        'I configure shadowsocks with server {server:S} and password {password:w}'
    ))
def configure_shadowsocks_with_details(browser, server, password):
    application.configure_shadowsocks(browser, server, password)


@then(
    parsers.parse(
        'shadowsocks should be configured with server {server:S} and password {password:w}'
    ))
def assert_shadowsocks_configuration(browser, server, password):
    assert (server,
            password) == application.shadowsocks_get_configuration(browser)


@when(
    parsers.parse('I modify the maximum file size of coquelicot to {size:d}'))
def modify_max_file_size(browser, size):
    application.modify_max_file_size(browser, size)


@then(parsers.parse('the maximum file size of coquelicot should be {size:d}'))
def assert_max_file_size(browser, size):
    assert application.get_max_file_size(browser) == size


@when(parsers.parse('I modify the coquelicot upload password to {password:w}'))
def modify_upload_password(browser, password):
    application.modify_upload_password(browser, password)


@given(parsers.parse('share {name:w} is not available'))
def remove_share(browser, name):
    application.remove_share(browser, name)


@when(parsers.parse('I add a share {name:w} from path {path} for {group:w}'))
def add_share(browser, name, path, group):
    application.add_share(browser, name, path, group)


@when(
    parsers.parse(
        'I edit share {old_name:w} to {new_name:w} from path {path} for {group:w}'
    ))
def edit_share(browser, old_name, new_name, path, group):
    application.edit_share(browser, old_name, new_name, path, group)


@when(parsers.parse('I remove share {name:w}'))
def remove_share2(browser, name):
    application.remove_share(browser, name)


@then(
    parsers.parse(
        'the share {name:w} should be listed from path {path} for {group:w}'))
def verify_share(browser, name, path, group):
    application.verify_share(browser, name, path, group)


@then(parsers.parse('the share {name:w} should not be listed'))
def verify_invalid_share(browser, name):
    with pytest.raises(splinter.exceptions.ElementDoesNotExist):
        application.get_share(browser, name)


@then(parsers.parse('the share {name:w} should be accessible'))
def access_share(browser, name):
    application.access_share(browser, name)


@then(parsers.parse('the share {name:w} should not exist'))
def verify_nonexistant_share(browser, name):
    application.verify_nonexistant_share(browser, name)


@then(parsers.parse('the share {name:w} should not be accessible'))
def verify_inaccessible_share(browser, name):
    application.verify_inaccessible_share(browser, name)


@when(parsers.parse('I enable mediawiki public registrations'))
def enable_mediawiki_public_registrations(browser):
    application.enable_mediawiki_public_registrations(browser)


@when(parsers.parse('I disable mediawiki public registrations'))
def disable_mediawiki_public_registrations(browser):
    application.disable_mediawiki_public_registrations(browser)


@when(parsers.parse('I enable mediawiki private mode'))
def enable_mediawiki_private_mode(browser):
    application.enable_mediawiki_private_mode(browser)


@when(parsers.parse('I disable mediawiki private mode'))
def disable_mediawiki_private_mode(browser):
    application.disable_mediawiki_private_mode(browser)


@when(parsers.parse('I set the mediawiki admin password to {password}'))
def set_mediawiki_admin_password(browser, password):
    application.set_mediawiki_admin_password(browser, password)


@when(parsers.parse('I enable message archive management'))
def set_mediawiki_admin_password(browser):
    application.enable_ejabberd_message_archive_management(browser)


@when(parsers.parse('I disable message archive management'))
def set_mediawiki_admin_password(browser):
    application.disable_ejabberd_message_archive_management(browser)


@when('there is an ikiwiki wiki')
def ikiwiki_create_wiki_if_needed(browser):
    application.ikiwiki_create_wiki_if_needed(browser)


@when('I delete the ikiwiki wiki')
def ikiwiki_delete_wiki(browser):
    application.ikiwiki_delete_wiki(browser)


@then('the ikiwiki wiki should be restored')
def ikiwiki_should_exist(browser):
    assert application.ikiwiki_wiki_exists(browser)


@given('I have added a contact to my roster')
def ejabberd_add_contact(browser):
    application.ejabberd_add_contact(browser)


@when('I delete the contact from my roster')
def ejabberd_delete_contact(browser):
    application.ejabberd_delete_contact(browser)


@then('I should have a contact on my roster')
def ejabberd_should_have_contact(browser):
    assert application.ejabberd_has_contact(browser)


@given(parsers.parse('tor relay is {enabled:w}'))
def tor_given_relay_enable(browser, enabled):
    application.tor_feature_enable(browser, 'relay', enabled)


@when(parsers.parse('I {enable:w} tor relay'))
def tor_relay_enable(browser, enable):
    application.tor_feature_enable(browser, 'relay', enable)


@then(parsers.parse('tor relay should be {enabled:w}'))
def tor_assert_relay_enabled(browser, enabled):
    application.tor_assert_feature_enabled(browser, 'relay', enabled)


@then(parsers.parse('tor {port_name:w} port should be displayed'))
def tor_assert_port_displayed(browser, port_name):
    assert port_name in application.tor_get_relay_ports(browser)


@given(parsers.parse('tor bridge relay is {enabled:w}'))
def tor_given_bridge_relay_enable(browser, enabled):
    application.tor_feature_enable(browser, 'bridge-relay', enabled)


@when(parsers.parse('I {enable:w} tor bridge relay'))
def tor_bridge_relay_enable(browser, enable):
    application.tor_feature_enable(browser, 'bridge-relay', enable)


@then(parsers.parse('tor bridge relay should be {enabled:w}'))
def tor_assert_bridge_relay_enabled(browser, enabled):
    application.tor_assert_feature_enabled(browser, 'bridge-relay', enabled)


@given(parsers.parse('tor hidden services are {enabled:w}'))
def tor_given_hidden_services_enable(browser, enabled):
    application.tor_feature_enable(browser, 'hidden-services', enabled)


@when(parsers.parse('I {enable:w} tor hidden services'))
def tor_hidden_services_enable(browser, enable):
    application.tor_feature_enable(browser, 'hidden-services', enable)


@then(parsers.parse('tor hidden services should be {enabled:w}'))
def tor_assert_hidden_services_enabled(browser, enabled):
    application.tor_assert_feature_enabled(browser, 'hidden-services', enabled)


@then(parsers.parse('tor hidden services information should be displayed'))
def tor_assert_hidden_services(browser):
    application.tor_assert_hidden_services(browser)


@given(parsers.parse('download software packages over tor is {enabled:w}'))
def tor_given_download_software_over_tor_enable(browser, enabled):
    application.tor_feature_enable(browser, 'software', enabled)


@when(parsers.parse('I {enable:w} download software packages over tor'))
def tor_download_software_over_tor_enable(browser, enable):
    application.tor_feature_enable(browser, 'software', enable)


@then(
    parsers.parse('download software packages over tor should be {enabled:w}'))
def tor_assert_download_software_over_tor(browser, enabled):
    application.tor_assert_feature_enabled(browser, 'software', enabled)


@then(parsers.parse('{domain:S} should be a tahoe {introducer_type:w} introducer'))
def tahoe_assert_introducer(browser, domain, introducer_type):
    assert application.tahoe_get_introducer(browser, domain, introducer_type)


@then(parsers.parse('{domain:S} should not be a tahoe {introducer_type:w} introducer'))
def tahoe_assert_not_introducer(browser, domain, introducer_type):
    assert not application.tahoe_get_introducer(browser, domain, introducer_type)


@given(parsers.parse('{domain:S} is not a tahoe introducer'))
def tahoe_given_remove_introducer(browser, domain):
    if application.tahoe_get_introducer(browser, domain, 'connected'):
        application.tahoe_remove_introducer(browser, domain)


@when(parsers.parse('I add {domain:S} as a tahoe introducer'))
def tahoe_add_introducer(browser, domain):
    application.tahoe_add_introducer(browser, domain)


@given(parsers.parse('{domain:S} is a tahoe introducer'))
def tahoe_given_add_introducer(browser, domain):
    if not application.tahoe_get_introducer(browser, domain, 'connected'):
        application.tahoe_add_introducer(browser, domain)


@when(parsers.parse('I remove {domain:S} as a tahoe introducer'))
def tahoe_remove_introducer(browser, domain):
    application.tahoe_remove_introducer(browser, domain)
