#!/usr/bin/env python
# import fileinput, os, sys, getopt

import sys

from .cli import verbose, check

from .general_stuff import (
        GeneralInfos, 
        version_control_infos, 
        tab_completion, 
        write_minimal_user_config,
        )

from .compile_info import setup_and_model_infos





def main_flow(parsed_args, target):

    main_infos = GeneralInfos()
    vcs = version_control_infos()
    
    setups2models = setup_and_model_infos(vcs, main_infos)
    setups2models.config = setups2models.reduce(target)

    user_config = write_minimal_user_config()
    from esm_runscripts.esm_sim_objects import SimulationSetup

    tab_completion(parsed_args, setups2models)

    # This will be a problem later with GEOMAR
    #setups2models.replace_last_vars(env)

    user_task = Task(target, setups2models, vcs, main_infos, complete_config)
    if verbose > 0:
        user_task.output()

    user_task.output_steps()

    if check:
        return 0
    user_task.validate()
    #env.write_dummy_script()

    user_task.execute() #env)
    database = database_actions.database_entry(
        user_task.todo, user_task.package.raw_name, ESM_MASTER_DIR
    )
    database.connection.close()

    if not keep:
        user_task.cleanup_script()

    return 0
