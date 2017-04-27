#    Copyright 2013, Big Switch Networks, Inc.
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

from django.core.urlresolvers import reverse
from django.core.urlresolvers import reverse_lazy
from django.utils.translation import ugettext_lazy as _
from django.conf import settings

from horizon import exceptions
from horizon import forms
from horizon import tabs
from horizon.utils import memoized
from horizon import workflows

from openstack_dashboard import api
from openstack_dashboard.dashboards.monitor.monitor \
    import forms as m_forms


class IndexView(forms.ModalFormView):
    form_class = m_forms.VmmonitorLoginForm
    template_name = 'monitor/monitor/index.html'
    page_title = _("Monitor")

    def get_context_data(self, **kwargs):
        context = super(IndexView, self).get_context_data(**kwargs)
        vmmonitor_url = getattr(settings, 'VMMONITOR_URL', '')
        vmmonitor_username = getattr(settings, 'VMMONITOR_USERNAME', '')
        vmmonitor_password = getattr(settings, 'VMMONITOR_PASSWORD', '')
        context.update({'vmmonitor_url': vmmonitor_url,
                        'username': vmmonitor_username,
                        'password': vmmonitor_password})
        return context


