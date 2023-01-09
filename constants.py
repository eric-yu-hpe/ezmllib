import os

# kubernetes.default is the dns for service account, and is used during the check_output command
# adding it to the NO_PROXY env list will prevent the network from routing through hpecp proxy
NO_PROXY = 'kubernetes.default,' + str(os.environ['NO_PROXY']) if os.environ.get('NO_PROXY') else 'kubernetes.default'


CONFIG_DIR = '/home/guestconfig'
PUBLIC_CONFIG_METADATA_FILE = os.path.join(CONFIG_DIR, 'configmeta.json')
MLFLOW_SECRET_FILE_TEMPLATE = '/opt/guestconfig/appconfig/templates/mlflow-dp'
FERNET_KEY_FILE = "/etc/guestconfig/fernet_key"
DECODE_FORMAT_UTF = 'utf-8'
AUTH_TOKEN_ANNOTATION = 'kubedirector.hpe.com/kd-auth-token'
MLFLOW_S3_CREDENTIALS_SECRET = 's3-cred'
MODEL_MGMT_SECRET_LABEL = 'model-mgmt'
KUBEFLOW_USER_SECRET = 'kubeflow-users-secret'
SERVICE_ACCOUNT_TOKEN_PATH = "/var/run/secrets/kubernetes.io/serviceaccount/token"

#kubeflow
KUBEFLOW_DASHBOARD_SERVICE_PORT = "80"

#kdmodel related constants
MODEL_DESTINATION="/bd-fs-mnt/project_repo/models/"
SCORING_FILE_DESTINATION="/bd-fs-mnt/project_repo/code/"
MODEL_FILE_CM="repo://project_repo/models/"
SCORING_FILE_CM="repo://project_repo/code/"
LB_CPU="2"
LB_MEMORY="4Gi"
LB_GPU="0"
LB_CPU_LMT="2"
LB_MEMORY_LMT="4Gi"
LB_GPU_LMT="0"
RS_CPU="2"
RS_MEMORY="4Gi"
RS_GPU="0"
RS_CPU_LMT="2"
RS_MEMORY_LMT="4Gi"
RS_GPU_LMT="0"

# ezk8s 
KDAPP_CONDITION_DEPLOYMENT = "loadbalancer"
KDAPP_CONDITION_TRAINING = "loadbalancer"
KDAPP_CONDITION_NOTEBOOK = "controller"
KDAPP_CONDITION_OTHERS = "controller"

# spark constants
SPARK_IMAGE_NAME="gcr.io/mapr-252711/spark-py-3.1.2:202111021109R"
SPARK_DRIVER_CORES = 1
SPARK_DRIVER_MEMORY = "512m"
SPARK_DRIVER_CORE_LIMIT = "1000m"
SPARK_EXECUTOR_CORES = 1 
SPARK_EXECUTOR_INSTANCES = 2 
SPARK_EXECUTOR_MEMORY = "512m" 
SPARK_EXECUTOR_CORE_LIMIT = "1000m"
SPARK_VERSION = "3.1.2" 
SPARK_PYTHON_VERSION = "3" 
SPARK_APP_TYPE = "Python" 
SPARK_API_VERSION = "sparkoperator.hpe.com/v1beta2" # "sparkoperator.k8s.io/v1beta2" 
SPARK_KIND = "SparkApplication" 
SPARK_MODE = 'cluster'
SPARK_DRIVER_LABELS = {'version': SPARK_VERSION, 'hpecp.hpe.com/dtap': 'hadoop2'}
SPARK_EXECUTOR_LABELS = {'version': SPARK_VERSION, 'hpecp.hpe.com/dtap': 'hadoop2'}
SPARK_IMAGE_PULL_POLICY = 'Always'
SPARK_RESTART_POLICY = {'type': 'Never'}
SPARK_IMAGE_PULL_SECRETS = ['imagepull']
SPARK_FIXED_IMAGE_TAG='202111021109R'
# TODO
# "spark.eventLog.enabled":"false" is a temporary fix to disable integration with history server,
# Once the spark 3.1.2 image issue is fixed, we'll enable the history server by deleting this key-value
SPARKCONF = {
          'spark.eventLog.enabled':'false',
          'spark.hadoop.fs.dtap.impl': 'com.bluedata.hadoop.bdfs.Bdfs',
          'spark.hadoop.fs.AbstractFileSystem.dtap.impl': 'com.bluedata.hadoop.bdfs.BdAbstractFS',
          'spark.hadoop.fs.dtap.impl.disable.cache': 'false',
          'spark.driver.extraClassPath': 'local:///opt/bdfs/bluedata-dtap.jar',
          'spark.executor.extraClassPath': 'local:///opt/bdfs/bluedata-dtap.jar'
          }

# sa constants
K8S_API_SERVER = "https://kubernetes.default"
SA_CERTIFICATE_AUTHORITY = "/var/run/secrets/kubernetes.io/serviceaccount/ca.crt"


# tensorflow constants
TFVERSION='2.4.0'


