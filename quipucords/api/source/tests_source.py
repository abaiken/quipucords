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
"""Test the API application."""

import json
from django.test import TestCase
from django.core.urlresolvers import reverse
from rest_framework import status
from api.models import Credential, Source
import api.messages as messages


class SourceTest(TestCase):
    """Test the basic Source infrastructure."""

    def setUp(self):
        """Create test case setup."""
        self.net_cred = Credential.objects.create(
            name='net_cred1',
            cred_type=Credential.NETWORK_CRED_TYPE,
            username='username',
            password='password',
            sudo_password=None,
            ssh_keyfile=None)
        self.net_cred_for_upload = self.net_cred.id
        self.net_cred_for_response = {'id': self.net_cred.id,
                                      'name': self.net_cred.name}

        self.vc_cred = Credential.objects.create(
            name='vc_cred1',
            cred_type=Credential.VCENTER_CRED_TYPE,
            username='username',
            password='password',
            sudo_password=None,
            ssh_keyfile=None)
        self.vc_cred_for_upload = self.vc_cred.id
        self.vc_cred_for_response = {'id': self.vc_cred.id,
                                     'name': self.vc_cred.name}

    def create(self, data):
        """Call the create endpoint."""
        url = reverse('source-list')
        return self.client.post(url,
                                json.dumps(data),
                                'application/json')

    def create_expect_400(self, data):
        """We will do a lot of create tests that expect HTTP 400s."""
        response = self.create(data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def create_expect_201(self, data):
        """Create a source, return the response as a dict."""
        response = self.create(data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        return response.json()

    def test_successful_net_create(self):
        """A valid create request should succeed."""
        data = {'name': 'source1',
                'source_type': Source.NETWORK_SOURCE_TYPE,
                'hosts': ['1.2.3.4'],
                'port': '22',
                'credentials': [self.net_cred_for_upload]}
        response = self.create_expect_201(data)
        self.assertIn('id', response)

    def test_successful_vc_create(self):
        """A valid create request should succeed."""
        data = {'name': 'source1',
                'source_type': Source.VCENTER_SOURCE_TYPE,
                'hosts': ['1.2.3.4'],
                'credentials': [self.vc_cred_for_upload]}
        response = self.create_expect_201(data)
        self.assertIn('id', response)

    def test_double_create(self):
        """A duplicate create should fail."""
        data = {'name': 'source1',
                'source_type': Source.NETWORK_SOURCE_TYPE,
                'hosts': ['1.2.3.4'],
                'port': '22',
                'credentials': [self.net_cred_for_upload]}
        response = self.create_expect_201(data)
        self.assertIn('id', response)
        response = self.create_expect_400(data)

    def test_create_multiple_hosts(self):
        """A valid create request with two hosts."""
        data = {'name': 'source1',
                'source_type': Source.NETWORK_SOURCE_TYPE,
                'hosts': ['1.2.3.4', '1.2.3.5'],
                'port': '22',
                'credentials': [self.net_cred_for_upload]}
        self.create_expect_201(data)

    def test_create_no_name(self):
        """A create request must have a name."""
        self.create_expect_400(
            {'hosts': '1.2.3.4',
             'source_type': Source.NETWORK_SOURCE_TYPE,
             'port': '22',
             'credentials': [self.net_cred_for_upload]})

    def test_create_unprintable_name(self):
        """The Source name must be printable."""
        self.create_expect_400(
            {'name': '\r\n',
             'source_type': Source.NETWORK_SOURCE_TYPE,
             'hosts': '1.2.3.4',
             'port': '22',
             'credentials': [self.net_cred_for_upload]})

    def test_create_no_host(self):
        """A Source needs a host."""
        self.create_expect_400(
            {'name': 'source1',
             'source_type': Source.NETWORK_SOURCE_TYPE,
             'port': '22',
             'credentials': [self.net_cred_for_upload]})

    def test_create_empty_host(self):
        """An empty string is not a host identifier."""
        self.create_expect_400(
            {'name': 'source1',
             'source_type': Source.NETWORK_SOURCE_TYPE,
             'hosts': [],
             'port': '22',
             'credentials': [self.net_cred_for_upload]})

    def test_create_long_name(self):
        """An long source name."""
        self.create_expect_400(
            {'name': 'A' * 100,
             'source_type': Source.NETWORK_SOURCE_TYPE,
             'hosts': ['1.2.3.4'],
             'port': '22',
             'credentials': [self.net_cred_for_upload]})

    def test_create_negative_port(self):
        """An long source name."""
        self.create_expect_400(
            {'name': 'source1',
             'source_type': Source.NETWORK_SOURCE_TYPE,
             'hosts': ['1.2.3.4'],
             'port': -1,
             'credentials': [self.net_cred_for_upload]})

    def test_create_valid_hosts(self):
        """Test valid host patterns."""
        self.create_expect_201(
            {'name': 'source1',
             'source_type': Source.NETWORK_SOURCE_TYPE,
             'hosts': ['10.10.181.9',
                       '10.10.181.9/16',
                       '10.10.128.[1:25]',
                       '10.10.[1:20].25',
                       '10.10.[1:20].[1:25]',
                       'localhost',
                       'mycentos.com',
                       'my-rhel[a:d].company.com',
                       'my-rhel[120:400].company.com'],
             'port': '22',
             'credentials': [self.net_cred_for_upload]})

    def test_create_invalid_hosts(self):
        """Test invalid host patterns."""
        hosts = ['192.1..2',
                 '192.01.5.10',
                 '192.1.5.1/',
                 '192.01.5.[1:10]/10',
                 '192.3.4.455',
                 '192.3.4.455/16',
                 '10.10.[181.9',
                 '10.10.128.[a:25]',
                 '10.10.[1-20].25',
                 '1.1.1.1/33',
                 'my_rhel[a:d].company.com',
                 'my-rhel[a:400].company.com']

        response = self.create(
            {'name': 'source1',
             'source_type': Source.NETWORK_SOURCE_TYPE,
             'hosts': hosts,
             'port': '22',
             'credentials': [self.net_cred_for_upload]})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(len(response.data['hosts']), len(hosts))

    def test_create_bad_host_pattern(self):
        """Test a invalid host pattern."""
        hosts = ['10.1.1.1-10.1.1.254']

        response = self.create(
            {'name': 'source1',
             'source_type': Source.NETWORK_SOURCE_TYPE,
             'hosts': hosts,
             'port': '22',
             'credentials': [self.net_cred_for_upload]})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(len(response.data['hosts']), len(hosts))

    def test_create_bad_port(self):
        """-1 is not a valid ssh port."""
        self.create_expect_400(
            {'name': 'source1',
             'source_type': Source.NETWORK_SOURCE_TYPE,
             'hosts': ['1.2.3.4'],
             'port': '-1',
             'credentials': [self.net_cred_for_upload]})

    def test_create_no_credentials(self):
        """A Source needs credentials."""
        self.create_expect_400(
            {'name': 'source1',
             'source_type': Source.NETWORK_SOURCE_TYPE,
             'hosts': ['1.2.3.4'],
             'port': '22'})

    def test_create_empty_credentials(self):
        """The empty string is not a valid credential list."""
        self.create_expect_400(
            {'name': 'source1',
             'source_type': Source.NETWORK_SOURCE_TYPE,
             'hosts': ['1.2.3.4'],
             'port': '22',
             'credentials': []})

    def test_create_invalid_credentials(self):
        """A random int is not a valid credential."""
        self.create_expect_400(
            {'name': 'source1',
             'source_type': Source.NETWORK_SOURCE_TYPE,
             'hosts': ['1.2.3.4'],
             'port': '22',
             'credentials': [42]})

    def test_create_invalid_cred_type(self):
        """A source type and credential type must be the same."""
        self.create_expect_400(
            {'name': 'source1',
             'source_type': Source.NETWORK_SOURCE_TYPE,
             'hosts': ['1.2.3.4'],
             'port': '22',
             'credentials': [self.vc_cred_for_upload]})

    def test_create_too_many_creds(self):
        """A vcenter source and have one credential."""
        self.create_expect_400(
            {'name': 'source1',
             'source_type': Source.VCENTER_SOURCE_TYPE,
             'hosts': ['1.2.3.4'],
             'credentials': [self.vc_cred_for_upload,
                             self.net_cred_for_upload]})

    def test_create_req_host(self):
        """A vcenter source must have an host."""
        self.create_expect_400(
            {'name': 'source1',
             'source_type': Source.VCENTER_SOURCE_TYPE,
             'credentials': [self.vc_cred_for_upload]})

    def test_create_vc_with_hosts(self):
        """A vcenter source cannot have a host."""
        self.create_expect_400(
            {'name': 'source1',
             'source_type': Source.VCENTER_SOURCE_TYPE,
             'hosts': ['1.2.3.4', '1.2.3.5'],
             'credentials': [self.vc_cred_for_upload]})

    def test_create_req_type(self):
        """A vcenter source must have an type."""
        self.create_expect_400(
            {'name': 'source1',
             'hosts': ['1.2.3.4'],
             'credentials': [self.vc_cred_for_upload]})

    def test_list(self):
        """List all Source objects."""
        data = {'name': 'source',
                'source_type': Source.NETWORK_SOURCE_TYPE,
                'port': '22',
                'hosts': ['1.2.3.4'],
                'credentials': [self.net_cred_for_upload]}
        for i in range(3):
            this_data = data.copy()
            this_data['name'] = 'source' + str(i)
            self.create_expect_201(this_data)

        url = reverse('source-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        content = response.json()
        expected = [{'id': 1, 'name': 'source0',
                     'source_type': Source.NETWORK_SOURCE_TYPE,
                     'port': 22,
                     'hosts': ['1.2.3.4'], 'credentials':
                     [self.net_cred_for_response]},
                    {'id': 2, 'name': 'source1',
                     'source_type': Source.NETWORK_SOURCE_TYPE,
                     'port': 22,
                     'hosts': ['1.2.3.4'], 'credentials':
                     [self.net_cred_for_response]},
                    {'id': 3, 'name': 'source2',
                     'source_type': Source.NETWORK_SOURCE_TYPE,
                     'port': 22,
                     'hosts': ['1.2.3.4'], 'credentials':
                     [self.net_cred_for_response]}]
        self.assertEqual(content, expected)

    def test_filter_by_type_list(self):
        """List all Source objects filtered by type."""
        data = {'name': 'nsource',
                'source_type': Source.NETWORK_SOURCE_TYPE,
                'port': '22',
                'credentials': [self.net_cred_for_upload],
                'hosts': ['1.2.3.4']}
        for i in range(1, 3):
            this_data = data.copy()
            this_data['name'] = 'nsource' + str(i)
            self.create_expect_201(this_data)

        data = {'name': 'vsource',
                'source_type': Source.VCENTER_SOURCE_TYPE,
                'credentials': [self.vc_cred_for_upload],
                'hosts': ['1.2.3.4']}

        for i in range(3, 5):
            this_data = data.copy()
            this_data['name'] = 'vsource' + str(i)
            self.create_expect_201(this_data)

        url = reverse('source-list')
        response = self.client.get(
            url, {'source_type': Source.VCENTER_SOURCE_TYPE})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_json = response.json()
        print(response_json)

        content = response.json()
        expected = [
            {
                'id': 3, 'name':
                'vsource3', 'source_type':
                'vcenter', 'port': 443,
                'credentials': [{'id': 2, 'name': 'vc_cred1'}],
                'hosts': ['1.2.3.4'],
            },
            {
                'id': 4,
                'name': 'vsource4',
                'source_type': 'vcenter', 'port': 443,
                'credentials': [{'id': 2, 'name': 'vc_cred1'}],
                'hosts': ['1.2.3.4'],
            }
        ]

        self.assertEqual(content, expected)

    def test_retrieve(self):
        """Get details on a specific Source by primary key."""
        initial = self.create_expect_201({
            'name': 'source1',
            'source_type': Source.NETWORK_SOURCE_TYPE,
            'hosts': ['1.2.3.4'],
            'port': '22',
            'credentials': [self.net_cred_for_upload]})

        url = reverse('source-detail', args=(initial['id'],))
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('credentials', response.json())
        creds = response.json()['credentials']

        self.assertEqual(creds, [self.net_cred_for_response])

    # We don't have to test that update validates fields correctly
    # because the validation code is shared between create and update.
    def test_update(self):
        """Completely update a Source."""
        initial = self.create_expect_201({
            'name': 'source2',
            'source_type': Source.NETWORK_SOURCE_TYPE,
            'hosts': ['1.2.3.4'],
            'port': '22',
            'credentials': [self.net_cred_for_upload]})

        data = {'name': 'source2',
                'hosts': ['1.2.3.5'],
                'port': 23,
                'credentials': [self.net_cred.id]}
        url = reverse('source-detail', args=(initial['id'],))
        response = self.client.put(url,
                                   json.dumps(data),
                                   content_type='application/json',
                                   format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        expected = {'name': 'source2',
                    'source_type': Source.NETWORK_SOURCE_TYPE,
                    'hosts': ['1.2.3.5'],
                    'port': 23,
                    'credentials': [self.net_cred_for_response]}
        # data should be a strict subset of the response, because the
        # response adds an id field.
        for key, value in expected.items():  # pylint: disable=unused-variable
            self.assertEqual(expected[key], response.json()[key])

    def test_update_collide(self):
        """Fail update due to name conflict."""
        self.create_expect_201({
            'name': 'source2-double',
            'source_type': Source.NETWORK_SOURCE_TYPE,
            'hosts': ['1.2.3.4'],
            'port': '22',
            'credentials': [self.net_cred_for_upload]})

        initial = self.create_expect_201({
            'name': 'source2',
            'source_type': Source.NETWORK_SOURCE_TYPE,
            'hosts': ['1.2.3.4'],
            'port': '22',
            'credentials': [self.net_cred_for_upload]})

        data = {'name': 'source2-double',
                'hosts': ['1.2.3.5'],
                'port': 23,
                'credentials': [self.net_cred.id]}
        url = reverse('source-detail', args=(initial['id'],))
        response = self.client.put(url,
                                   json.dumps(data),
                                   content_type='application/json',
                                   format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_empty_hosts(self):
        """Fail update due to empty host array."""
        initial = self.create_expect_201({
            'name': 'source',
            'source_type': Source.NETWORK_SOURCE_TYPE,
            'hosts': ['1.2.3.4'],
            'port': '22',
            'credentials': [self.net_cred_for_upload]})

        data = {'name': 'source',
                'hosts': [],
                'port': 22,
                'credentials': [self.net_cred_for_upload]}
        url = reverse('source-detail', args=(initial['id'],))
        response = self.client.put(url,
                                   json.dumps(data),
                                   content_type='application/json',
                                   format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        json_rsp = response.json()
        print(json_rsp)
        self.assertEqual(json_rsp['hosts'][0],
                         messages.SOURCE_HOSTS_CANNOT_BE_EMPTY)

    def test_update_type_passed(self):
        """Fail update due to type passed."""
        initial = self.create_expect_201({
            'name': 'source2',
            'source_type': Source.NETWORK_SOURCE_TYPE,
            'hosts': ['1.2.3.4'],
            'port': '22',
            'credentials': [self.net_cred_for_upload]})

        data = {'name': 'source3',
                'source_type': Source.NETWORK_SOURCE_TYPE,
                'hosts': ['1.2.3.5'],
                'port': 23,
                'credentials': [self.net_cred.id]}
        url = reverse('source-detail', args=(initial['id'],))
        response = self.client.put(url,
                                   json.dumps(data),
                                   content_type='application/json',
                                   format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_bad_cred_type(self):
        """Fail update due to bad cred type."""
        initial = self.create_expect_201({
            'name': 'source2',
            'source_type': Source.NETWORK_SOURCE_TYPE,
            'hosts': ['1.2.3.4'],
            'port': '22',
            'credentials': [self.net_cred_for_upload]})

        data = {'name': 'source3',
                'source_type': Source.NETWORK_SOURCE_TYPE,
                'hosts': ['1.2.3.5'],
                'port': 23,
                'credentials': [self.vc_cred.id]}
        url = reverse('source-detail', args=(initial['id'],))
        response = self.client.put(url,
                                   json.dumps(data),
                                   content_type='application/json',
                                   format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_partial_update(self):
        """Partially update a Source."""
        initial = self.create_expect_201({
            'name': 'source3',
            'source_type': Source.NETWORK_SOURCE_TYPE,
            'hosts': ['1.2.3.4'],
            'port': '22',
            'credentials': [self.net_cred_for_upload]})

        data = {'name': 'source3-new',
                'hosts': ['1.2.3.5']}
        url = reverse('source-detail', args=(initial['id'],))
        response = self.client.patch(url,
                                     json.dumps(data),
                                     content_type='application/json',
                                     format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['name'], 'source3-new')
        self.assertEqual(response.json()['hosts'], ['1.2.3.5'])

    def test_delete(self):
        """Delete a Source."""
        data = {'name': 'source3',
                'source_type': Source.NETWORK_SOURCE_TYPE,
                'hosts': ['1.2.3.4'],
                'port': '22',
                'credentials': [self.net_cred_for_upload]}
        response = self.create_expect_201(data)

        url = reverse('source-detail', args=(response['id'],))
        response = self.client.delete(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
