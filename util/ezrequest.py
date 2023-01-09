import requests

def get_service_prefix(endpoint):
    try:
        prefix = 'http'
        requests.get(f"{prefix}://{endpoint}", verify=False)
    except:
        try:
            prefix = 'https'
            requests.get(f"{prefix}://{endpoint}", verify=False)
        except OSError:
            prefix = 'https'
        except:
            prefix = 'http'
    return prefix
