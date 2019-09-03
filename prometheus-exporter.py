#!/bin/python

import calendar
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
    projects = list(cloud.identity.projects())
    projects.sort(key = lambda project: project.name)
    for project in projects:
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

def get_month(year, month):
    month_int = month_to_int[month]
    return "start=%s-%02d-01T00:00:00&end=%s-%02d-01T00:00:00" % (year, month_int, year, month_int + 1)

month_to_int = {month.lower(): i for i,month in enumerate(calendar.month_name) if month != ""}
month_days = {month: calendar.monthrange(2019, i)[1] for month, i in month_to_int.items()}

def get_months():
    months_raw = [
	(2019, "april"),
	(2019, "may"),
	(2019, "june"),
	(2019, "july"),
	(2019, "august"),
	(2019, "september"),
    ]
    return [(month, get_month(year, month)) for year, month in months_raw]

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

    #monthly_usages = get_usages(cloud, get_months())
    #weekly_usages = get_usages(cloud, list(get_weeks()))
    #all_usages = list(monthly_usages) + list(weekly_usages)
    all_usages = get_usages(cloud, get_months())

    print ("project_name, timeframe, "
           "average physical cores, physical core hours, average physical hypervisors, average vcpus, "
           "active vm count, vm memory usage hours, vm core usage hours, project_id")

    for month, usage in all_usages:
	days = month_days.get(month, 7)
        hours = 24 * days

	vcpu_hours = float(usage['total_vcpus_usage'])
	average_vcpus = vcpu_hours / hours

        hypervisor_hours = vcpu_hours / 56.0  # 56 vCPU per hypervisor
        average_hypervisors = hypervisor_hours / hours

        physical_core_hours = hypervisor_hours * 32  # 32 physical_cores in a hypervisor
        #adjusted_core_hours = physical_core_hours * 1.171875
        average_physical_cores = physical_core_hours / hours

	usage_list = [
             usage['project_name'],
	     month.strip("wb:"),
             str(average_physical_cores),
             str(physical_core_hours),
             str(average_hypervisors),
             str(average_vcpus),
	     str(usage['server_usage_count']),
	     str(usage['total_memory_mb_usage']),
	     str(usage['total_vcpus_usage']),
             usage['project_id'],
	]
	print ",".join(usage_list)

    #REGISTRY.register(CustomCollector(cloud))
    #start_http_server(8000)
    #while True: time.sleep(1)
