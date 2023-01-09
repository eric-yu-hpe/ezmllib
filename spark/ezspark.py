import yaml
import subprocess
import re
from ezmllib.util.ezlog import k8s_job_log, k8s_job_events
from ezmllib.util.ezcli import check_output
from ezmllib.constants import SPARK_IMAGE_NAME, SPARK_DRIVER_CORES, SPARK_DRIVER_MEMORY, SPARK_DRIVER_CORE_LIMIT, SPARK_EXECUTOR_CORES, SPARK_EXECUTOR_INSTANCES, SPARK_EXECUTOR_MEMORY, SPARK_EXECUTOR_CORE_LIMIT
from ezmllib.constants import SPARK_VERSION, SPARK_PYTHON_VERSION, SPARK_APP_TYPE, SPARK_API_VERSION, SPARK_KIND
from ezmllib.constants import SPARKCONF, SPARK_IMAGE_PULL_SECRETS, SPARK_RESTART_POLICY, SPARK_IMAGE_PULL_POLICY, SPARK_EXECUTOR_LABELS, SPARK_DRIVER_LABELS, SPARK_MODE, SPARK_FIXED_IMAGE_TAG
from ezmllib.util.ezconfigmeta import get_namespace

# this might not work namespace is not set explicitly
#def get_namespace(): 
#    return subprocess.check_output(['bash', '-c', "kubectl config view --minify --output 'jsonpath={..namespace}'"]).strip().decode('utf-8')

def set_namespace(yaml_path, namespace):
    with open(yaml_path,"r") as f:
        content = yaml.safe_load(f)
        content['metadata']['namespace'] = namespace
        text = yaml.dump(content, default_flow_style=False, sort_keys=False)
    # Overwrite namespace field in the file
    with open(yaml_path,"w") as f:
        f.write(text)

def get_name(yaml_path):
    with open(yaml_path,"r") as f:
        content = yaml.safe_load(f)
    return content['metadata']['name']
             
def fix_image(yaml_path):
    '''
    fix the PRESERVE_CONTAINER error in spark image gcr.io/mapr-252711/spark-py-2.4.7:202104010902C
    '''
    image = check_output(f"cat {yaml_path} | grep image | grep spark") # get the spark image name
    if re.search(SPARK_FIXED_IMAGE_TAG,image): # if the image is 202104010902C 
        value = "true"
        check_output(f"kubectl get cm cluster-cm -o json | jq '.data[\"PRESERVE_CONTAINER\"]=\"{value}\"' | kubectl replace -f -") # modify configmap

def submit(app_path = None, #"local:///opt/mapr/spark/spark-2.4.7/examples/src/main/python/wordcount.py", 
           data_path = None, #"dtap://TenantStorage/data/wordcount.txt", 
           yaml_path = None, 
           name = None, # "pyspark-wordcount-secure"
           image_name = SPARK_IMAGE_NAME, 
           driver_cores = SPARK_DRIVER_CORES,
           driver_memory = SPARK_DRIVER_MEMORY, 
           driver_core_limit = SPARK_DRIVER_CORE_LIMIT,
           executor_cores = SPARK_EXECUTOR_CORES, 
           executor_instances = SPARK_EXECUTOR_INSTANCES,
           executor_memory = SPARK_EXECUTOR_MEMORY, 
           executor_core_limit = SPARK_EXECUTOR_CORE_LIMIT,
           spark_version = SPARK_VERSION, 
           python_version = SPARK_PYTHON_VERSION, 
           app_type = SPARK_APP_TYPE, 
           api_version = SPARK_API_VERSION, # "sparkoperator.k8s.io/v1beta2" 
           kind = SPARK_KIND, 
           namespace = None,
           ):
    '''
    Submit spark jobs with inputs or yaml file
    '''
    #print("WARNING: Make sure site administrator has enabled Spark Operator and Picasso-compute addons (if not then install sparkoperator with helm-chart and set api_version to sparkoperator.k8s.io/v1beta2).")
    config = locals()
    print(f"Spark configuration: {config}")
    if not namespace:
        namespace = get_namespace() 
    if not yaml_path:
        if not app_path:
            print("Error: Please provide your application path starting with dtap://, maprfs://, hdfs://, http://, https://, ftp://, s3a:// (with extra user config access key, secret key as extra fields in the spark job yaml)")
            return
        if not data_path:
            print("Error: Please provide your data path starting with dtap://, maprfs://, hdfs://, http://, https://, ftp://, s3a:// (with extra user config access key, secret key as extra fields in the spark job yaml") 
            return
        if not name:
            print("Error: Please provide your spark job name") 
            return
        # spark configs user won't be able to change 
        default = {'metadata':{}, 'spec':{'driver':{'labels':{}}, 'executor':{'labels':{}}} }
        default['spec']['sparkConf'] = SPARKCONF
        default['spec']['driver']['labels'] = SPARK_DRIVER_LABELS 
        default['spec']['executor']['labels'] = SPARK_EXECUTOR_LABELS 
        default['spec']['mode'] = SPARK_MODE 
        default['spec']['imagePullPolicy'] = SPARK_IMAGE_PULL_POLICY 
        default['spec']['restartPolicy'] = SPARK_RESTART_POLICY
        default['spec']['arguments'] = [''] # for data_path
        default['spec']['imagePullSecrets'] = SPARK_IMAGE_PULL_SECRETS
        try:
            # spark configs that user can change
            default['apiVersion'] = api_version
            default['spec']['mainApplicationFile'] = app_path
            default['spec']['image'] = image_name 
            default['spec']['arguments'][0] = data_path # need more care from a list
            default['spec']['driver']['cores'] = driver_cores
            default['spec']['driver']['memory'] = driver_memory
            default['spec']['driver']['coreLimit'] = driver_core_limit
            default['spec']['executor']['cores'] = executor_cores
            default['spec']['executor']['instances'] = executor_instances
            default['spec']['executor']['memory'] = executor_memory
            default['spec']['executor']['coreLimit'] = executor_core_limit
            default['spec']['sparkVersion'] = spark_version 
            default['spec']['pythonVersion'] = python_version 
            default['spec']['type'] = app_type 
            default['kind'] = kind 
            default['metadata']['name'] = name 
            default['metadata']['namespace'] = namespace
            text = yaml.dump(default, default_flow_style=False, sort_keys=False)
            yaml_path = "/tmp/spark-job.yaml" 
            with open(yaml_path,"w") as f:
                f.write(text)
        except yaml.YAMLError as exc:
            print(exc)      
    set_namespace(yaml_path, namespace)
    submit_by_yaml(yaml_path)

def submit_by_yaml(yaml_path):
    # fix the image spark-py-2.4.7:202104010902C
    name = get_name(yaml_path)
    fix_image(yaml_path)
    submitSparkJob = f"kubectl apply -f {yaml_path}"
    check_output(submitSparkJob, f"Spark application '{name}' created") 

        
def delete(*args):
    """
    args:
      name:: str:: job names
    """
    if not args:
        tmp = check_output("kubectl get sparkapplications")
        names = [s.split(" ")[0] for s in tmp.split("\n")[1:]]  # spark application names
        if not names:
            print("No available spark jobs")
            return 
        print(f"Available spark job names: {names}")
        args = input("Please type the space-delimited spark job names (e.g., name1 name2 name3): ").split(" ")
    name = " ".join(args)
    deleteSparkJob = f"kubectl delete sparkapplications {name}"
    name = ", ".join(args)
    check_output(deleteSparkJob, f"Spark applications [{name}] deleted")


        
def logs(name, events=False, **kwargs):
# TODO: spark job name in cr to log
    '''
    Print out spark job logs in the notebook
    args:
      name:: spark job name
    
    kwargs:
      events:: [True,False]:: if True will list pod events
      follow:: [True,False]:: stream the logs
      since:: ["10m","30m",...]
      tail:: ["10","15","100",...]:: tail the last N lines
      previous:: [True,False]
    '''
    check_output(f"while ! kubectl get pod/{name}-driver 2> /dev/null | grep -q 'Running\|Completed\|Ready' ; do sleep 1; done; echo 'spark job started'", timeout=360) # check if spark job started to get the logs
    if events:
        k8s_job_events(f'{name}-driver')
    else:
        k8s_job_log(pod_name = f"{name}-driver", 
                    container_name = "spark-kubernetes-driver",
                    is_streaming_log = kwargs.get('follow'), 
                    service_name = kwargs.get("service_name"), 
                    since = kwargs.get("since"), 
                    tail = kwargs.get("tail"), 
                    previous = kwargs.get("previous"))
        
