import configparser
import os
import shutil
import functools


@functools.cache
def get_config():
    """
    Gets and returns the httpycam config, caching the result
    """
    config = configparser.ConfigParser(allow_no_value=True)
    # borrowing from https://stackoverflow.com/a/53222876
    configpath = os.path.join(
        os.environ.get("APPDATA")
        or os.environ.get("XDG_CONFIG_HOME")
        or os.path.join(os.environ["HOME"], ".config"),
        "httpycam",
    )
    os.makedirs(configpath, exist_ok=True)
    config.read(os.path.join(configpath, "config.ini"))

    # no config yet, write a default one
    if len(config.sections()) == 0:
        shutil.copy("config.ini", configpath)
        config.read(os.path.join(configpath, "config.ini"))
    return config
