import os, json
import requests
from ezmllib.util.ezk8s import get_svc_annotation_value
from ezmllib.util.ezcli import check_output

# function for get kubeflow pod log which is bascially remove kubectl
# pod_name, service_name, is_streaming_log, container_name, since, tail, previous - logs flag
def k8s_job_log(pod_name = None, service_name = None, is_streaming_log = False, container_name = None, since = None, tail = None, previous = False):
    kubectl_cmd = "kubectl logs " 
    if container_name is not None:
        kubectl_cmd += " -c " + container_name + " "
    if pod_name is not None:
        kubectl_cmd += pod_name
    if service_name is not None:
        kubectl_cmd += service_name
    if is_streaming_log:
        kubectl_cmd += " -f "
    if since is not None:
        kubectl_cmd += " --since=" + since
    if tail is not None:
        kubectl_cmd += " --tail=" + tail
    if previous:
        kubectl_cmd += " --previous "
    output = check_output(kubectl_cmd).strip() 
    print(output)

def k8s_job_status(pod_name):
    kubectl_cmd = f'kubectl get pods {pod_name} --no-headers -o custom-columns=":status.phase"'
    output = check_output(kubectl_cmd, error_message="No pod or job is found!")
    print(output)

def k8s_job_events(pod_name):
    kubectl_cmd = f'kubectl get event --field-selector involvedObject.name={pod_name}'
    output = check_output(kubectl_cmd) 
    print(output)

# mlflow training job log
def mlflow_job_log(job_id, training_engine_name):
    try:
        history_url = training_job_end_point(job_id, training_engine_name)
        history_response = requests.request("GET", history_url + "?auth=none").json()[0]
        status = history_response['status']
        log_url = history_response['log_url'] + "?auth=none"
        print("Job Status: {0}".format(status))
        logs_json = requests.request("GET", log_url).json()
        if logs_json['logs']:
            print(logs_json['logs'])
    except Exception as e:
        print("No logs to show at this time for this job!")

def training_job_end_point(job_id, training_engine_name):
    training_engine_name = str(training_engine_name) + '-loadbalancer-'
    training_api_server_end_point = get_svc_annotation_value(training_engine_name, 'hpecp-internal-gateway/10001')
    return 'http://' + training_api_server_end_point + '/history/' + str(job_id)
    
            
