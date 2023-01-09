from ..constants import AUTH_TOKEN_ANNOTATION
from ..templates import modelcm, inferencekdcluster
from ..util import ezk8s, ezconfigmeta
from ..constants import MODEL_DESTINATION,SCORING_FILE_DESTINATION,MODEL_FILE_CM,SCORING_FILE_CM
from ..constants import LB_CPU, LB_MEMORY, LB_GPU, LB_CPU_LMT, LB_MEMORY_LMT, LB_GPU_LMT, RS_CPU, RS_MEMORY, RS_GPU, RS_CPU_LMT, RS_MEMORY_LMT, RS_GPU_LMT
import json
import requests
import getpass
from pwd import getpwnam
import os
import shutil
from ezmllib.util.ezcli import check_output
from ezmllib.util.ezk8s import get_service_names


def predict(modelName, modelVersion, data, deployment_service):
    """
    Make model prediction(s)
    args:
      deployment_service:: str:: model deployment service name
      modelName:: str:: name of the model
      modelVersion:: int:: the model version
      data:: dict:: the data in dictionary format 
    return:
      str:: prediction results
    """
    get_service_names(kdapp="deployment-engine")  # inform the user about available deployment-engine names 
    service_prefix = deployment_service + "-load"
    url = get_inference_service_url(service_prefix)
    suffix = f"/{modelName}/{modelVersion}/predict"
    predict_endpoint = url + suffix
    auth_token = ezk8s.get_svc_annotation_value(service_prefix,AUTH_TOKEN_ANNOTATION)
    headers  = {'content-type' : 'application/json', 'X-AUTH-TOKEN': auth_token}
    try:
        api = 'http://' + predict_endpoint
        response = requests.post(api, data=json.dumps(data), headers=headers, verify=False)
    except Exception as e:
        api = 'https://' + predict_endpoint
        response = requests.post(api, data=json.dumps(data), headers=headers, verify=False)
    return response

def register(model_registry_name, model_path, scoring_path, model_version, model_description=None):
    """
    Register the model components. 
    This is required to serve a model by giving the model path, model version, model prediction/scoring script path.
    args:
      model_registry_name:: str:: The model registry name created to register the model_path, scoring_path and model_version
      model_path:: str:: The model path in notebook
      scoring_path:: str:: The model prediction/scoring script path in notebook
      model_version:: str::  The version of the model to serve, e.g., 'v1'
    kwargs:
      model_description:: str:: Description for the model registry
    """
    user = getpass.getuser().strip()
    model_destination = MODEL_DESTINATION + model_path.split('/')[-1]
    scoring_file_destination = SCORING_FILE_DESTINATION + scoring_path.split('/')[-1]

    model_file_cm = MODEL_FILE_CM + model_path.split('/')[-1]
    scoring_file_cm = SCORING_FILE_CM + scoring_path.split('/')[-1]

    shutil.copy(model_path, model_destination)
    shutil.copy(scoring_path, scoring_file_destination)
    json_cm_dict = modelcm.get_model_cm(model_description,model_version,model_registry_name,model_file_cm,scoring_file_cm,user)
    model_registry_file = f"/home/{user}/.model_registry_cm.json"
    try:
        with open(model_registry_file, 'w') as f:
            json.dump(json_cm_dict, f)
        # get UIDs and GIDs
        uid = getpwnam(user)[2]
        gid = getpwnam(user)[3]
        # Change the ownership of password file to user.
        os.chown(model_registry_file, uid, gid)
    except Exception as e:
        print("Failed to create configmap file")
        print(e)
    KUBECTL_CMD = f"kubectl apply -f {model_registry_file}"
    check_output(KUBECTL_CMD, "Model registered successfully", "Failed to create model registry, Please make sure you have set kubeconfig and able to make kubectl API calls")


def deploy(deployment_service,cm_array,sc_array=[],dtapenabled="false",lb_cpu=LB_CPU,lb_memory=LB_MEMORY,lb_gpu=LB_GPU,
                  lb_cpu_lmt=LB_CPU_LMT,lb_memory_lmt=LB_MEMORY_LMT,lb_gpu_lmt=LB_GPU_LMT,rs_cpu=RS_CPU,rs_memory=RS_MEMORY,
                  rs_gpu=RS_GPU,rs_cpu_lmt=RS_CPU_LMT,rs_memory_lmt=RS_MEMORY_LMT,rs_gpu_lmt=RS_GPU_LMT,description=""):
    """This function deploy the model
    """
    user = getpass.getuser().strip()
    is_dtap_enabled = dtapenabled.capitalize()
    inf_json = inferencekdcluster.get_inference_json(deployment_service, cm_array,sc_array,lb_cpu=LB_CPU,lb_memory=LB_MEMORY,lb_gpu=LB_GPU,
                  lb_cpu_lmt=LB_CPU_LMT,lb_memory_lmt=LB_MEMORY_LMT,lb_gpu_lmt=LB_GPU_LMT,rs_cpu=RS_CPU,rs_memory=RS_MEMORY,
                  rs_gpu=RS_GPU,rs_cpu_lmt=RS_CPU_LMT,rs_memory_lmt=RS_MEMORY_LMT,rs_gpu_lmt=RS_GPU_LMT,description="")
    for element in inf_json['spec']['roles']: 
        if is_dtap_enabled == 'False':
            del element['podLabels']

    inf_kdcluster_file = f"/home/{user}/.inf_kdcluster_file.json"
    try:
        with open(inf_kdcluster_file, 'w') as f:
            json.dump(inf_json, f)
        # get UIDs and GIDs
        uid = getpwnam(user)[2]
        gid = getpwnam(user)[3]
        # Change the ownership of password file to user.
        os.chown(inf_kdcluster_file, uid, gid)
    except Exception as e:
        print("Failed to create kdcluster file")
        print(e)
    check_output(f"kubectl apply -f {inf_kdcluster_file}", f"Started deploying inference app, model.get_inference_app_details(\"{deployment_service}\") function can now be used to track the status of deployment app")


def register_and_deploy(model_registry_name, model_path, scoring_path, model_version,
                                deployment_service,cm_array,sc_array=[],dtapenabled="false",lb_cpu=LB_CPU,lb_memory=LB_MEMORY,lb_gpu=LB_GPU,
                                lb_cpu_lmt=LB_CPU_LMT,lb_memory_lmt=LB_MEMORY_LMT,lb_gpu_lmt=LB_GPU_LMT,rs_cpu=RS_CPU,rs_memory=RS_MEMORY,
                                rs_gpu=RS_GPU,rs_cpu_lmt=RS_CPU_LMT,rs_memory_lmt=RS_MEMORY_LMT,rs_gpu_lmt=RS_GPU_LMT,description="", 
                                model_description=""):
    """This function register the model then deploy it in inference kd app 
    """
    register(model_path, scoring_path, model_registry_name, model_version, model_description="")
    check_output(f"kubectl get cm {model_registry_name} ", "Model registered", "Could not register the model, error occured")
    print("Started deploying the model...")
    deploy(deployment_service,cm_array,sc_array,dtapenabled="false",lb_cpu=LB_CPU,lb_memory=LB_MEMORY,lb_gpu=LB_GPU,
                  lb_cpu_lmt=LB_CPU_LMT,lb_memory_lmt=LB_MEMORY_LMT,lb_gpu_lmt=LB_GPU_LMT,rs_cpu=RS_CPU,rs_memory=RS_MEMORY,
                  rs_gpu=RS_GPU,rs_cpu_lmt=RS_CPU_LMT,rs_memory_lmt=RS_MEMORY_LMT,rs_gpu_lmt=RS_GPU_LMT,description="")
    return


def get_inference_app_details(kd_inference_app_name):
    """
       This function is to get inference app details.
       output : Status, url, message of inference app
       input : Name of inference app
    """
    kdcluster_state = ezk8s.get_kdcluster_state(kd_inference_app_name)
    if kdcluster_state == None:
        return
    if kdcluster_state == 'configured':
        return {'Inference App State' : kdcluster_state, 'Message' : f'{kd_inference_app_name} inference app reday to use', 'Service URL' : get_inference_service_url(kd_inference_app_name+'-load')}
    elif kdcluster_state == 'creating':
        return {'Inference App State' : kdcluster_state, 'Message' : f'{kd_inference_app_name} inference app is in creating state', 'Service URL' : 'Not Available Yet'}
    else:
        return {'Inference App State' : kdcluster_state, 'Message' : f'{kd_inference_app_name} inference app is in error state', 'Service URL' : 'No service url'}


def update_registry(context, modelname,modelpath=None, scoringpath=None):
    """
    This function is to update the existing model registry
    context - Name of current context, can be found in your kubeconfig
    """
    if context is None:
        print("Please specify a valid context (--context), can be found in your kubeconfig")
        return
    if modelname is None:
        print("Please specify a valid model name (--modelname)")
        return
    if scoringpath is not None:
        key = "scoring-path"
        check_output(f"""kubectl patch configmap --context {context} {modelname} -p='{{"data":{{"{key}": "{scoringpath}"}}}}'""", "Failed to update model prediction scripts path")
    if modelpath is not None:
        key = "path"
        check_output(f"""kubectl patch configmap --context {context} {modelname} -p='{{"data":{{"{key}": "{modelpath}"}}}}'""", "Failed to update model path")
        

def get_inference_service_url(service_prefix):
    """
       Get service url
       output : service url
       input : service prefix
    """
    service_list = check_output(f"kubectl get svc -o json ")
    service_list_json = json.loads(service_list)
    service_name = ""
    for service in service_list_json['items']:
        if service['metadata']['name'].startswith(service_prefix):
            service_name = service['metadata']['name']
    if not service_name:
        print("Service not found with given prefix")
        return
    service_yaml = check_output(f"kubectl get -o json svc {service_name}")
    service_yaml_json = json.loads(service_yaml)
    service_url = (f"{list(service_yaml_json['metadata']['annotations'].values())[1]}")
    return service_url
