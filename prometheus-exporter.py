#!/bin/python

import json
import time

import openstack
from openstack.config import loader
from prometheus_client.core import GaugeMetricFamily, CounterMetricFamily, REGISTRY
from prometheus_client import start_http_server


def get_usage_for_project(cloud, project):
    q2 = "start=2019-04-01T00:00:00&end=2019-07-01T00:00:00"
    url = "/os-simple-tenant-usage/%s?%s"
    response = cloud.compute.get(url % (project.id, q2))
    raw_usage = response.json()['tenant_usage']

    usage = {'project_id': project.id, 'project_name': project.name}
    usage['server_usage_count'] = len(raw_usage.get('server_usages', []))
    usage['total_memory_mb_usage'] = int(raw_usage.get('total_memory_mb_usage',0))
    usage['total_vcpus_usage'] = int(raw_usage.get('total_vcpus_usage',0))
    usage['total_iris_vcpus_usage'] = int(raw_usage.get('total_vcpus_usage',0))
    return usage


def get_usage(cloud):
    for project in cloud.identity.projects():
        yield get_usage_for_project(cloud, project)


class CustomCollector(object):
    def __init__(self, cloud):
        self.cloud = cloud

    def collect(self):
        #yield GaugeMetricFamily('my_gauge', 'Help text', value=7)
	
        vcpu = CounterMetricFamily('openstack_vcpu_usage',
                'Help text', labels=['project'])
        ram_mb = CounterMetricFamily('openstack_ram_mb_usage',
                'Help text', labels=['project'])
        instances = CounterMetricFamily('openstack_instances_usage',
                'Help text', labels=['project'])

        usages = get_usage()
	for usage in usages:
            project_name = usage['project_name']
            instances.add_metric([project_name], usage['server_usage_count'])
            vcpu.add_metric([project_name, "vcpu"], usage.get('total_vcpus_usage'))
            ram_mb.add_metric([project.name], usage.get('total_memory_mb_usage'))

        yield vcpu
        yield ram_mb
        yield instances

if __name__ == '__main__':
    cloud = openstack.connect()
    cloud.compute.servers()

    print "project_id, project_name, server_usage_count, total_memory_mb_usage, total_vcpus_usage"
    usages = get_usage(cloud)
    for usage in usages:
        usage_list = [usage['project_id'], usage['project_name'],
                      str(usage['server_usage_count']),
                      str(usage['total_memory_mb_usage']),
                      str(usage['total_vcpus_usage'])]
        print ",".join(usage_list)

    print list(get_usage(cloud))

    #REGISTRY.register(CustomCollector(cloud))
    #start_http_server(8000)
    #while True: time.sleep(1)
