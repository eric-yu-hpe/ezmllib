import json
import requests
import getpass
from pwd import getpwnam
import os
import shutil
import yaml
from ezmllib.util.ezcli import check_output
from ezmllib.util.ezrequest import get_service_prefix
from ezmllib.util.ezconfigmeta import decode
from ezmllib.constants import KDAPP_CONDITION_DEPLOYMENT, KDAPP_CONDITION_TRAINING, KDAPP_CONDITION_NOTEBOOK, KDAPP_CONDITION_OTHERS

def get_svc_annotation_dict(service_name):
    """
       Get service annotations
       output : key: service, value: dictionary of annotations
       input : service name
    """
    services = []
    annotations = {}
    KUBECTL_CMD = f"kubectl get svc | grep '^{service_name}' "
    lines = check_output(KUBECTL_CMD, error_message=f"Failed to get the services with names starting with '{service_name}'. Please make sure they are available by checking with your system administrator.")
    for line in lines.split("\n"):
        services.append(line.split(" ")[0])
    if not services:
        print(f"Service not found with given prefix {service_name}")
        return
    for service in services:
        KUBECTL_CMD_SVC = f"kubectl get -o json svc {service}"
        service_yaml = check_output(KUBECTL_CMD_SVC)
        service_yaml_json = json.loads(service_yaml)
        if service_yaml_json['metadata'].get('annotations'):
            annotations[service] = dict(service_yaml_json['metadata']['annotations'])
    return annotations

def get_svc_annotation_value(service_name, key):
    """
       Get a specific service annotation value from a key, e.g., annotations = {"livy":{<gateway>:<endpoint>}, get the <endpoint> from the <gateway>
       output : the value of specific annotation
       input : service name and annotation name
    """
    annotations = get_svc_annotation_dict(service_name)
    for service, maps in annotations.items():
        for k, v in maps.items():
            if k == key:
                return v 

def get_kdcluster_state(kdcluster_name):
    """
       This function is to get status of kd cluster.
       output : State of kd cluster like Configured, Creating.
       input : Name of kd cluster
    """
    KUBECTL_CMD = f"kubectl get kdcluster {kdcluster_name} -o json"
    kdcluster_details = check_output(KUBECTL_CMD, error_message="Could not find the kdcluster, please make sure kubeconfig is set and kdluster name is correct")
    kdcluster_details_json = json.loads(kdcluster_details)
    kdcluster_state = kdcluster_details_json['status']['state']
    return kdcluster_details_json['status']['state']

def get_service_names(kdapp="jupyter-notebook"):
    """
    Get the service names filtered by of kdapp
    args:
      kdapp:: {"jupyter-notebook", "deployment-engine", "training-engine"}
    Example:
      get_service_names(kdapp="deployment-engine")
    """
    if kdapp == "deployment-engine":
        condition = KDAPP_CONDITION_DEPLOYMENT
    elif kdapp == "training-engine":
        condition = KDAPP_CONDITION_TRAINING
    elif kdapp == "jupyter-notebook":
        condition = KDAPP_CONDITION_NOTEBOOK
    else:
        condition = KDAPP_CONDITION_OTHERS
    lines = check_output(f"kubectl get pod --show-labels | grep kdapp={kdapp} | grep {condition}")
    lines = lines.split("\n") # split according to new lines
    podnames = [line.split(" ")[0] for line in lines] # extract pod name
    services = [podname.split(condition)[0][:-1] for podname in podnames]
    print(f"Available {kdapp} services are: {services}")
    return services

def get_service_endpoints(service, service_name="", port='', verbose=True):
    '''
    Print the available endpoints related to the service
    args:
      service:: str:: name of the service
      service_name:: str:: the service_name you want to show on printout
      verbose:: boolean:: mute printout for functionize testing if False

    Example:
      get_service_endpoints("livy-http", "Livy")

    '''
    ep = []
    annotations = get_svc_annotation_dict(service) # ex., {"livy-srv": {hpecp-internal-gateway/8998: mip-bd-vm232.mip.storage.hpecorp.net:10032}, "livy-blabla: {hpecp-internal-gateway/8998: mip-bd-vm232.mip.storage.hpecorp.net:10033}}
    if not annotations:
        raise RuntimeError(f"No services with previx {service} found!")
    for service, endpoint_map in annotations.items():
        cond = 1 # if any endpoint is available, then print the statement the first time
        for gateway, endpoint in endpoint_map.items():
            if gateway.startswith('hpecp-internal-gateway'):
                if verbose and cond:
                    print(f"Available {service_name} endpoints for {service}: ")
                    cond = 0
                prefix = get_service_prefix(endpoint)
                print(f"{prefix}://{endpoint}") # ex., https://mip-bd-vm232.mip.storage.hpecorp.net:10032   
                if gateway.endswith(str(port)):
                    ep.append(f"{prefix}://{endpoint}")
    return ep

def get_secret_data_by_name(secret_name):
    """
    Unpack and decodes secret data into key/value pairs
    args:
        secret_name: String containing exact name of secret
    output:
        dict:  key / value pairs of secret data base64 decoded
    """
    error_message=f"secret {secret_name} not found!"
    secret = json.loads(check_output(f"kubectl get secret {secret_name} -o json", error_message=error_message))
    decoded_secret = {k: decode(v).strip() for k,v in secret['data'].items()} if secret['data'] else None
    return decoded_secret

def get_secret_data_by_name_and_key(secret_name, key):
    """
    Decode secret data and select specifc value by key
    args:
        secret_name: String containing exact name of secret
        key: String containing data key
    output:
        String: decoded value corresponding to provided key from secret data
    """
    error_message=f"secret {secret_name} not found!"
    secret = json.loads(check_output(f"kubectl get secret {secret_name} -o json", error_message=error_message))
    return decode(secret['data'][key]) if secret['data'] else None

def get_gateway(kubeconfig_secret_name):
    """
    returns gateway config given kubeconfig secret 
    args:
        kubeconfig_secret_name: full name of the kc secret
    """
    config = get_secret_data_by_name_and_key(kubeconfig_secret_name, "config")
    config = yaml.full_load(config)
    return config['users'][0]['user']['exec']['args'][2][:-5]

def get_clusters_by_app(app_name,namespace=None):
    """
    Returns list of kdcluster names with spec.app matching app_name
    args:
        app_name: String containing application name
        namespace (Optional): namespace to look for kdclusters in. Default: tenant namespace
    output:
        List: List of Strings containing cluster names with matching app 
    """
    # example app names: mlflow, training-engine, jupyter-notebook
    spec_app = lambda cluster_name: check_output(f"kubectl get kdcluster {cluster_name} -o jsonpath='{{.spec.app}}'")
    cluster_list = check_output("kubectl get kdcluster",namespace=namespace).split("\n")[1:] # first line are headers, split on lines
    cluster_list = list(map(lambda i: i.split()[0], cluster_list)) # take only cluster name
    return [ cluster for cluster in cluster_list if spec_app(cluster) == app_name]

def get_cm_by_name(cm_name):
    """
    Gets configmap data given configmap name  
    args:
        cm_name: String containing exact name of configmap
    output:
        Dict: Dictionary object containing configmap data
    """
    error_message=f"configmap {cm_name} not found"
    cm = check_output(f"kubectl get cm {cm_name} -o json",error_message=error_message)
    cm = json.loads(cm)['data'] if json.loads(cm)['data'] else None
    return cm

def get_cluster_connections(kdcluster_name):
    """
    Returns dictionary containing all connected resources to the provided kdcluster
    args:
        kdcluster_name: String containing exact name of kdcluster
    output:
        Dict: Dictionary with connection resource type as keys, and a list of resource names as values.
    """
    connections = json.loads(check_output(f"kubectl get kdcluster {kdcluster_name} -o json"))['spec']['connections']
    return connections
