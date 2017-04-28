# Copyright 2013 Kylin OS, Inc
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import json
import traceback

from django.core.urlresolvers import reverse
from django.utils.translation import ugettext_lazy as _
from django.utils.translation import ugettext

from horizon import exceptions
from horizon import forms
from horizon import messages

from openstack_dashboard import api
from openstack_dashboard.dashboards.project.instances \
    import tables as project_tables


class LiveMigrateForm(forms.SelfHandlingForm):
    multi_instances = forms.CharField(widget=forms.HiddenInput, required=False)
    current_host = forms.CharField(label=_("Current Host"),
                                   required=False,
                                   widget=forms.TextInput(
                                       attrs={'readonly': 'readonly'}))
    host = forms.ThemableChoiceField(
        label=_("New Host"),
        help_text=_("Choose a Host to migrate to."),
        required=False)
    disk_over_commit = forms.BooleanField(label=_("Disk Over Commit"),
                                          initial=False, required=False)
    block_migration = forms.BooleanField(label=_("Block Migration"),
                                         initial=False, required=False)

    def __init__(self, request, *args, **kwargs):
        super(LiveMigrateForm, self).__init__(request, *args, **kwargs)
        initial = kwargs.get('initial', {})
        instance_id = initial.get('instance_id')
        if instance_id == 'MULTIPLE':
            self.fields['current_host'] = forms.CharField(widget=forms.HiddenInput, required=False)
        self.fields['instance_id'] = forms.CharField(widget=forms.HiddenInput,
                                                     initial=instance_id)
        self.fields['host'].choices = self.populate_host_choices(request,
                                                                 initial)

    def populate_host_choices(self, request, initial):
        hosts = initial.get('hosts')
        current_host = initial.get('current_host')
        host_list = [(host.host_name,
                      host.host_name)
                     for host in hosts
                     if (host.service.startswith('compute') and
                         host.host_name != current_host)]
        if host_list:
            host_list.insert(0, ("", _("Automatically schedule new host.")))
        else:
            host_list.insert(0, ("", _("No other hosts available")))
        return sorted(host_list)

    def _get_all_instances(self):
        (all_instances_list, _more) = api.nova.server_list(self.request, all_tenants=True)
        all_instances = {}
        for i in all_instances_list:
            all_instances[i.id] = i
        return all_instances

    def handle(self, request, data):
        try:
            block_migration = data['block_migration']
            disk_over_commit = data['disk_over_commit']
            host = None if not data['host'] else data['host']
            instance_id_arr = []
            if data['instance_id'] == 'MULTIPLE':
                instance_id_arr = data['multi_instances'].split(',')
                all_instances = self._get_all_instances()
            else:
                instance_id_arr.append(data['instance_id'])
            same_host = []
            deleting = []
            not_active = []
            for instance_id in instance_id_arr:
                if data['instance_id'] == 'MULTIPLE':
                    instance = all_instances.get(instance_id)
                    if getattr(instance, 'OS-EXT-SRV-ATTR:host', '')  == host:
                        same_host.append(instance.name)
                        continue
                    elif project_tables.is_deleting(instance):
                        deleting.append(instance.name)
                        continue
                    elif instance.status not in project_tables.ACTIVE_STATES:
                        not_active.append(instance.name)
                        continue
                api.nova.server_live_migrate(request,
                                             instance_id,
                                             host,
                                             block_migration=block_migration,
                                             disk_over_commit=disk_over_commit)
            if same_host or deleting or not_active:
                msg = ''
                if same_host:
                    msg = msg + ugettext('Instances %s has been at this host, do not need to migrate.') % ', '.join(same_host)
                if deleting:
                    msg = msg + ugettext('Instances %s are deleting, not allowed to migrate.') % ', '.join(deleting)
                if not_active:
                    msg = msg + ugettext('Instances %s are not active, not allowed to migrate.') % ', '.join(not_active)
                messages.warning(request, msg)
            else:
                msg = _('The instance is preparing the live migration '
                        'to a new host.')
                messages.info(request, msg)
            return True
        except Exception:
            msg = _('Failed to live migrate instance to '
                    'host "%s".') % data['host']
            redirect = reverse('horizon:admin:instances:index')
            exceptions.handle(request, msg, redirect=redirect)
