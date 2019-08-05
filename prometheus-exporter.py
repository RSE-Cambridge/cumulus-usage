#!/bin/python

import json
import time

import openstack
from openstack.config import loader
from prometheus_client.core import GaugeMetricFamily, CounterMetricFamily, REGISTRY
from prometheus_client import start_http_server


def get_usage_for_project(cloud, project, time_period):
    url = "/os-simple-tenant-usage/%s?%s"
    response = cloud.compute.get(url % (project.id, time_period))
    if not response:
        print response
        raise Exception("failed to get usage for %s %s" % (project.name, time_period))
    raw_usage = response.json()['tenant_usage']

    usage = {'project_id': project.id, 'project_name': project.name}
    usage['server_usage_count'] = len(raw_usage.get('server_usages', []))
    usage['total_memory_mb_usage'] = int(raw_usage.get('total_memory_mb_usage',0))
    usage['total_vcpus_usage'] = int(raw_usage.get('total_vcpus_usage',0))
    usage['total_iris_vcpus_usage'] = int(raw_usage.get('total_vcpus_usage',0))
    return usage


def get_usages(cloud, months):
    for project in cloud.identity.projects():
        if project.domain_id != "default":
            continue
        usages = {}
        for month, time_period in months:
            yield month, get_usage_for_project(cloud, project, time_period)

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

        usages = get_usage() # TODO!!!
	for usage in usages:
            project_name = usage['project_name']
            instances.add_metric([project_name], usage['server_usage_count'])
            vcpu.add_metric([project_name, "vcpu"], usage.get('total_vcpus_usage'))
            ram_mb.add_metric([project.name], usage.get('total_memory_mb_usage'))

        yield vcpu
        yield ram_mb
        yield instances

def get_month(month):
    return "start=2019-%02d-01T00:00:00&end=2019-%02d-01T00:00:00" % (month, month + 1)

def get_months():
    months = [
      ("april", get_month(4)),
      ("may", get_month(5)),
      ("june", get_month(6)),
      ("july", get_month(7)),
      ("august", get_month(8)),
    ]
    return months

def get_weeks():
    import datetime
    from dateutil import rrule
    start =  datetime.date(2019, 4, 1)
    end = datetime.datetime.now().date() + datetime.timedelta(days=7)
    weeks = rrule.rrule(rrule.WEEKLY, dtstart=start, until=end)
    previous = None
    for week in weeks:
        if not previous:
            previous = week
            continue
        yield "wb:%s" % previous.strftime("%Y-%m-%d"), "start=%s&end=%s" % (
            previous.strftime("%Y-%m-%dT%H:%M:%S"),
            week.strftime("%Y-%m-%dT%H:%M:%S"))
        previous = week


if __name__ == '__main__':
    cloud = openstack.connect()
    cloud.compute.servers()

    monthly_usages = get_usages(cloud, get_months())
    weekly_usages = get_usages(cloud, list(get_weeks()))
    all_usages = list(monthly_usages) + list(weekly_usages)

    print "project_id, project_name, timeframe, server_usage_count, total_memory_mb_usage, total_vcpus_usage"

    for month, usage in all_usages:
	usage_list = [usage['project_id'], usage['project_name'],
	     month,
	     str(usage['server_usage_count']),
	     str(usage['total_memory_mb_usage']),
	     str(usage['total_vcpus_usage'])]
	print ",".join(usage_list)

    #REGISTRY.register(CustomCollector(cloud))
    #start_http_server(8000)
    #while True: time.sleep(1)
