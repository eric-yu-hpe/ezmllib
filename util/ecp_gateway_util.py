import requests, json
import concurrent.futures
from concurrent.futures import ThreadPoolExecutor
import base64, yaml
import time


class EcpGatewayUtil(object):
    def get_gateway_dns(self):
        with open('/home/guestconfig/configmeta.json') as f:
             data = json.load(f)
             if 'kubeconfig' in data['connections']['secrets'] :
                 kubeconfigValues = data['connections']['secrets']['kubeconfig']
                 for d in kubeconfigValues:
                     config = base64.b64decode(d['data']['config']).decode("utf-8")
                     config = yaml.full_load(config)
                     gateway = config['users'][0]['user']['exec']['args'][2][:-5]
        return gateway
    
    def get_rest_api_response(self,url):
        try:
            response = requests.get(url, verify=False, timeout=10)
        except Exception as e:
            return None
        if response.status_code == 200:
            prefix = url.split("://")[0]
            return prefix
        return None

    def get_prefix(self):
        with ThreadPoolExecutor(max_workers=4) as executor:
            gateway = self.get_gateway_dns()
            f1 = executor.submit(self.get_rest_api_response, url="https://" + gateway + ":8080/api/v2/config")
            f2 = executor.submit(self.get_rest_api_response, url="http://" + gateway + ":8080/api/v2/config")

            output = None
            while(True):
                if f1.done() and f1.result()!=None:
                    output = f1.result()
                    break
                if f2.done() and f2.result()!=None:
                    output = f2.result()
                    break
                if f1.done() and f2.done():
                    break
                time.sleep(0.001)

            concurrent.futures.thread._threads_queues.clear()
            executor._threads.clear()
        return output
    
    def get_gateway_url(self):
        return self.get_prefix() + "://" + self.get_gateway_dns()
