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

"""Serializer for system facts models."""

from rest_framework.serializers import (ValidationError,
                                        IntegerField,
                                        CharField,
                                        UUIDField,
                                        DateField,
                                        NullBooleanField)
from api.models import SystemFacts, FactCollection
import api.messages as messages
from api.common.serializer import NotEmptySerializer

from django.utils.translation import ugettext as _


class SystemFactsSerializer(NotEmptySerializer):
    """Serializer for the SystemFacts model."""

    connection_host = CharField(required=False, max_length=256)
    connection_port = IntegerField(required=False, min_value=0)
    connection_uuid = UUIDField(required=True)
    cpu_count = IntegerField(required=False, min_value=0)
    cpu_core_per_socket = IntegerField(required=False, min_value=0)
    cpu_siblings = IntegerField(required=False, min_value=0)
    cpu_hyperthreading = NullBooleanField(required=False)
    cpu_socket_count = IntegerField(required=False, min_value=0)
    cpu_core_count = IntegerField(required=False, min_value=0)
    date_anaconda_log = DateField(required=False)
    date_yum_history = DateField(required=False)
    etc_release_name = CharField(required=True, max_length=64)
    etc_release_version = CharField(required=True, max_length=64)
    etc_release_release = CharField(required=True, max_length=128)
    virt_virt = CharField(required=False, max_length=64)
    virt_type = CharField(required=False, max_length=64)
    virt_num_guests = IntegerField(required=False, min_value=0)
    virt_num_running_guests = IntegerField(required=False, min_value=0)
    virt_what_type = CharField(required=False, max_length=64)

    class Meta:
        """Meta class for SystemFactsSerializer."""

        model = SystemFacts
        exclude = ('id',)


class FactCollectionSerializer(NotEmptySerializer):
    """Serializer for the FactCollection model."""

    facts = SystemFactsSerializer(many=True)

    class Meta:
        """Meta class for FactCollectionSerializer."""

        model = FactCollection
        fields = '__all__'
        qpc_allow_empty_fields = ['facts']

    def create(self, validated_data):
        """Create the fact collection."""
        facts_data = validated_data.pop('facts')
        fact_collection = FactCollection.objects.create(**validated_data)
        for fact_data in facts_data:
            new_fact = SystemFacts.objects.create(**fact_data)
            fact_collection.facts.add(new_fact)
        fact_collection.save()
        return fact_collection

    @staticmethod
    def validate_facts(facts):
        """Make sure the facts list is present."""
        if not facts:
            raise ValidationError(_(messages.VALIDATE_FACTS_MSG))
        return facts
