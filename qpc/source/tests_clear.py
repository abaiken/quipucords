#
# Copyright (c) 2017 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 3 (GPLv3). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv3
# along with this software; if not, see
# https://www.gnu.org/licenses/gpl-3.0.txt.
#
"""Test the CLI module."""

import unittest
import sys
from io import StringIO
from argparse import ArgumentParser, Namespace
import requests
import requests_mock
from qpc.tests_utilities import HushUpStderr, redirect_stdout
from qpc.request import CONNECTION_ERROR_MSG, SSL_ERROR_MSG
from qpc.source import SOURCE_URI
from qpc.source.clear import SourceClearCommand
from qpc.utils import get_server_location, write_server_config

PARSER = ArgumentParser()
SUBPARSER = PARSER.add_subparsers(dest='subcommand')

write_server_config({'host': '127.0.0.1', 'port': 8000})
BASE_URL = get_server_location()


class SourceClearCliTests(unittest.TestCase):
    """Class for testing the source clear commands for qpc."""

    def setUp(self):
        """Create test setup."""
        # Temporarily disable stderr for these tests, CLI errors clutter up
        # nosetests command.
        self.orig_stderr = sys.stderr
        sys.stderr = HushUpStderr()

    def tearDown(self):
        """Remove test setup."""
        # Restore stderr
        sys.stderr = self.orig_stderr

    def test_clear_source_ssl_err(self):
        """Testing the clear source command with a connection error."""
        source_out = StringIO()
        url = BASE_URL + SOURCE_URI + '?name=source1'
        with requests_mock.Mocker() as mocker:
            mocker.get(url, exc=requests.exceptions.SSLError)
            ncc = SourceClearCommand(SUBPARSER)
            args = Namespace(name='source1')
            with self.assertRaises(SystemExit):
                with redirect_stdout(source_out):
                    ncc.main(args)
                    self.assertEqual(source_out.getvalue(), SSL_ERROR_MSG)

    def test_clear_source_conn_err(self):
        """Testing the clear source command with a connection error."""
        source_out = StringIO()
        url = BASE_URL + SOURCE_URI + '?name=source1'
        with requests_mock.Mocker() as mocker:
            mocker.get(url, exc=requests.exceptions.ConnectTimeout)
            ncc = SourceClearCommand(SUBPARSER)
            args = Namespace(name='source1')
            with self.assertRaises(SystemExit):
                with redirect_stdout(source_out):
                    ncc.main(args)
                    self.assertEqual(source_out.getvalue(),
                                     CONNECTION_ERROR_MSG)

    def test_clear_source_internal_err(self):
        """Testing the clear source command with an internal error."""
        source_out = StringIO()
        url = BASE_URL + SOURCE_URI + '?name=source1'
        with requests_mock.Mocker() as mocker:
            mocker.get(url, status_code=500, json={'error': ['Server Error']})
            ncc = SourceClearCommand(SUBPARSER)
            args = Namespace(name='source1')
            with self.assertRaises(SystemExit):
                with redirect_stdout(source_out):
                    ncc.main(args)
                    self.assertEqual(source_out.getvalue(), 'Server Error')

    def test_clear_source_empty(self):
        """Testing the clear source command successfully with empty data."""
        source_out = StringIO()
        url = BASE_URL + SOURCE_URI + '?name=source1'
        with requests_mock.Mocker() as mocker:
            mocker.get(url, status_code=200, json=[])
            ncc = SourceClearCommand(SUBPARSER)
            args = Namespace(name='source1')
            with self.assertRaises(SystemExit):
                with redirect_stdout(source_out):
                    ncc.main(args)
                    self.assertEqual(source_out.getvalue(),
                                     'Source "source1" was not found\n')

    def test_clear_by_name(self):
        """Testing the clear source command.

        Successfully with stubbed data when specifying a name
        """
        source_out = StringIO()
        get_url = BASE_URL + SOURCE_URI + '?name=source1'
        delete_url = BASE_URL + SOURCE_URI + '1/'
        source_entry = {'id': 1, 'name': 'source1', 'hosts': ['1.2.3.4'],
                        'credential': ['credential1', 'cred2'], 'port': 22}
        data = [source_entry]
        with requests_mock.Mocker() as mocker:
            mocker.get(get_url, status_code=200, json=data)
            mocker.delete(delete_url, status_code=204)
            ncc = SourceClearCommand(SUBPARSER)
            args = Namespace(name='source1')
            with redirect_stdout(source_out):
                ncc.main(args)
                expected = 'Source "source1" was removed\n'
                self.assertEqual(source_out.getvalue(), expected)

    def test_clear_by_name_err(self):
        """Test the clear source command successfully.

        With stubbed data when specifying a name with an error response
        """
        source_out = StringIO()
        get_url = BASE_URL + SOURCE_URI + '?name=source1'
        delete_url = BASE_URL + SOURCE_URI + '1/'
        source_entry = {'id': 1, 'name': 'source1', 'hosts': ['1.2.3.4'],
                        'credential': ['credential1', 'cred2'], 'port': 22}
        data = [source_entry]
        err_data = {'error': ['Server Error']}
        with requests_mock.Mocker() as mocker:
            mocker.get(get_url, status_code=200, json=data)
            mocker.delete(delete_url, status_code=500, json=err_data)
            ncc = SourceClearCommand(SUBPARSER)
            args = Namespace(name='source1')
            with self.assertRaises(SystemExit):
                with redirect_stdout(source_out):
                    ncc.main(args)
                    expected = 'Failed to remove source "source1"'
                    self.assertTrue(expected in source_out.getvalue())

    def test_clear_all_empty(self):
        """Test the clear source command successfully.

        With stubbed data empty list of sources
        """
        source_out = StringIO()
        get_url = BASE_URL + SOURCE_URI
        with requests_mock.Mocker() as mocker:
            mocker.get(get_url, status_code=200, json=[])
            ncc = SourceClearCommand(SUBPARSER)
            args = Namespace(name=None)
            with self.assertRaises(SystemExit):
                with redirect_stdout(source_out):
                    ncc.main(args)
                    expected = 'No sources exist to be removed\n'
                    self.assertEqual(source_out.getvalue(), expected)

    def test_clear_all_with_error(self):
        """Testing the clear source command successfully.

        With stubbed data list of sources with delete error
        """
        source_out = StringIO()
        get_url = BASE_URL + SOURCE_URI
        delete_url = BASE_URL + SOURCE_URI + '1/'
        source_entry = {'id': 1, 'name': 'source1', 'hosts': ['1.2.3.4'],
                        'credential': ['credential1', 'cred2'], 'port': 22}
        data = [source_entry]
        err_data = {'error': ['Server Error']}
        with requests_mock.Mocker() as mocker:
            mocker.get(get_url, status_code=200, json=data)
            mocker.delete(delete_url, status_code=500, json=err_data)
            ncc = SourceClearCommand(SUBPARSER)
            args = Namespace(name=None)
            with self.assertRaises(SystemExit):
                with redirect_stdout(source_out):
                    ncc.main(args)
                    expected = 'Some sources were removed, however and' \
                               ' error occurred removing the following' \
                               ' credentials:'
                    self.assertTrue(expected in source_out.getvalue())

    def test_clear_all(self):
        """Testing the clear source command successfully with stubbed data."""
        source_out = StringIO()
        get_url = BASE_URL + SOURCE_URI
        delete_url = BASE_URL + SOURCE_URI + '1/'
        source_entry = {'id': 1, 'name': 'source1', 'hosts': ['1.2.3.4'],
                        'credential': ['credential1', 'cred2'], 'port': 22}
        data = [source_entry]
        with requests_mock.Mocker() as mocker:
            mocker.get(get_url, status_code=200, json=data)
            mocker.delete(delete_url, status_code=204)
            ncc = SourceClearCommand(SUBPARSER)
            args = Namespace(name=None)
            with redirect_stdout(source_out):
                ncc.main(args)
                expected = 'All sources were removed\n'
                self.assertEqual(source_out.getvalue(), expected)
