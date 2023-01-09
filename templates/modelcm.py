# TODO: createdBy field in configmap needs to be identified. It is different for each user
# createdBy is used by ecp ui
def get_model_cm(model_description,model_version,model_registry_name,model_path,scoring_path,user):
  json_cm_dict = {
                   "apiVersion":"v1",
                   "data":{
                      "description": model_description,
                      "model-version": model_version,
                      "modelType":"kubedirector",
                      "name": model_registry_name,
                      "path": model_path,
                      "scoring-path": scoring_path
                   },
                   "kind":"ConfigMap",
                   "metadata":{
                      "labels":{
                        #  "createdBy":"21",
                         "createdByUserName": user,
                         "kubedirector.hpe.com/cmType":"model"
                      },
                      "name": model_registry_name
                   }
                }
  return json_cm_dict