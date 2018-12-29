import os
import logging.config
import yaml

def setup_config(
    default_path='config/config.yml'
):
    """
    Setup config parameters
    """

    root_directory = os.path.dirname(os.path.dirname(__file__))
    default_path = os.path.join(root_directory, default_path)

    try:
        with open(default_path, 'r') as yaml_file:
            yaml_config = yaml.safe_load(yaml_file)
            yaml_config.update({'root_path':root_directory}) # add root_directory to config
            return yaml_config

    except yaml.YAMLError as exc:
        raise
    except IOError as exc:
        raise

def setup_logging(
    default_path='config/logging.yml',
    default_level=logging.INFO,
    env_key='LOG_CFG',
    config_global_path = 'config/config.yml'
):
    """Setup logging configuration
    :param: config_global_path - path to config for all modules (for PSQL)
    """

    root_directory = os.path.dirname(os.path.dirname(__file__))
    config_path = os.path.join(root_directory, default_path)

    # Logger for logging while file and PSQL loggers are not initialized
    # We configure root logger and all child loggers are inherited from him
    root_logger = logging.getLogger()


    value = os.getenv(env_key, None)
    if value:
        config_path = value
    if os.path.exists(config_path):
        with open(config_path, 'rt') as f:
            config = yaml.safe_load(f.read())

        try:
            config['handlers']['file']['filename'] = os.path.join(
                root_directory,config['handlers']['file']['filename'])

            root_logger.info("Creating abs path for logging file: {}".format(config['handlers']['file']['filename']))

        except KeyError:
            root_logger.info('No logging path found in {} file. Will create it further'.format(default_path))


        try:
            logging.config.dictConfig(config)


        except ValueError: # If config for log file doesn't exist

            log_filename = str(config['handlers']['file']['filename'])
            log_filename = os.path.join(root_directory, log_filename)

            if not os.path.exists(os.path.dirname(log_filename)):
                root_logger.info('log file directory:{} doesn\'t exist. Creating it'.format(log_filename))
                os.makedirs(os.path.dirname(log_filename))

            root_logger.info('log file:{} doesn\'t exist. Creating it'.format(log_filename))
            open(log_filename,"w+")

            logging.config.dictConfig(config)