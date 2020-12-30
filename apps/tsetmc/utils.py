import logging
import os
import re
from logging.handlers import RotatingFileHandler

from pid import PidFile


def get_or_create_task_logger(func):
    """ A helper function to create function specific logger lazily. """

    # https://docs.python.org/2/library/logging.html?highlight=logging#logging.getLogger
    # This will always result the same singleton logger
    # based on the task's function name (does not check cross-module name clash,
    # for demo purposes only)
    logger = logging.getLogger(func.__name__)

    # Add our custom logging handler for this logger only
    # You could also peek into Celery task context variables here
    #  http://celery.readthedocs.org/en/latest/userguide/tasks.html#context
    if len(logger.handlers) == 0:
        # Log to output file based on the function name
        handler = logging.FileHandler('logs/%s.log' % func.__name__)
        formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)

    return logger


def check_running(function_name):
    if not os.path.exists('./locks'):
        os.mkdir('./locks')
    file_lock = PidFile(str(function_name), piddir='./locks')
    try:
        file_lock.create()
        return file_lock
    except:
        return None


def close_running(file_lock):
    file_lock.close()


def extract_script_values(parsed_html, namad_key, func_name, logger):
    """
    This function will extract script values based on namad page and returns this values as dict.
    :param parsed_html: parsed html body of soup type
    :param namad_key: number of specific namad
    :param func_name: name of function for logging
    :param logger: logger object of logging
    :return: script dict after job is done and False if any exceptions occurs
    """
    script = str(parsed_html.find(
        string=re.compile("TopInst"))
    ).replace('var ', '').replace(';', '').split(',')

    script_dict = {}
    try:
        for s in script:
            temp_v = s.split('=')[1].replace("'", "").strip()
            try:
                key, value = s.split('=')[0], float(temp_v)
            except ValueError:
                key, value = s.split('=')[0], temp_v
            script_dict[key] = value
    except Exception as err:
        logger.error(
            "[Exception occurred when trying to evaluating script values]-"
            "[Error body: {}]-"
            "[Error type: {}]"
            "[Namad key: {}]-"
            "[Func name: {}]".format(
                str(err),
                type(err),
                namad_key,
                func_name
            )
        )
        return False

    return script_dict
