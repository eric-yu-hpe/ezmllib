import os
import requests
import getpass
import inspect
import functools
import mlflow
from ezmllib.util import ezconfigmeta, ezpasswordutil
from ezmllib.util.ecp_gateway_util import EcpGatewayUtil
from ezmllib.constants import MODEL_MGMT_SECRET_LABEL
#MLFlow model mgmt backend REST APIs
CREATE_EXP = '/api/v1/experiments/create'
GET_EXP = '/api/v1/mlflow/experiments/get'
LIST_EXPS = '/api/v1/experiments/'
GET_EXP_BYNAME = '/api/v1/experimentbyname'
DELETE_EXP = '/api/v1/experiments/'
SET_EXP_TAG = '/api/v1/experiments/tag'
GET_RUN = '/api/v1/runs/'
CREATE_RUN = '/api/v1/runs/create'
DELETE_RUN = '/api/v1/runs'
RESTORE_RUN = '/api/v1/runs/restore'
SEARCH_RUN = '/api/v1/runs/search'
SET_RUN_TAG = '/api/v1/run/tag'
LOG_METRIC = '/api/v1/runs/log-metric'
LOG_PARAM = '/api/v1/run/log-param'

def get_header():
    return {'Content-Type': 'application/json', 'accept':'application/json', 'X-BDS-SESSION': get_session()}

def get_modelmgmt_backend_url():
    return ezconfigmeta.get_secret_data_value(MODEL_MGMT_SECRET_LABEL, "MODELMGMT_BACKEND_URL")

def get_session():
    username = getpass.getuser().strip()
    password = get_password()
    data = {"name":username, "password":password}
    gateway = ezconfigmeta.get_gateway()
    ecp_util = EcpGatewayUtil()
    prefix = ecp_util.get_prefix()
    headers  = {'content-type' : 'application/json'}
    url = prefix +  "://" + gateway + ":8080/api/v1/login"
    response = requests.post(url, json=data, headers=headers, verify=False)
    session=response.headers['Location']
    return session

def get_password():
    """Get user password
    """
    if ezpasswordutil.is_pwd_available():
        pwd = ezpasswordutil.get_password()
    else:
        print("please enter your password")
        pwd = getpass.getpass()
        ezpasswordutil.save_password(pwd)
    return pwd

def get_object_module_name(object):
    """
    Returns name of the module the object is from
    """
    module = inspect.getmodule(object)
    package = module.__package__ if module.__package__ else None
    return module.__name__ if not package else package.split(".")[0]

def get_model_flavour_module_object(model):
    """
    Returns an instance of the mlflow module that corresponds to the flavour of model provided 
    """
    module = get_object_module_name(model)
    return get_model_flavour_module_object_from_name(module)

def get_model_flavour_module_object_from_name(module):
    """
    Returns an instance of the mlflow module that corresponds to the flavour of model provided 
    """
    if module in dir(mlflow): # check if mlflow supports the flavour in the apk
        flavour = getattr(mlflow, module) # load the mlflow module in the flavour variable
        return flavour
    elif module == "pyspark":# mlflow.spark supports pyspark python library
        flavour = getattr(mlflow, "spark")
        return flavour
    elif module == "__main__":
        raise TypeError(f"ERROR: If provided model is defined with a custom class, provide the model flavor as keyword argument. Ex: client.log_model(model=custom_model, flavor='pytorch'...)")
    else: 
        raise TypeError(f"ERROR: Unsupported model flavour from {module} module")

def get_args_for_flavour_save_model(flavor,model, *args, **kwargs): 
    """
    Returns dict of arguments adding missing parameters to fit existing flavour specific save_model interface
    """
    #TODO implement remaining mlflow supported flavours 
    if flavor is mlflow.sklearn:
        return get_sklearn_save_model_args(model, *args,**kwargs)
    elif flavor is mlflow.keras:
        return get_keras_save_model_args(model, *args, **kwargs)
    elif flavor is mlflow.xgboost:
        return get_xgboost_save_model_args(model, *args, **kwargs)
    elif flavor is mlflow.pytorch:
        return get_pytorch_save_model_args(model, *args, **kwargs)
    elif flavor is mlflow.h2o:
        return get_h2o_save_model_args(model, *args, **kwargs)
    elif flavor is mlflow.spark:
        return get_spark_save_model_args(model, *args, **kwargs)
    elif flavor is mlflow.tensorflow:
        return get_tensorflow_save_model_args(model, *args, **kwargs)
    else: # setup support for all mlflow flavours, then can extend to other flavours
        print (f"Model flavor {flavor} is unsupported at this time.")

def get_sklearn_save_model_args(model, **kwargs):
    kwargs['sk_model'] = model
    return kwargs 

def get_keras_save_model_args(model, **kwargs):
    kwargs['keras_model'] = model
    return kwargs

def get_xgboost_save_model_args(model, **kwargs):
    kwargs['xgb_model'] = model
    return kwargs

def get_pytorch_save_model_args(model, **kwargs):
    kwargs['pytorch_model'] = model
    return kwargs

def get_h2o_save_model_args(model, **kwargs):
    kwargs['h2o_model'] = model
    return kwargs

def get_spark_save_model_args(model, **kwargs):
    kwargs['spark_model'] = model
    return kwargs

def get_tensorflow_save_model_args(model, tf_meta_graph_tags=None, tf_signature_def_key=None, **kwargs):
    local_path=kwargs['path']
    if not tf_meta_graph_tags:
        kwargs['tf_meta_graph_tags'] = [ tag_constants.SERVING ]
    if not tf_signature_def_key:
        kwargs['tf_signature_def_key'] = signature_constants.DEFAULT_SERVING_SIGNATURE_DEF_KEY
    saved_model.save(model, f'{local_path}/tf_saved_model_dir')
    kwargs['tf_saved_model_dir'] = f'{local_path}/tf_saved_model_dir'
    kwargs['path'] = f'{local_path}/model'
    return kwargs

def set_env_vars_for_api(func):
    @functools.wraps(func)
    def wrap(*args, **kwargs):
        model_mgmt_dict = ezconfigmeta.get_secret_data(MODEL_MGMT_SECRET_LABEL)
        if model_mgmt_dict is None:
            return
        os.environ["MLFLOW_TRACKING_URI"] = model_mgmt_dict["MLFLOW_TRACKING_URI"]
        os.environ["MLFLOW_ARTIFACT_ROOT"] = model_mgmt_dict["MLFLOW_ARTIFACT_ROOT"]
        os.environ["MLFLOW_S3_ENDPOINT_URL"] = model_mgmt_dict["MLFLOW_S3_ENDPOINT_URL"]
        os.environ["AWS_ACCESS_KEY_ID"] = model_mgmt_dict["AWS_ACCESS_KEY_ID"]
        os.environ["AWS_SECRET_ACCESS_KEY"] = model_mgmt_dict["AWS_SECRET_ACCESS_KEY"]
        os.environ["MLFLOW_S3_IGNORE_TLS"]= 'true'
        func(*args, **kwargs)
        os.environ.pop('MLFLOW_TRACKING_URI',None)
        os.environ.pop('MLFLOW_S3_ENDPOINT_URL',None)
        os.environ.pop('MLFLOW_ARTIFACT_ROOT',None)
        os.environ.pop('AWS_ACCESS_KEY_ID',None)
        os.environ.pop('AWS_SECRET_ACCESS_KEY',None)
        os.environ.pop("MLFLOW_S3_IGNORE_TLS", None)

    return wrap
