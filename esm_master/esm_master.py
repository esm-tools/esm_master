#!/usr/bin/env python
# import fileinput, os, sys, getopt

import sys

from . import database_actions
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

# kh 27.11.20
    if "modify" in parsed_args: 
        if "general" in user_config:
            user_config["general"]["modify_config_file"] = parsed_args["modify"]

    if "ignore" in parsed_args:
        ignore_errors  = parsed_args["ignore"]
    else:
        ignore_errors = False
   
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
        return 0
    user_task.validate()

    user_task.execute(ignore_errors) #env)

    database = database_actions.database_entry(
        user_task.todo, user_task.package.raw_name, ESM_MASTER_DIR
    )
    database.connection.close()

    if not parsed_args["keep"]:
        user_task.cleanup_script()

    return 0
