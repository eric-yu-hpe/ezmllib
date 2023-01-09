from ezmllib.util import ezpam, ezconfigmeta, ezpasswordutil
from ezmllib.constants import KUBEFLOW_USER_SECRET
from ezmllib.util.ezcli import check_output
from ezmllib.util.ecp_gateway_util import EcpGatewayUtil
from ezmllib.util.ezconfigmeta import get_namespace

import requests
import getpass
import yaml
import os, json
import os.path
import logging, sys
import base64
import shutil

def set_kubeconfig(pwd=None):
    """
    This function is to set kubeconfig for current user.
    It makes an API call to ECP and gets latest kubeconfig file.
    """
    try:
        user = getpass.getuser().strip()
        if pwd is None:
            pwd = get_password(user)
        ezpam.validate_user(user,pwd)
        gateway = ezconfigmeta.get_gateway()
        # always create an empty .kube directory
        kubedir = os.path.join('/home', user, '.kube')
        if os.path.exists(kubedir):
            shutil.rmtree(kubedir)
        os.makedirs(kubedir)
        ecp_util = EcpGatewayUtil()
        prefix = ecp_util.get_prefix()
        #get the new kubeconfig and write it in home folder
        with open(os.path.join(kubedir, 'config'), 'w') as file:
            try:
                file.write(get_kubeconfig_user(gateway, user, pwd, prefix))
            except Exception as e:
                print("kubeconfig refresh failed")
                print(e)
                return
        print("kubeconfig set for user " + user)
        try:
            add_secret_users(user)
        except:
            print("Unable to add user to kubeflow dashboard")
            raise
    except Exception as e:
        print("Failed to execute kubeRefresh")
        print(e)
        raise

    return None


def set_local_kubeconfig():
    """
    This function is to set kubeconfig from user uploaded kubeconfig file present in notebook directory /home/{user}/kubeconfig/
    """
    user = getpass.getuser().strip()
    local_kube_dir = "/home/" + user + "/kubeconfig"
    if os.path.isdir(local_kube_dir):
        file_list = [f for f in os.listdir(local_kube_dir) if not f.startswith('.ipy')]
        if len(file_list) == 1:
            try:
                local_kube_file = local_kube_dir + "/" + file_list[0]
                with open(local_kube_file, 'r') as f:
                    kube_config_data = f.read()
                # always create an empty .kube directory
                kubedir = os.path.join('/home', user, '.kube')
                if os.path.exists(kubedir):
                    shutil.rmtree(kubedir)
                os.makedirs(kubedir)
                #get the new kubeconfig and write it in home folder
                with open(os.path.join(kubedir, 'config'), 'w') as file:
                    file.write(kube_config_data)
                temp_result = check_output(f'kubectl get pods')
                print("Kubeconfig is available to use")
                try:
                    add_secret_users(user)
                except:
                    print("Unable to add user to kubeflow dashboard")
                    raise
            except Exception as e:
                print(f"Kubeconfig got expired, please update config file under directory /home/{user}/kubeconfig/")
                print(e)
            return
        else:
            print(f"Please make sure you have only one config file under directory /home/{user}/kubeconfig/")
            return
    else:
        print(f"Kubeconfig file not found. Please add config file under directory /home/{user}/kubeconfig/")
        return

def get_session(ip, username, password, prefix,tenant = None):
    """
    Get current session id of user
    """
    if tenant:
        data = {"name":username, "password":password, "tenant_name": tenant}
    else:
        data = {"name":username, "password":password}
    headers  = {'content-type' : 'application/json'}
    url = prefix +  "://" + ip + ":8080/api/v1/login"
    response = requests.post(url, json=data, headers=headers, verify=False)
    session=response.headers['Location']
    return session

def get_tenant_name(session, namespace, prefix, ip):
    """
    Get current tenant the user is operating in
    """
    headers = { 'X-BDS-SESSION' : session}
    url = prefix + "://" + ip + ":8080/api/v2/tenant"
    response = requests.get(url, headers=headers, verify=False)
    tenants = response.json()['_embedded']['tenants']
    tenant_name = None
    for tenant in tenants:
        if tenant["tenant_enclosed_properties"]["namespace"]==namespace:
            tenant_name=tenant["label"]['name']
            break
    return tenant_name if tenant_name is not None else namespace

def get_kubeconfig_user(ip, username, password, prefix):
    """
    Get kubeconfig data of user
    """
    #Get a vlid session first
    try:
        session = get_session(ip, username, password, prefix)
    except Exception as e:
        #check if its SAML configured notebook by checking jupyterhub authenticator class
        #If yes, read session id from UPSTREAM_TOKEN
        if "AUTHENTICATOR_CLASS" in os.environ and os.environ['AUTHENTICATOR_CLASS'].lower() == 'ecpssoauthenticator':
            if "UPSTREAM_TOKEN" in os.environ:
                session = '{UPSTREAM_TOKEN}'.format(**os.environ)
            else:
                print("Missing UPSTREAM_TOKEN")

    #extract current tenant name using namespace
    namespace = get_namespace()
    tenant_name = get_tenant_name(session,namespace,prefix,ip)

    #Call the session api to get a new session with context of current tenant
    try:
        session = get_session(ip, username, password, prefix, tenantname)
    except Exception as e:
        #check if its SAML configured notebook by checking jupyterhub authenticator class
        #If yes, read session id from UPSTREAM_TOKEN
        if "AUTHENTICATOR_CLASS" in os.environ and os.environ['AUTHENTICATOR_CLASS'].lower() == 'ecpssoauthenticator':
            if "UPSTREAM_TOKEN" in os.environ:
                session = '{UPSTREAM_TOKEN}'.format(**os.environ)
            else:
                print("Missing UPSTREAM_TOKEN")

    headers = { 'X-BDS-SESSION' : session}
    url = prefix + "://" + ip + ":8080/api/v2/k8skubeconfig"
    response = requests.get(url, headers=headers, verify=False)
    return response.text


def get_password(user):
    """Get user password
    """
    if ezpasswordutil.is_pwd_available():
        pwd = ezpasswordutil.get_password()
    else:
        print("please enter your password")
        pwd = getpass.getpass()
        ezpasswordutil.save_password(pwd)
    return pwd


def add_secret_users(user):
    """Add a new user to the kubeflow-users-secret
    """
    secret_created, secret_data = secret_exists()
    if secret_created:
        users = json.loads(secret_data)
        users = users['data']['users']
        users = base64.b64decode(users).decode('utf-8').strip()
        user_list = users.split(",")
        if user in user_list:
            return
        user_list.append(user)
        users = ",".join(user_list)
        #users = str(base64.b64encode(users.encode('utf-8')))
        users_enc = check_output(f'echo {users} | base64')
        addUser = f"kubectl get secret {KUBEFLOW_USER_SECRET} -o json | jq '.data[\"users\"]=\"{users_enc}\"' | kubectl replace -f -"
        check_output(addUser)
    else:
        createSecret = f"kubectl create secret generic {KUBEFLOW_USER_SECRET} --from-literal=users={user}"
        check_output(createSecret)
        
def secret_exists():
    """Check if secret exists
    """
    try:
        getSecret = f"kubectl get secret {KUBEFLOW_USER_SECRET} -o json"
        output = check_output(getSecret, verbose=False)
        return (True, output)
    except:
        return (False, None)
