import getpass
from ezmllib.constants import MLFLOW_SECRET_FILE_TEMPLATE
from ezmllib.util.ezconfigmeta import base64_decode, get_service_endpoint, get_clusters_based_on_ditro_id, get_secret_data
from ezmllib.util.ezlog import mlflow_job_log
from ezmllib.util.ezcli import check_output

import getpass
import json, requests
import subprocess
import getpass
import yaml
import os, json
import os.path
import logging, sys
import base64
import contextlib
from dotenv import load_dotenv
import shutil


def load_mlflow():
    """
    This function is used to import and set environment variables for mlflow
    It then also creates a secret populatetd with s3 credentials and endpoint for prism to utilize
    """
    try:
        scvalues = get_secret_data('mlflow')
        aws_access_key_id = scvalues['AWS_ACCESS_KEY_ID']
        aws_secret_access_key = scvalues['AWS_SECRET_ACCESS_KEY']
        key_id = f'AWS_ACCESS_KEY_ID={aws_access_key_id}' # this will go in .env file
        secret_access_key = f'AWS_SECRET_ACCESS_KEY={aws_secret_access_key}' # this will go in .env file
        endpoint_url = ""
        cluster_name = get_clusters_based_on_ditro_id('hpecp/mlflow')[-1]

        mlflowui_value = get_service_endpoint(cluster_name,'mlflow-server')
        mlflowui = f'MLFLOW_TRACKING_URI={mlflowui_value}'
        if mlflowui_value:
            mlflowui = f'MLFLOW_TRACKING_URI={mlflowui_value}'
            if 'MLFLOW_S3_ENDPOINT_URL' in scvalues:
                endpoint_url = scvalues['MLFLOW_S3_ENDPOINT_URL']
            else:
                endpoint_url = get_service_endpoint(cluster_name,'minio-server')
        artifactui = f'MLFLOW_S3_ENDPOINT_URL={endpoint_url}' # this will go in .env file
        sslflag = "MLFLOW_S3_IGNORE_TLS=true"
        env_val = ('\n').join([key_id,secret_access_key,artifactui,mlflowui,sslflag])
        name =  getpass.getuser().strip()  
        mlfile = "/home/" + name + "/.env"
        with open(mlfile, "w") as a:
            a.write(env_val)
        load_dotenv()
        _create_mlflow_secret(scvalues, name, endpoint_url)
    except Exception as e:
        print("Failed to set backend for Mlflow.")
        print(e)

def _create_mlflow_secret(scvalues, uname, endpoint_url):
    """
    This function is called by function 'load_mlflow' to create mlflow deployment secret for prism.
    """
    try:
        secret_dir = f'/home/{uname}/.secret/'
        check_output(f'mkdir -vp {secret_dir}')
        standard_secret_file = MLFLOW_SECRET_FILE_TEMPLATE
        check_output(f'cp -f {standard_secret_file} {secret_dir}')
        user_secret_file = os.path.join(secret_dir, 'mlflow-dp')
                
        # we open the template JSON and replace the values in it with the required values
        with open(standard_secret_file, "r") as secret_template:
            secret_json = json.load(secret_template)
        secret_json["stringData"]["AWS_ACCESS_KEY_ID"] = scvalues['AWS_ACCESS_KEY_ID']
        secret_json["stringData"]["AWS_SECRET_ACCESS_KEY"] = scvalues['AWS_SECRET_ACCESS_KEY']
        secret_json["stringData"]["AWS_ENDPOINT_URL"] = endpoint_url
        secret_json["stringData"]["RCLONE_CONFIG_S3_ACCESS_KEY_ID"] = scvalues['AWS_ACCESS_KEY_ID']
        secret_json["stringData"]["RCLONE_CONFIG_S3_SECRET_ACCESS_KEY"] = scvalues['AWS_SECRET_ACCESS_KEY']
        secret_json["stringData"]["RCLONE_CONFIG_S3_ENDPOINT"] = endpoint_url

        # we then write to the file for kubectl apply command 
        with open(user_secret_file, "w") as secret_file: 
            json.dump(secret_json, secret_file)
        # try to replace the secret. If secret is not present, an exception will be thrown.
        # If an exception is caught, try kubectl apply. 
        # If apply fails, an exception will be thrown which will be caught by the outer except block
        try:
            command = f'kubectl replace -f {user_secret_file}'
            check_output(command)
        except:
            command = f'kubectl apply -f {user_secret_file}'
            check_output(command)
    except Exception as e:
        print("Resource generation failed.")
        print(e)

def register_model(modelname, modelpath, description_url=""):
    """
    This function is used to register a model for deployment and creates a configmap with the details.
    It takes in model artifact path and the name to be registered.
    """
    try:
        uname = getpass.getuser()
        config_map_dir = f'/home/{uname}/.configmap/' + modelname + '/'
        check_output(f'mkdir -vp {config_map_dir}')
        standard_configmap_file = '/opt/guestconfig/appconfig/templates/mlflow-cm'
        check_output(f'cp -f {standard_configmap_file} {config_map_dir}')
        user_secret_file = os.path.join(config_map_dir, 'mlflow-cm')
                
        # we open the template JSON and replace the values in it with the required values
        with open(standard_configmap_file, "r") as secret_template:
            secret_json = json.load(secret_template)
        secret_json["data"]["modelArtifactUrl"] = modelpath
        secret_json["data"]["description"] = description_url
        secret_json["data"]["name"] = modelname
        secret_json["metadata"]["name"] = modelname
        secret_json["metadata"]["labels"]["createdByUserName"] = uname

        # we then write to the file for kubectl apply command 
        with open(user_secret_file, "w") as secret_file: 
            json.dump(secret_json, secret_file)
        # try to replace the configmap. If configmap is not present, an exception will be thrown.
        # If an exception is caught, try kubectl apply. 
        # If apply fails, an exception will be thrown which will be caught by the outer except block
        try:
            command = f'kubectl replace -f {user_secret_file}'
            check_output(command)
        except:
            command = f'kubectl apply -f {user_secret_file}'
            check_output(command)
    except Exception as e:
        print("Failed to register Mlflow model.")
        print(e)

def set_exp(exp_name):
    """
    This function is used to register an experiment in mlflow tracking service.
    The name of the experiment provided by the user will be set in mlflow.
    """
    try:
        import mlflow
        usr = getpass.getuser()
        mlflow.set_experiment(exp_name)
        mlflow.set_tag('mlflow.user', usr)
    except Exception as e:
        print("Failed to set user.")
        print(e)

def logs(job_id, training_engine_name):
    '''
    Print out mlflow job logs in the notebook
    args:
      job_id: mlflow job id
      training_engine_name: training engine cluter name
    '''
    mlflow_job_log(job_id, training_engine_name)
