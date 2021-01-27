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

import base64
from google.cloud import dns
import json
import re
import time

PROJECT_ID='your-project-id'
ZONE='test-zone'
DOMAIN='your.domain.'
TTL=3600

env_folders = { 'folder_id_for_dev': 'dev', 'folder_id_for_prod': 'prod' }
bu_folders = { 'bu2_folder_id': 'bu2', 'bu1_folder_id': 'bu1' }

client = dns.Client(project=PROJECT_ID)
zone = client.zone(ZONE, DOMAIN)

# used when debugging feed events
def justprintdata(event, context):
    if event.get('data'):
        data = base64.b64decode(event['data']).decode('utf-8')
        data = json.loads(data)
        print(data)

def find_by_name(name):
    records = zone.list_resource_record_sets()
    for record in records:
        if name in record.name:
            print('Found existing record:',record.name)
            rs = zone.resource_record_set(record.name, record.record_type, record.ttl, record.rrdatas)
            return(rs)
    return None

def get_env_and_bu(data):
    bu = 'default'
    env = 'default'
    # determine env/bu folder then map to portions of dns name
    for i in data['asset']['ancestors']:
        match = re.search(r"folders\/(.+)", i)
        if match is not None and env_folders.get(match[1]):
            env = env_folders[match[1]]
        if match is not None and bu_folders.get(match[1]):
            bu = bu_folders[match[1]]
    return(bu,env)

def vmToDNS(event, context):
    changes=zone.changes()
    valid_statuses = ['STAGING','DELETED']
    bu = 'default'
    env = 'default'

    if event.get('data'):
        data = base64.b64decode(event['data']).decode('utf-8')
        data = json.loads(data)
        print(data)
        if 'Instance' in data['asset']['assetType']:
            assetType = 'instance'
        elif 'ForwardingRule' in data['asset']['assetType']:
            assetType = 'forwardingrule'

        if 'deleted' in data and data['deleted'] == True:
            status = 'DELETED'
            print(f'Will DELETE record for {assetType}', data['asset']['name'])
            if assetType == 'instance':
                match = re.search(r"/instances\/(.+)", data['asset']['name'])
            elif assetType == 'forwardingrule':
                match = re.search(r"/forwardingRules\/(.+)", data['asset']['name'])
            if match is not None:
                name = match[1]
            if data['priorAsset']['resource']['data'].get('labels'):
                if data['priorAsset']['resource']['data']['labels'].get(
                    'dns-name'):
                    name = data['priorAsset']['resource']['data']['labels']['dns-name']
        elif assetType == 'instance':
            status = data['asset']['resource']['data']['status']
        elif assetType == 'forwardingrule':
            status = 'STAGING' # allow us to process a forwarding rule add

        bu,env = get_env_and_bu(data)

    # set vars for valid statuses
    if 'STAGING' in status:
        print(f'Handling status', status)
        name = data['asset']['resource']['data']['name']
        if data['asset']['resource']['data'].get('labels'):
            if data['asset']['resource']['data']['labels'].get('dns-name'):
                name = data['asset']['resource']['data']['labels']['dns-name']
        if assetType == 'instance':
            ip = data['asset']['resource']['data']['networkInterfaces'][0]['networkIP']
        elif assetType == 'forwardingrule':
            ip = data['asset']['resource']['data']['IPAddress']

    elif 'DELETED' in status:
        pass
    else:
        # all other statuses are not handled
        return(True)

    # check for existing and mark for deletion
    name = f'{name}.{bu}.{env}'
    del_record_set = find_by_name(name)
    if del_record_set is not None:
        print(f'Deleting record for {assetType} {name}')
        changes.delete_record_set(del_record_set)
    elif 'DELETED' in status:
        # skip execution for deleted if no existing records
        status = 'noop'

    # add records for new VMs
    if 'STAGING' in status and name != '' and ip != '':
        print(f'Creating creation record set for {assetType}: {name} with IP {ip}')
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
