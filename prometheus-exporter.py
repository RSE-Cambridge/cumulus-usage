#!/bin/python

import json
import time

import openstack
from openstack.config import loader
from prometheus_client.core import GaugeMetricFamily, CounterMetricFamily, REGISTRY
from prometheus_client import start_http_server


def get_usage(cloud, project_id):
    url = "/os-simple-tenant-usage/%s?start=2019-04-01T00:00:00&end=2019-06-26T00:00:00"
    response = cloud.compute.get(url % project_id)
    usages = response.json()['tenant_usage']
    usages['server_usage_count'] = len(usages.get('server_usages', []))
    usages['server_usages'] = None
    del usages['server_usages']
    usages['total_memory_mb_usage'] = int(usages.get('total_memory_mb_usage',0))
    usages['total_vcpus_usage'] = int(usages.get('total_vcpus_usage',0))
    usages['total_iris_vcpus_usage'] = int(usages.get('total_vcpus_usage',0))
    return usages

class CustomCollector(object):
    def __init__(self, cloud):
        self.cloud = cloud

    def collect(self):
        #yield GaugeMetricFamily('my_gauge', 'Help text', value=7)
	
        vcpu = CounterMetricFamily('openstack_vcpu_usage', 'Help text', labels=['project', 'project_uuid'])
        ram_mb = CounterMetricFamily('openstack_ram_mb_usage', 'Help text', labels=['project'])
        instances = CounterMetricFamily('openstack_instances_usage', 'Help text', labels=['project'])

	#total_memory_mb_usage': 22964517.546666667, u'total_vcpus_usage'

	for project in cloud.identity.projects():
            usage = get_usage(cloud, project.id)

            instances.add_metric([project.name], usage['server_usage_count'])
            vcpu.add_metric([project.name, project.id, "vcpu"], usage.get('total_vcpus_usage'))
            ram_mb.add_metric([project.name], usage.get('total_memory_mb_usage'))

        yield vcpu
        yield ram_mb
        yield instances

if __name__ == '__main__':
  # connect to openstack
  cloud = openstack.connect()
  # check connection
  cloud.compute.servers()

  REGISTRY.register(CustomCollector(cloud))

  start_http_server(8000)
  while True: time.sleep(1)

