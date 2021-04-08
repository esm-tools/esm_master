#!/usr/bin/env python
# import fileinput, os, sys, getopt

import sys
import os
import yaml

from . import database_actions

# deniz: TODO: refactor verbose and check like in other tools (eg. esm_runscripts)
from .cli import verbose, check

from .general_stuff import (
        GeneralInfos, 
        version_control_infos, 
        tab_completion, 
        write_minimal_user_config,
        ESM_MASTER_DIR
        )

from .compile_info import setup_and_model_infos

from .task import Task


def main_flow(parsed_args, target):

    main_infos = GeneralInfos()
    vcs = version_control_infos()
   
    setups2models = setup_and_model_infos(vcs, main_infos, parsed_args)
    tab_completion(parsed_args, setups2models)
    setups2models.config = setups2models.reduce(target)
    
    user_config = write_minimal_user_config(setups2models.config)
    # Miguel: Move this somewhere else after talking to Paul and Dirk
    user_config["general"]["run_or_compile"] = "compiletime"

    # deniz: small bugfix: when esm_master receives --verbose, it did not make
    # it into the configuration since it was only a global variable
    if verbose:
        user_config["general"]["verbose"] = True
    
    from esm_runscripts.sim_objects import SimulationSetup
    complete_setup = SimulationSetup(user_config=user_config)
    complete_config = complete_setup.config

    # This will be a problem later with GEOMAR
    #setups2models.replace_last_vars(env)


    user_task = Task(target, setups2models, vcs, main_infos, complete_config)

    if verbose > 0:
        user_task.output()

    user_task.output_steps()

    if check:
        # deniz: if the environment variable ESM_MASTER_DEBUG is also set dump
        # the contents of the current config to stdout for more investigation 
        if os.environ.get("ESM_MASTER_DEBUG", None):
            print()
            print("Contents of the complete_config:")
            print("--------------------------------")
            print(yaml.dump(complete_config, default_flow_style=False, indent=4) ) 
        
        print("esm_master: check mode is activated. Not executing the actions above")
        return 0
    
    user_task.validate()

    user_task.execute() #env)

    database = database_actions.database_entry(
        user_task.todo, user_task.package.raw_name, ESM_MASTER_DIR
    )
    database.connection.close()

    if not parsed_args["keep"]:
        user_task.cleanup_script()

    
    return 0
