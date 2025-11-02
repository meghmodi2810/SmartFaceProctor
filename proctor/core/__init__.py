import os
import warnings
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'  # Suppress TensorFlow logs
warnings.filterwarnings('ignore')  # Suppress other warnings

# Ensure signals are registered
default_app_config = 'core.apps.CoreConfig'