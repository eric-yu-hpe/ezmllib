from ezmllib.util.ezlog import k8s_job_log, k8s_job_status, k8s_job_events

def logs(name, events = False, status = False, **kwargs):
    '''
    Print out kubeflow job logs in the notebook
    args:
      name:: kubeflow job name
    
    kwargs:
      follow:: [True,False]:: stream the logs
      since:: ["10m","30m","1h"...]
      tail:: ["10","15","100",...]:: tail the last N lines
      previous:: [True,False]
    '''
    if events:
      k8s_job_events(name)
    elif status:
      k8s_job_status(name)
    else:
      k8s_job_log(pod_name = f"{name}", 
                service_name = kwargs.get("service_name"), 
                is_streaming_log = kwargs.get("follow"),
                container_name = kwargs.get("container_name"),  
                since = kwargs.get("since"), 
                tail = kwargs.get("tail"), 
                previous = kwargs.get("previous"))
