import requests
import ezmllib.modelmgmt.utils as utils
import mlflow
import urllib.parse
from ezmllib.constants import MODEL_MGMT_SECRET_LABEL

class Ezmodelmgmt(object):
    

    def __init__(self, exp_name=None, artifact_location= None, backend_url=None ):
        self.exp_name = exp_name
        self.header = utils.get_header()
        self.backend_url = backend_url if backend_url != None else utils.get_modelmgmt_backend_url()
        #create exp or if exp exists set exp
        if not self.backend_url:
            print(f"Please mount a {MODEL_MGMT_SECRET_LABEL} secret to the notebook, or explicitly provide a backend url with the backend_url kwarg")
            return

        if exp_name is not None and exp_name != "":
            exp_response = self.get_experiment_by_name(exp_name)
            if 'experiment' in exp_response:
                self.exp_id = exp_response['experiment']['experiment_id']
                print("Experiment already exists with name::" + str(self.exp_name))
                print("Experiment Id::" + str(self.exp_id))
            else:
                self.exp_id = None if not exp_name else self.create_experiment(exp_name, artifact_location)
        else:
            print("Experiment name cannot be Empty. No experiment created!!")
            self.exp_id = None
        self.run_id = None
        self.artifact_location = artifact_location

    #Pipeline is analogous to mlflow Experiment 
    def create_experiment(self, name, artifact_location=None, **tags):
        """
        Create mlflow experiment
        Arguments:
            name:: string:: name of experiment
            artifact_location:: string:: location of artifact
            tags:: dictionary:: key value pairs of tag
        Return:
            exp_id: experiment id
        """
        params = {}
        params["name"] = name
        if artifact_location != None:
            params["artifact_location"] = artifact_location
        if tags:
            params["tags"] = tags
        response = requests.post(self.backend_url + utils.CREATE_EXP, json=params, headers=self.header, verify=False)
        if response.status_code == 201:
            response_json = response.json()
            self.exp_id = response_json['experiment_id']
            print("Experiment created successfully!")
            print("Experiment Id::" + str(self.exp_id))
            return response_json['experiment_id']
        print(response.json())
            
    def start_run(self, **tags):
        """
        Start/create mlflow run
        Arguments:
            tags:: dictionary:: key value pairs of tag
        Return:
            Run:: object
        """
        #assuming this method is called for new run always and start new run, self.run_id = create_run()
        params = {}
        params["experiment_id"] = self.exp_id
        if tags:
            params["tags"] = tags
        response = requests.post(self.backend_url + utils.CREATE_RUN, json=params, headers=self.header, verify=False)
        if response.status_code == 201:
            response_json = response.json()
            self.run_id = response_json['run']['info']['run_id']
            return response_json['run']['info']['run_id']
        print(response.json())
    
    def log_param(self, key, value, run_id = None):
        """
        Log parameter for run
        Arguments:
            key:: string:: key name of tag
            val:: string:: value of the tag
            run_id:: string:: run id
        """
        #Default run is self.run
        params = {}
        params["run_id"] = self.run_id
        if run_id != None:
            params["run_id"] = run_id
        params["key"] = key
        params["value"] = value
        response = requests.post(self.backend_url + utils.LOG_PARAM, json=params, headers=self.header, verify=False)
        response_json = response.json()
        print(response_json)

    def log_metric(self, key, value, run_id = None):
        """
        Log metric for run
        Arguments:
            key:: string:: key name of tag
            val:: float:: value of the tag
            run_id:: string:: run id
        """
        #Default run is self.run
        params = {}
        params["run_id"] = self.run_id
        if run_id != None:
            params["run_id"] = run_id
        params["key"] = key
        params["value"] = value
        response = requests.post(self.backend_url + utils.LOG_METRIC, json=params, headers=self.header, verify=False)
        response_json = response.json()
        print(response_json)

    def log_run_tag(self, key, value, run_id = None):
        """
        Log tag for run
        Arguments:
            key:: string:: key name of tag
            val:: string:: value of the tag
            run_id:: string:: run id
        """
        #Default run is self.run
        params = {}
        params["run_id"] = self.run_id
        if run_id != None:
            params["run_id"] = run_id
        params["key"] = key
        params["value"] = value
        response = requests.post(self.backend_url + utils.SET_RUN_TAG, json=params, headers=self.header, verify=False)
        response_json = response.json()
        print(response_json)
    
    def get_run(self, run_id = None):
        """
        Get run by run_id
        Arguments:
            run_id:: string:: run id
        Return:
            Run:: object
        """
        #Default run is self.run
        params = {}
        params["run_id"] = self.run_id
        if run_id != None:
            params["run_id"] = run_id
        response = requests.get(self.backend_url + utils.GET_RUN + params["run_id"], headers=self.header, verify=False)
        response_json = response.json()
        return response_json
    
    def get_runs(self, exp_ids = []):
        """
        Get runs by exp_ids
        Arguments:
            exp_ids:: array:: array of experiment ids
        Return:
            Runs:: array:: List of runs
        """
        params = {}
        if exp_ids == None or len(exp_ids) == 0:
            params["experiment_ids"] = [self.exp_id]
        else:
            params["experiment_ids"] = exp_ids
        response = requests.post(self.backend_url + utils.SEARCH_RUN, json=params, headers=self.header, verify=False)
        response_json = response.json()
        return response_json
    
    def search_runs(self, exp_ids = [], filter = None, run_view_type = None, max_results = None, order_by = None, page_token = None):
        """
        Get runs by exp_ids
        Arguments:
            exp_ids:: array:: array of experiment ids
            filter:: str:: metrics.rmse < 1 and params.model_class = 'LogisticRegression'
            run_view_type:: str:: ACTIVE_ONLY, DELETED_ONLY, ALL
            max_results:: int:: max 5000
            order_by:: array:: [“params.input DESC”, “metrics.alpha ASC”, “metrics.rmse”] 
            page_token:: str:: pagination
        Return:
            Runs:: array:: List of runs
        """
        params = {}
        if exp_ids == None or len(exp_ids) == 0:
            params["experiment_ids"] = [self.exp_id]
        else:
            params["experiment_ids"] = exp_ids

        if filter != None:
            params['filter'] = filter

        if run_view_type != None:
            params['run_view_type'] = run_view_type
        
        if max_results != None:
            params['max_results'] = max_results
        
        if order_by != None:
            params['order_by'] = order_by

        if page_token != None:
            params['page_token'] = page_token
        
        response = requests.post(self.backend_url + utils.SEARCH_RUN, json=params, headers=self.header, verify=False)
        response_json = response.json()
        return response_json
    
    def delete_run(self, run_id = None):
        """
        Delete run by run_id
        Arguments:
            run_id:: string:: run id
        """
        #Default run is self.run
        if run_id == None:
            run_id = self.run_id
        response = requests.delete(self.backend_url + utils.DELETE_RUN + "?id=" + run_id, headers=self.header, verify=False)
        response_json = response.json()
        return response_json
    
    def restore_run(self, run_id = None):
        """
        Restore run by run_id
        Arguments:
            run_id:: string:: run id
        """
        #Default run is self.run
        if run_id == None:
            run_id = self.run_id
        response = requests.post(self.backend_url + utils.RESTORE_RUN + "?id=" + run_id, headers=self.header, verify=False)
        response_json = response.json()
        return response_json
    
    def list_experiment(self):
        """
        List all experiments of user
        Return:
            Experiments:: array:: List of experiments
        """
        response = requests.get(self.backend_url + utils.LIST_EXPS, headers=self.header, verify=False)
        response_json = response.json()
        return response_json
    
    def get_experiment(self, exp_id = None):
        """
        Get experiment by exp_id
        Arguments:
            exp_id:: string:: experiment id
        Return:
            Experiment:: object
        """
        #default is self.exp_id
        params = {}
        params["exp_id"] = self.exp_id
        if exp_id != None:
            params["exp_id"] = exp_id
        response = requests.get(self.backend_url + utils.LIST_EXPS + params["exp_id"], headers=self.header, verify=False)
        response_json = response.json()
        return response_json
    
    def get_experiment_by_name(self, exp_name):
        """
        Get experiment by name
        Arguments:
            exp_name:: string:: name of experiment
        Return:
            Experiment:: object
        """
        exp_name = urllib.parse.quote(exp_name)
        response = requests.get(self.backend_url + utils.GET_EXP_BYNAME +"?exp_name=" + exp_name, headers=self.header, verify=False)
        response_json = response.json()
        return response_json
    
    def delete_exp(self, exp_id = None):
        """
        Delete experiment by exp_id
        Arguments:
            exp_id:: string:: experiment id
        Return:
            Experiment:: object
        """
        #default is self.exp_id
        params = {}
        params["exp_id"] = self.exp_id
        if exp_id != None:
            params["exp_id"] = exp_id
        response = requests.delete(self.backend_url + utils.DELETE_EXP + params["exp_id"], headers=self.header, verify=False)
        response_json = response.json()
        return response_json

    def set_exp_tag(self, key, value, exp_id = None):
        """
        Set tag of an experiment
        Arguments:
            key:: string:: key name of tag
            val:: string:: value of the tag
            exp_id:: string:: experiment id
        """
        #default is self.exp_id
        params = {}
        params["experiment_id"] = self.exp_id
        if exp_id != None:
            params["experiment_id"] = exp_id
        params["key"] = key
        params["value"] = value
        response = requests.post(self.backend_url + utils.SET_EXP_TAG, json=params, headers=self.header, verify=False)
        response_json = response.json()
        print(response_json)

    #Direct mflow api integration
    @utils.set_env_vars_for_api
    def log_artifacts(self, folder_location, run_id=None,):
        """
        Log artifacts(folder) for a run
        Arguments:
            folder_location:: string:: full path of folder to be logged e.g., /home/<user>/testresults
            run_id:: string:: run id
        """
        if not run_id:
            run_id = self.run_id if self.run_id else self.start_run()
        if self._check_access(run_id):
            mlflow.tracking.MlflowClient().log_artifacts(run_id, folder_location, "")
        else:
            print( f"User does not have access to run {run_id}")
    
    @utils.set_env_vars_for_api
    def log_artifact(self, file_location, run_id=None ):
        """
        Log artifact(file) for a run
        Arguments:
            file_location:: string:: full path of file e.g., /home/<user>/testfile.csv
            run_id:: string:: run id
        """
        if not run_id:
            run_id = self.run_id if self.run_id else self.start_run()
        if self._check_access(run_id):
            mlflow.tracking.MlflowClient().log_artifact(run_id, file_location, "")
        else:
            print( f"User does not have access to run {run_id}")

    @utils.set_env_vars_for_api        
    def log_model(self,model=None,flavor=None,artifact_path=None,run_id=None,registered_model_name=None,**kwargs):
        """
        Log model for a run
        Arguments:
            model:: model object:: reference to model object to save and log in s3 store, accepts MlFlow supported flavours
            flavour:: module object:: mlflow module for corresponding model flavour, ex. mlflow.sklearn note: pass the actual module object, not a string containing its name
            artifact_path:: str:: Optional parameter, path to log the model artifacts to. Default value None, if not provided will read artifact path from class variable
            run_id:: string:: User can provide the run_id to associate the model with. If not provided will use value in client object
            kwargs:: dict:: User must pass all required fields for the model flavours `save_model` function, ex. flavour mlflow.sklearn requires "sk_model" as a keyword argument referencing the sklearn model object log_model(model=model, flavor=mlflow.sklearn, sk_model=model)


        If flavour or kwargs are not passed function will attempt to detect flavour from model object and prepare arguements for logging the model
        """
        if not model:
            print("Provide a model to log using the keyword 'model'")
            return
        if not flavor:
            try:
                flavor = utils.get_model_flavour_module_object(model) #ex. for a sk_model, module is mlflow.sklearn, func returns module obj of it so sk specific save can be invoked
            except TypeError as e:
                print(e)
                return
        else:
            flavor = utils.get_model_flavour_module_object_from_name(flavor)
        
        
        artifact_path = ""
        if not run_id:
            run_id = self.run_id if self.run_id else self.start_run()
        
        if not self._check_access(run_id):
            print(f"User does not have access to run {run_id}")
            return
        
        with mlflow.utils.file_utils.TempDir() as tmp:
            local_path = tmp.path("model")
            mlflow_model =  mlflow.models.Model(artifact_path=artifact_path, run_id=run_id)
            flavor_args = utils.get_args_for_flavour_save_model(flavor, model,path=local_path, **kwargs)
            flavor.save_model(**flavor_args, **kwargs)
            mlflow.tracking.MlflowClient().log_artifacts(run_id, local_path, artifact_path)
            if registered_model_name:
                mlflow.register_model(
                    "runs:/%s/%s" % (run_id, artifact_path),
                    registered_model_name,
                )

    def _check_access(self, run_id=None):
        """
        Private method for checking user access to provided run id 
        """
        if not run_id:
            run_id = self.run_id
        try:
            response = requests.get(self.backend_url + utils.GET_RUN + str(run_id), headers=self.header, verify=False) 
            return str(response.status_code) == "200" # if the server responds with 200, user has access
        except Exception as e:
            print(f"Error {e} while logging model server response: {response.text}")
            return False
