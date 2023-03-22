from pydantic import BaseModel, Extra
from pydantic import validator
from typing import List, Optional, Union, Any
from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter
from os import environ
from get_logger import get_logger
import json

class SSIDSpec(BaseModel):
    ssid_name: str
    network_name: str
    network_id: str
    ssid_number: int

class DemoConfigModel(BaseModel):
    api_key_spec: Optional[str]
    log_file: str
    log_stdout: bool = False
    enable_debug: bool = False
    tz: str = "Asia/Tokyo"
    server_address: str = "::"
    server_port: int = 48001
    server_basename: Optional[str] = None
    server_cert: Union[str, None]
    enable_tls: bool = True
    ui_path: str = "./ui/"
    ssid_list: List[SSIDSpec]
    logger: Any
    loop: Any

    @validator("enable_tls", always=True)
    def update_enable_tls(cls, v, values, config, **kwargs):
        return True if values["server_cert"] else False

    class Config():
        extra = Extra.forbid

def __from_args(args):
    ap = ArgumentParser(
            description="DEMO server.",
            formatter_class=ArgumentDefaultsHelpFormatter)
    ap.add_argument("config_file", metavar="CONFIG_FILE",
                    help="specify the config file.")
    ap.add_argument("-d", action="store_true", dest="enable_debug",
                help="enable debug mode.")
    ap.add_argument("-D", action="store_true", dest="log_stdout",
                help="enable to show messages onto stdout.")
    opt = ap.parse_args(args)
    environ["DEMO_CONFIG_FILE"] = opt.config_file
    environ["DEMO_ENABLE_DEBUG"] = str(opt.enable_debug)
    environ["DEMO_LOG_STDOUT"] = str(opt.log_stdout)

def __get_env_bool(key, default):
    c = environ.get(key)
    if c is None:
        return default
    elif c.upper() in [ "TRUE", "1" ]:
        return True
    elif c.upper() in [ "FALSE", "0" ]:
        return False
    else:
        raise ValueError(f"ERROR: {key} must be bool, but {c}")

def set_config(prog_name, loop, args=None):
    """
    priority order
        1. cli arguments.
        2. environment variable.
        3. config file.
    """
    if args is not None:
        __from_args(args)
    # load the config file.
    config_file = environ["DEMO_CONFIG_FILE"]
    try:
        config = DemoConfigModel.parse_obj(json.load(open(config_file)))
    except Exception as e:
        print("ERROR: {} read error. {}".format(config_file, e))
        exit(1)
    # set logger
    config.logger = get_logger(prog_name,
                               log_file=config.log_file,
                               debug_mode=config.enable_debug)
    # overwrite the config by the cli options/env variable.
    config.enable_debug = __get_env_bool("DEMO_ENABLE_DEBUG", False)
    config.log_stdout = __get_env_bool("DEMO_LOG_STDOUT", False)
    config.loop = loop
    return config

if __name__ == "__main__":
    import sys
    conf = json.load(open(sys.argv[1]))
    m = DemoConfig.parse_obj(conf)
    print(m)

