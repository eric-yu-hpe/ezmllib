def get_inference_json(infernce_cluster_name,cm_array,sc_array,lb_cpu="2",lb_memory="4Gi",lb_gpu="0",
                  lb_cpu_lmt="2",lb_memory_lmt="4Gi",lb_gpu_lmt="0",rs_cpu="2",rs_memory="4Gi",
                  rs_gpu="0",rs_cpu_lmt="2",rs_memory_lmt="4Gi",rs_gpu_lmt="0",description=""):


  inference_json = {
                    "apiVersion": "kubedirector.hpe.com/v1beta1",
                    "kind": "KubeDirectorCluster",
                    "metadata": {
                      "name": infernce_cluster_name,
                      "labels": {
                        "description": description
                      }
                    },
                    "spec": {
                      "app": "deployment-engine",
                      "namingScheme": "CrNameRole",
                      "appCatalog": "local",
                      "connections": {
                        "configmaps": cm_array,
                        "secrets": sc_array,
                      },
                      "roles": [
                        {
                          "id": "LoadBalancer",
                          "members": 1,
                          "resources": {
                            "requests": {
                              "cpu": lb_cpu,
                              "memory": lb_memory,
                              "nvidia.com/gpu": lb_gpu
                            },
                            "limits": {
                              "cpu": lb_cpu_lmt,
                              "memory": lb_memory_lmt,
                              "nvidia.com/gpu": lb_gpu_lmt
                            }
                          },
                          "podLabels": {
                            "hpecp.hpe.com/dtap": "hadoop2"
                          }
                        },
                        {
                          "id": "RESTServer",
                          "members": 1,
                          "resources": {
                            "requests": {
                              "cpu": rs_cpu,
                              "memory": rs_memory,
                              "nvidia.com/gpu": rs_gpu
                            },
                            "limits": {
                              "cpu": rs_cpu_lmt,
                              "memory": rs_memory_lmt,
                              "nvidia.com/gpu": rs_gpu_lmt
                            }
                          },
                          "podLabels": {
                            "hpecp.hpe.com/dtap": "hadoop2"
                          }
                        }
                      ]
                    }
                  }
  return inference_json