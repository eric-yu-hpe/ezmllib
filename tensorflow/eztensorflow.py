
from ezmllib.constants import TFVERSION

def config(tf, v2=False):
    '''
    Configure the tensorflow env in notebook session

    args:
       tf:: tensorflow library object
       v2:: bool:: disable v2 by default when tf version <= TFVERSION
    return:
       tf:: tensorflow library object
    '''
    gpus = tf.config.list_physical_devices('GPU')
    print("Num GPUs Available: ", len(gpus))
    if gpus:
        for gpu in gpus:
            tf.config.experimental.set_memory_growth(gpu, True) # apply this to avoid OOM
        print("Configured the GPU memory to growth mode")
        if tf.__version__ <= TFVERSION and not v2:
            tf.compat.v1.disable_eager_execution()
            print(f"Disabling v2 eager mode for tensorflow versions <= {TFVERSION}. If still need eager mode (which might run into performance issue on version <= {TFVERSION}) then run `ezmllib.tensorflow.config(v2=True)`")     
            print(f"Make sure to run `tf.reset_default_graph()` to free up the GPU memory at the end of each tf.Session(), or your tensorflow performance will degrade with memory leak.")
        if v2:
            tf.compat.v1.enable_eager_execution()
            print(f"Enabling v2 eager mode")
    
    return tf
