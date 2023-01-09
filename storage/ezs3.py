from ezmllib.util import ezk8s
from ezmllib.util.ezcli import check_output
from ezmllib.util.ezconfigmeta import encode_parameter
from ezmllib.constants import MLFLOW_S3_CREDENTIALS_SECRET

import os, sys, logging, re
import hashlib
import getpass
import boto3
import yaml
from botocore.client import Config

class s3_util( object ):
    """A utility for s3 upload and download fucntionality
    """
    def __init__( self, src, dest ):
        self.info = {}
        self.info['SOURC_LOC'] = src
        self.info['DEST_LOC'] = dest
        self.info.update(ezk8s.get_secret_data_by_name(MLFLOW_S3_CREDENTIALS_SECRET))

    def getRemotePath(self, path):
        #example: path = 's3://hpe/data/model3.pkl'
        path = re.sub('^[a-z0-9]*://','', path) # remove s3:// or any url protocal
        path_list = path.strip('/').split('/') # # remove leading '/', and split path into a list
        return path_list[0], ('/').join(path_list[1:]) 

    def upload(self, **kwargs):
        self.download_upload(self.info['DEST_LOC'], 'upload', **kwargs)

    def download(self, **kwargs):
        self.download_upload(self.info['SOURC_LOC'], 'download', **kwargs)

    def download_upload(self, url, action, **kwargs):
        try:
            self.info['BUCKET_NAME'], self.info['REMOTE_NAME'] = self.getRemotePath(url)
            try:
                if not kwargs.get('aws_access_key_id'):
                    print("Using k8s tenant secret S3_ACCESS_KEY_ID")
                    kwargs['aws_access_key_id'] = self.info['S3_ACCESS_KEY_ID']
                if not kwargs.get('aws_secret_access_key'):
                    print("Using k8s tenant secret S3_SECRET_ACCESS_KEY")
                    kwargs['aws_secret_access_key'] = self.info['S3_SECRET_ACCESS_KEY']
                kwargs['config'] = Config(signature_version='s3v4')
                # S3 Connect
                s3 = boto3.resource('s3', verify=False, **kwargs)
                try:
                    if action =='upload':
                        s3.Bucket(self.info['BUCKET_NAME']).upload_file(self.info['SOURC_LOC'],self.info['REMOTE_NAME'])
                        print("File uploaded to s3")
                    elif action =='download':
                        s3.Bucket(self.info['BUCKET_NAME']).download_file(self.info['REMOTE_NAME'], self.info['DEST_LOC'])
                        print("File downloaded from s3")
                except Exception as e:
                    print('Failed to connect to s3 bucket. You might need to provide your aws_access_key_id and aws_secret_access_key to the s3_util.upload() or s3_util.download() function.')
                    raise
            except Exception as e:
                raise
        except Exception as e:
            print("Failed to %s file"%action)
            sys.exit(0)

def create_s3_secret(s3_id, s3_key):
    user =  getpass.getuser().strip()
    secret_file = f"/home/{user}/examples/s3/{MLFLOW_S3_CREDENTIALS_SECRET}"

    with open(secret_file, 'r') as secret:
        data = secret.read()
        secret_yaml = yaml.safe_load(data)
        secret_yaml['data']['S3_ACCESS_KEY_ID'] = encode_parameter(s3_id)
        secret_yaml['data']['S3_SECRET_ACCESS_KEY'] = encode_parameter(s3_key)

    with open(secret_file, 'w') as secret:
        secret.write(yaml.dump(secret_yaml))
    try:
        check_output(f"kubectl apply -f {secret_file}")
        print("S3 Credentials Secret Successfully Created")
    except:
        print("S3 Credentials Secret Failed to be Created, please check provided credentials are valid and that the k8s environment is properly configured.")
