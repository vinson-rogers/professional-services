# Copyright 2020 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from google.cloud import dns
import time
import re

PROJECT_ID='storied-glazing-255921'
ZONE='test-zone'
DOMAIN='sabre-gcp.com.'
TTL=3600

env_folders = { '659459957450': 'dev', '414067823882': 'prod' }
bu_folders = { '1021170792996': 'shs', '1085585681071': 'shs' }

client = dns.Client(project=PROJECT_ID)
zone = client.zone(ZONE, DOMAIN)

def find_by_name(name):
    records = zone.list_resource_record_sets()
    for record in records:
        if name in record.name:
            print('Found existing record:',record.name)
            rs = zone.resource_record_set(record.name, record.record_type, record.ttl, record.rrdatas)
            return(rs)
    return False

def get_env_and_bu(data):
    bu = 'default'
    env = 'default'
    # determine env/bu folder then map to portions of dns name
    for i in data['asset']['ancestors']:
        #print(i)
        match = re.search(r"folders\/(.+)", i)
        if match is not None and match[1] in env_folders:
            #print(match[1])
            #print(env_folders[match[1]])
            env = env_folders[match[1]]
        if match is not None and match[1] in bu_folders:
            #print(match[1])
            #print(bu_folders[match[1]])
            bu = bu_folders[match[1]]
    return(bu,env)

def vmToDNS(event, context):
    import base64, json
    changes=zone.changes()
    valid_statuses = ['STAGING','DELETED']
    bu = 'default'
    env = 'default'

    if 'data' in event:
        data = base64.b64decode(event['data']).decode('utf-8')
        data = json.loads(data)
        print(data)
        if 'deleted' in data and data['deleted'] == True:
            status = 'DELETED'
            print('Will DELETE',data['asset']['name'])
            match = re.search(r"/instances\/(.+)", data['asset']['name'])
            if match is not None:
                print(match[1])
                name = match[1]
            if 'labels' in data['priorAsset']['resource']['data']:
                if 'dns-name' in data['priorAsset']['resource']['data']['labels']:
                    name = data['priorAsset']['resource']['data']['labels']['dns-name']
        else:
            status = data['asset']['resource']['data']['status']

        bu,env = get_env_and_bu(data)

    # set vars for valid statuses
    if 'STAGING' in status:
        print(f'Handling status', status)
        name = data['asset']['resource']['data']['name']
        if 'labels' in data['asset']['resource']['data']:
            if 'dns-name' in data['asset']['resource']['data']['labels']:
                name = data['asset']['resource']['data']['labels']['dns-name']
        ip = data['asset']['resource']['data']['networkInterfaces'][0]['networkIP']

    elif 'DELETED' in status:
        pass
    else:
        print(f'Status {status} not handled!')
        return(True)

    # check for existing and mark for deletion
    name = f'{name}.{bu}.{env}'
    del_record_set = find_by_name(name)
    if del_record_set is not False:
        print('Deleting existing record for', name)
        changes.delete_record_set(del_record_set)
    # clear status for deleted if we find no records
    elif 'deleted' in data and data['deleted'] == True:
        status = 'noop'

    # add records for new VMs
    if 'STAGING' in status and name != '' and ip != '':
        print(f'Creating creation record set for VM: {name} with IP {ip}')
        hostname = f'{name}.{DOMAIN}'
        add_record_set = zone.resource_record_set(hostname, 'A', TTL, ip)
        changes.add_record_set(add_record_set)

    # execute changes for valid statuses
    if any(x in status for x in valid_statuses):
        changes.create()
        print(changes.status)
        while changes.status != 'done':
            time.sleep(.1)
            changes.reload()
        print('Changes status:', changes.status)
