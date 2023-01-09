import os
import subprocess
from ezmllib.util.ezconfigmeta import get_namespace
from ezmllib.constants import SERVICE_ACCOUNT_TOKEN_PATH, K8S_API_SERVER, SA_CERTIFICATE_AUTHORITY, NO_PROXY

def kubectl(cmd, namespace=None, **kwargs):
    """
    Preps kubectl command as logged in user. Must set kubeconfig before using.
    args:
        cmd: String containing kubectl command
        namespace (Optional): Namespace command is executed in. Runs in tenant namespace by default
    output:
        String:  Command output / captured stdout
    """
    return _kubectl(cmd, namespace, SA=False, **kwargs)

def _kubectl(cmd, namespace=None,SA=True, **kwargs):
    """
    Preps kubectl command as service account for check_output
    args:
        cmd: String containing kubectl command
        namespace (Optional): Namespace command is executed in. Runs in tenant namespace by default
        SA (Optional): Boolean flag indicating to use service account token 
    output:
        String:  Command output / captured stdout
    """
    cmd_list = []
    for sub_cmd in cmd.split("|"):
        if 'kubectl' in sub_cmd:
            if not namespace:
                namespace = get_namespace() 
            if not ' -n ' in sub_cmd: # if cmd contains a namespace flag, do not append namespace
                sub_cmd = sub_cmd.replace('kubectl', f'kubectl -n {namespace}')
            if SA:
                 if not '--token' in sub_cmd:
                     token = open(SERVICE_ACCOUNT_TOKEN_PATH,"r").read().strip()
                     sub_cmd = sub_cmd + " " + f'--token={token}'
                 sub_cmd = sub_cmd + " " + f'--server={K8S_API_SERVER}' + " " + f'--certificate-authority={SA_CERTIFICATE_AUTHORITY}'
        cmd_list.append(sub_cmd)
    cmd = "|".join(cmd_list)
    return cmd

def check_output(cmd, success_message="", error_message="", timeout=None, verbose=True, **kwargs):
    '''
    cmd:: str:: command
    message:: str:: custom message after the command succeeds

    Example:
    check_output("env | grep 'USER=dev1'", "User found in the environment")
    '''
    os.environ['NO_PROXY']=NO_PROXY
    try:
        try:
            cmd_sa = _kubectl(cmd, **kwargs)
            output = subprocess.check_output(['bash', '-c', cmd_sa], stderr=subprocess.PIPE, timeout=timeout, env=os.environ).strip().decode('utf-8')
        except (subprocess.CalledProcessError, Exception):
            if verbose:  # This msg will always be printed until service account token is attached properly.
                print("WARN: Service account might be improperly set. The fallback solution would be to run `%kubeRefresh` or `ezmllib.kubeconfig.ezkubeconfig.set_kubeconfig()`.")
            cmd = kubectl(cmd, **kwargs)
            try:
                output = subprocess.check_output(['bash', '-c', cmd], stderr=subprocess.PIPE, timeout=timeout, env=os.environ).strip().decode('utf-8')
            except (subprocess.CalledProcessError, Exception):
                raise
        if success_message: print(success_message)
        return output
    except subprocess.CalledProcessError as e:
        if verbose:
            if error_message: print(error_message)
            print(e.output.strip().decode('utf-8'))
            print(e.stderr.strip().decode('utf-8'))
        raise

def threads_per_core():
    '''Get number of threads per core (required for XGBClassifier nthread param)'''
    nthreads = check_output(f"lscpu | grep Thread\(s\)\ per\ core")
    return int(nthreads[-1])
