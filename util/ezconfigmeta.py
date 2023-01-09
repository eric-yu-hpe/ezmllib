from ezmllib.constants import PUBLIC_CONFIG_METADATA_FILE 
from ezmllib.constants import DECODE_FORMAT_UTF

import json, requests
from random import shuffle
import getpass
import yaml
import os, json
import os.path
import logging, sys
import base64
import pam
import subprocess

def encode_parameter(string):
    message_bytes = string.encode('ascii')
    base64_bytes = base64.b64encode(message_bytes)
    base64_message = base64_bytes.decode('ascii')
    return base64_message

def decode(inp):
    base64_message = inp
    base64_bytes = base64_message.encode('ascii')
    message_bytes = base64.b64decode(base64_bytes)
    message = message_bytes.decode('ascii')
    return message

def base64_decode(value, decode_format='utf-8'):
    '''base64 decode'''
    if not value: return # return null for optional secrets
    return base64.b64decode(value).decode(decode_format).strip()

def get_secret_data(secret_type):
    """Get secret key value pairs
    """
    try:
        secret_key_value_pair = {}
        with open(PUBLIC_CONFIG_METADATA_FILE) as f:
            data = json.load(f)
            if secret_type not in data['connections']['secrets']:
                print(f"This application does not have the {secret_type} secret attached.  Contact your Kubernetes Tenant/Project Administrator.")
                return
            for key, val in data['connections']['secrets'][secret_type][-1]['data'].items(): 
                secret_key_value_pair[key] = base64_decode(val)
        return secret_key_value_pair
    except Exception as e:
        print("Failed to fetch secret from configmeta")
        print(e)

def get_secret_data_value(secret_name, secret_key):
    """Get value from secret key
    """
    try:
        with open(PUBLIC_CONFIG_METADATA_FILE) as f:
            data = json.load(f)
            if secret_name not in data['connections']['secrets']:
                print(f"This application does not have the {secret_name} secret attached.  Contact your Kubernetes Tenant/Project Administrator.")
                return
            for key, val in data['connections']['secrets'][secret_name][-1]['data'].items():
                if key == secret_key:
                    return base64_decode(val)
    except Exception as e:
        print("Failed to fetch secret key value from configmeta")
        print(e)

# distro_id = hpecp/mlflow
def get_clusters_based_on_ditro_id(distro_id):
    """Get cluster based on distro id like hpecp/mlflow
    """
    try:
        eligible_cluster_list =[]
        with open(PUBLIC_CONFIG_METADATA_FILE) as f:
            data = json.load(f)
            cluster_list = list(data['connections']['clusters'])
            for cluster in cluster_list:
                if data['connections']['clusters'][cluster]['nodegroups']['1']['distro_id'] == distro_id:
                    eligible_cluster_list.append(cluster)
        f.close()
        return eligible_cluster_list
    except Exception as e:
        print(e)

#service_name = mlflow-server, minio-server
def get_service_endpoint(cluster_name,service_name):
    """Get service url from configmeta file
    """
    try:
        with open(PUBLIC_CONFIG_METADATA_FILE) as f:
            data = json.load(f)
            service_url = list(data['connections']['clusters'][cluster_name]['nodegroups']['1']['roles']['controller']['services'][service_name]['endpoints'])[0]
            return service_url
    except Exception as e:
        print(e)

def get_gateway():
    """Get gateway api from configmeta file
    """
    with open(PUBLIC_CONFIG_METADATA_FILE) as f:
        data = json.load(f)
        if 'kubeconfig' in data['connections']['secrets'] :
            kubeconfigValues = data['connections']['secrets']['kubeconfig']
            for d in kubeconfigValues:
                config = base64.b64decode(d['data']['config']).decode(DECODE_FORMAT_UTF)
                config = yaml.full_load(config)
                gateway = config['users'][0]['user']['exec']['args'][2][:-5]
    return gateway

def get_namespace():
    """Get name space from configmeta file
    """
    current_namespace = None
    with open('/home/guestconfig/configmeta.json') as f:
        data = json.load(f)
    for nodegroup in data['nodegroups']:
        if data['nodegroups'][nodegroup]['roles']['controller']['services']['jupyter-nb']['endpoints']:
            nb_endpoint = data['nodegroups'][nodegroup]['roles']['controller']['services']['jupyter-nb']['endpoints'][0]
            current_namespace = nb_endpoint.split('.')[2]
            break
    if not current_namespace:
        raise ValueError("Tenant namespace is not found")
    return current_namespace

def get_service_name_prefix_from_configmeta():
    """Get service name from configmeta file
    """
    with open(PUBLIC_CONFIG_METADATA_FILE) as f:
        data = json.load(f)
        service_name =  data['cluster']['name']
        service_name_prefix = service_name + '-'
        return service_name_prefix

def print_configmeta():
    with open('/home/guestconfig/configmeta.json') as f:
        parsed = json.load(f)
    print(json.dumps(parsed, indent=4, sort_keys=True))
    

