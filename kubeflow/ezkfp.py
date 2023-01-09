import kfp
import json
import os
import requests
import getpass

from ezmllib.util import ezpasswordutil
from ezmllib.util.ezk8s import get_service_endpoints
from ezmllib.util.ezcli import check_output
from ezmllib.constants import KUBEFLOW_DASHBOARD_SERVICE_PORT

decode_format = 'utf-8'

class KfSession( object ):
    def __init__( self, verify=False, **kwargs ):
        '''
        kwargs:
        user:: str
        password:: str
        url:: str
        certs:: str
        verify:: bool:: default to non-SSL, otherwise set to True to enable SSL connnection to Kubeflow dashboard
        '''
        self.user = kwargs.get("user") if kwargs.get("user") else getpass.getuser()
        self.password = kwargs.get("password") if kwargs.get("password") else self.get_password(self.user)
        self.url = (kwargs.get("url") + '/pipeline') if kwargs.get("url") else None
        self.ui = (kwargs.get("url") + '/_/pipeline') if kwargs.get("url") else None
        
        self.verify = verify
        if not self.url:
            gateway_endpoints = get_service_endpoints("kf-dashboard", "Kubeflow URL")
            self.ui = self.__pick_one_from_list_by_input(gateway_endpoints, "Kubeflow dashboard public URLs")
            if self.verify:
                self.endpoint = self.ui
            else:
                service_names = check_output("kubectl get svc | grep kf-dashboard | sed 's/|/ /' | awk '{print $1, $8}'").strip(" ").split('\n')
                service_name = self.__pick_one_from_list_by_input(service_names, "kf-dashboard Kubernetes services")
                self.endpoint = f"http://{service_name}:{KUBEFLOW_DASHBOARD_SERVICE_PORT}"
            self.url = self.endpoint + '/pipeline'
            self.ui = self.ui + '/_/pipeline'
        if self.url.startswith('https'): # Assuming only one kubeflow endpoint
            self.cert = kwargs.get("cert") if kwargs.get("cert") else input('You are using an https endpoint, please enter the path to CA certification: ')
            if not self.cert:
                raise RuntimeError('Missing CA certification. Ask admin to set up the env, and provide the path and enable CA certification.')
            elif not os.path.isfile(self.cert):
                raise FileNotFoundError(f'The path to CA certification "{self.cert}" is not found.')
        else:
            print("WARN: Using internal network connection to Kubeflow Dashboard. If you want to enable SSL, then restart the notebook kernel and use `KfSession(verify=True)` to enable manual CA cert setup.")
            self.cert = None

    @staticmethod
    def __pick_one_from_list_by_input(options, prompt):
        if len(options) > 1:
            print(f"Available {prompt}: {options}")
            return input("Please paste one URL from above to use.")
        else:
            return options[0]

    def get_password(self, user):
        if ezpasswordutil.is_pwd_available():
            pwd = ezpasswordutil.get_password()
        else:
            print("please enter your password")
            pwd = getpass.getpass()
            ezpasswordutil.save_password(pwd)
        return pwd

    def replacePattern(self, sourceFile, pattern, value):
        with open(sourceFile, "rt") as fin:
            tmpData = fin.read()
            tmpData = tmpData.replace(pattern, value)
            fin.close()
            fin = open(sourceFile, "wt")
            fin.write(tmpData)
            fin.close()

# Return session cookie from url, username and password
    def get_user_auth_session_cookie(self, url, username, password):
        url = url.replace('/pipeline', '')
        verify = self.cert if self.verify else self.verify
        get_response = requests.get(url, verify=verify)
        if 'auth' in get_response.url:
            credentials = {'login': username, 'password': password}
            # Authenticate user
            session = requests.Session()
            session.post(get_response.url, data=credentials, verify=verify)
            cookie_auth_key = 'authservice_session'
            cookie_auth_value = session.cookies.get(cookie_auth_key)
            if cookie_auth_value:
                return cookie_auth_key + '=' + cookie_auth_value

# If user's kubeflow directory exists, read session cookies from there and return client object
# If not create session cookies and store it with endpoint in user;s kubeflow directory
    def kf_client(self, recreate=False):
        """
        kf_client create a .kubeflow directory with kf.json which contain kubeflow endpoint, session, and certs location.
        :param recreate: help the user to recreate .kubeflow and kf.json if .kubeflow got deleted.
        """
        try:
            user = self.user
            kf_dir = '/home/' + user + '/.kubeflow'
            kf_file = '/opt/guestconfig/appconfig/templates/kf.json'
            if not os.path.exists(kf_dir + '/kf.json') or recreate == True:
                try:
                    args_url = self.url
                    os.system('mkdir -vp '+ kf_dir)
                    os.system('cp -f ' + kf_file + ' ' + kf_dir)
                    if args_url is not None:
                        endpoint = args_url
                        password = self.password
                        session_cookie = self.get_user_auth_session_cookie(endpoint,user,password)
                        client = kfp.Client(host=endpoint,cookies=session_cookie, ssl_ca_cert=self.cert, ui_host=self.ui)
                        user_kf_file = "/home/" + self.user + "/.kubeflow/kf.json"
                        self.replacePattern(user_kf_file, '@@@SESSION@@@', session_cookie)
                        self.replacePattern(user_kf_file, '@@@KF_ENDPOINT@@@', endpoint)
                        self.replacePattern(user_kf_file, '@@@UI_ENDPOINT@@@', self.ui)
                        self.replacePattern(user_kf_file, '@@@CERT_LOCATION@@@', self.cert or '')
                        print("Kubeflow client Set")
                        return client
                except Exception as e:
                    os.system('rm -rf '+ kf_dir)
                    print(e)
                    raise
            else:
                user_kf_file = "/home/" + self.user + "/.kubeflow/kf.json"
                with open(user_kf_file) as fp:
                    datajson = json.load(fp)
                    if len(self.url)==0:
                        endpoint = datajson['url']
                    else:
                        endpoint = self.url
                    session_cookie = datajson['session']
                    if self.cert is None:
                        ca_cert = datajson.get('cert')
                        self.cert = ca_cert if (isinstance(ca_cert, str) and len(ca_cert) != 0) else None
                    client = kfp.Client(host=endpoint,cookies=session_cookie,ssl_ca_cert=self.cert,ui_host=self.ui)
                    # Verify if session cookie has expired. if so create a new session cookie and return client created with it.
                    kf_response=json.dumps(str(client.list_pipelines()))
                    if "'pipelines': None" in kf_response:
                        user = getpass.getuser()
                        password = self.password
                        session_cookie = self.get_user_auth_session_cookie(endpoint,user,password)
                        client = kfp.Client(host=endpoint,cookies=session_cookie,ssl_ca_cert=self.cert,ui_host=self.ui)
                        os.system('mkdir -vp '+ kf_dir)
                        os.system('cp -f ' + kf_file + ' ' + kf_dir)
                        self.replacePattern(user_kf_file, '@@@SESSION@@@', session_cookie)
                        self.replacePattern(user_kf_file, '@@@KF_ENDPOINT@@@', endpoint)
                        self.replacePattern(user_kf_file, '@@@UI_ENDPOINT@@@', self.ui)
                        self.replacePattern(user_kf_file, '@@@CERT_LOCATION@@@', self.cert or '')
                    print("Kubeflow client set")

                return client
        except Exception as inst:
            print(type(inst))    # the exception instance
            print(inst.args)     # arguments stored in .args
            print(inst)
            print("Please provide the correct kubeflow endpoint and user's password")
