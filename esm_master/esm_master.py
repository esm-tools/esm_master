#!/usr/bin/env python
# import fileinput, os, sys, getopt

import sys, copy, os, re, subprocess
import argparse

import esm_parser
import esm_environment

from .cli import verbose

from .general_stuff import *

######################################################################################
############################## class "software_package" ##############################
######################################################################################


def replace_var(var, tag, value):
    if var and tag and value:
        if type(var) == str:
            return var.replace("${" + tag + "}", value)
        elif type(var) == list:
            newlist = []
            for entry in var:
                newlist.append(replace_var(entry, tag, value))
            return newlist


class software_package:
    def __init__(
        self, raw, setup_info, vcs, general, no_infos=False
    ):  # model_and_version):
        if type(raw) == str:
            (
                dummy,
                self.kind,
                self.model,
                self.version,
                dummy2,
                self.raw_name,
            ) = setup_info.split_raw_target(raw, setup_info)
        else:  # tupel:
            (self.kind, self.model, self.version) = raw
            self.raw_name = setup_info.assemble_raw_name(
                None, self.kind, self.model, self.version
            )

        self.tag = None
        if not no_infos:
            self.fill_in_infos(setup_info, vcs, general)
        else:
            self.targets = self.subpackages = None
            self.repo_type = self.repo = self.branch = None
            self.bin_type = None
            self.bin_names = [None]
            self.command_list = None
            self.destination = None
            self.coupling_changes = None

    def fill_in_infos(self, setup_info, vcs, general):

        self.targets = self.get_targets(setup_info, vcs)
        self.subpackages = self.get_subpackages(setup_info, vcs, general)
        self.complete_targets(setup_info)
        self.repo_type, self.repo, self.branch = self.get_repo_info(setup_info, vcs)
        self.destination = setup_info.get_config_entry(self, "destination")
        if not self.destination:
            self.destination = self.raw_name

        self.coupling_changes = self.get_coupling_changes(setup_info)
        self.repo = replace_var(self.repo, self.model + ".version", self.version)
        self.branch = replace_var(self.branch, self.model + ".version", self.version)

        self.bin_type, self.bin_names = self.get_comp_type(setup_info)
        self.command_list = self.get_command_list(setup_info, vcs, general)

    def get_targets(self, setup_info, vcs):
        config = setup_info.config
        targets = []
        for todo in setup_info.known_todos:
            if setup_info.has_target(self, todo, vcs):
                targets.append(todo)
        return targets

    def complete_targets(self, setup_info):
        for todo in setup_info.known_todos:
            for package in self.subpackages:
                if todo in package.targets:
                    if todo not in self.targets:
                        self.targets.append(todo)

    def get_coupling_changes(self, setup_info):
        config = setup_info.config
        changes = []
        if self.kind == "couplings":
            these_changes = setup_info.get_config_entry(self, "coupling_changes")
            if these_changes:
                changes = changes + these_changes
        elif self.kind == "setups":
            couplings = setup_info.get_config_entry(self, "couplings")
            if couplings:
                for coupling in couplings:
                    changes = []
                    if "coupling_changes" in config["couplings"][coupling]:
                        these_changes = config["couplings"][coupling][
                            "coupling_changes"
                        ]
                        if these_changes:
                            changes = changes + these_changes
        return changes

    def get_subpackages(self, setup_info, vcs, general):
        subpackages = []
        config = setup_info.config

        if self.kind == "setups":
            couplings = setup_info.get_config_entry(self, "couplings")
            if couplings:
                for coupling in couplings:
                    newpackage = software_package(coupling, setup_info, vcs, general)
                    subpackages += newpackage.get_subpackages(setup_info, vcs, general)

        if self.kind == "couplings":
            components = setup_info.get_config_entry(self, "components")
            if components:
                for component in components:
                    found = False
                    for package in subpackages:
                        if component == package.raw_name:
                            found = True
                            break
                    if not found:
                        newpackage = software_package(
                            component, setup_info, vcs, general
                        )
                        subpackages += newpackage.get_subpackages(
                            setup_info, vcs, general
                        )
                        subpackages.append(newpackage)

        elif self.kind == "components":
            requirements = setup_info.get_config_entry(self, "requires")
            if requirements:
                for component in requirements:
                    found = False
                    for package in subpackages:
                        if component == package.raw_name:
                            found = True
                            break
                    if not found:
                        newpackage = software_package(
                            component, setup_info, vcs, general
                        )
                        subpackages += newpackage.get_subpackages(
                            setup_info, vcs, general
                        )
                        subpackages.append(newpackage)

        # if self.kind == "couplings":
        #    components = setup_info.get_config_entry(self, "components")
        #    if components:
        #        for component in components:
        #            comp_tupel = software_package(component, setup_info, vcs, general)
        #            if comp_tupel not in subpackages:
        #                subpackages.append(comp_tupel)
        # elif self.kind == "setups":
        #    couplings = setup_info.get_config_entry(self, "couplings")
        #    if couplings:
        #        for coupling in couplings:
        #            for component in config["couplings"][coupling]["components"]:
        #                 found = False
        #                 for package in subpackages:
        #                    if component == package.raw_name:
        #                        found = True
        #                        break
        #                if not found:
        #                    subpackages.append(
        #                        software_package(component, setup_info, vcs, general)
        #                    )
        # elif self.kind == "components":
        #    requirements = setup_info.get_config_entry(self, "requires")
        ##    if requirements:
        #        for requirement in requirements:
        #            found = False
        #            if subpackages:
        #                for package in subpackages:
        #                    if requirement == package.raw_name:
        #                        found = True
        #                        break
        #                if not found:
        #                    subpackages.append(
        #                      software_package(requirement, setup_info, vcs, general)
        #                    )
        #            else:
        #                subpackages.append(
        #                  software_package(requirement, setup_info, vcs, general)
        #                )
        return subpackages

    def get_comp_type(self, setup_info):
        exec_names = setup_info.get_config_entry(self, "install_bins")
        if exec_names:
            if type(exec_names) == str:
                exec_names = [exec_names]
            return "bin", exec_names
        exec_names = setup_info.get_config_entry(self, "install_libs")
        if exec_names:
            if type(exec_names) == str:
                exec_names = [exec_names]
            return "lib", exec_names
        return "bin", []

    def get_repo_info(self, setup_info, vcs):
        repo = branch = repo_type = None
        for check_repo in vcs.known_repos:
            repo = setup_info.get_config_entry(self, check_repo + "-repository")
            if repo:
                repo_type = check_repo
                break
        branch = setup_info.get_config_entry(self, "branch")
        return repo_type, repo, branch

    def get_command_list(self, setup_info, vcs, general):
        command_list = {}
        for todo in self.targets:
            if todo in vcs.known_todos:
                commands = vcs.assemble_command(self, todo, setup_info, general)
            else:
                commands = setup_info.get_config_entry(self, todo + "_command")
            if commands:
                if type(commands) == str:
                    commands = [commands]
                if not todo == "get":
                    commands.insert(0, "cd " + self.destination)
                    commands.append("cd ..")
            if todo == "get":
                if self.coupling_changes:
                    commands = []
                    for change in self.coupling_changes:
                        commands.append(change)
            command_list.update({todo: commands})
        return command_list

    def output(self):
        print()
        print(self.raw_name)
        print(
            "    Model:", self.model, ", Version:", self.version, ", Kind:", self.kind
        )
        if self.subpackages:
            for package in self.subpackages:
                print("    Subpackage: ", package.raw_name)
        if self.targets:
            print("    Targets: ", self.targets)
        if self.repo_type:
            print(
                "    Repo_type: ",
                self.repo_type,
                ", repo: ",
                self.repo,
                ", branch: ",
                self.branch,
            )
        if self.bin_type:
            print("    Bin_type: ", self.bin_type, ", bin_names: ", self.bin_names)
        if self.command_list:
            print("    Commands:")
            for todo in self.command_list.keys():
                print("        ", todo, self.command_list[todo])
        if self.coupling_changes:
            print("    Coupling Changes:")
            for todo in self.coupling_changes:
                print("        ", todo)


######################################################################################
################################# class "task" #######################################
######################################################################################


class Task:
    """What you can do with a software_package, e.g. comp-awicm-2.0"""
    def __init__(self, raw, setup_info, vcs, general, complete_config):
        if raw == "default":
            raw = ""
        if raw == "drytestall":
            # panic
            for package in setup_info.all_packages:
                for todo in package.targets:
                    try:
                        print(todo + "-" + package.raw_name)
                        newtask = Task(todo + "-" + package.raw_name, setup_info, vcs)
                        newtask.output_steps()
                    except:
                        print("Problem found with target " + newtask.raw_name)
                        sys.exit(1)
            sys.exit(0)

        if type(raw) == str:
            (
                self.todo,
                kind,
                model,
                version,
                self.only_subtask,
                self.raw_name,
            ) = setup_info.split_raw_target(raw, setup_info)
            self.package = software_package(
                (kind, model, version), setup_info, vcs, general
            )
        else:  # tupel:
            (self.todo, kind, model, version, self.only_subtask) = raw
            self.package = software_package(
                (kind, model, version), setup_info, vcs, general
            )
            self.raw_name = setup_info.assemble_raw_name(
                self.todo, kind, model, version
            )

        if kind == "components":
            self.env = esm_environment.esm_environment.EnvironmentInfos(
                    "compiletime",
                    complete_config,
                    model
                    )
        else:
            self.env = None
        if not self.todo in setup_info.meta_todos:
            self.check_if_target(setup_info)

        self.subtasks = self.get_subtasks(setup_info, vcs, general, complete_config)
        self.only_subtask = self.validate_only_subtask()
        self.ordered_tasks = self.order_subtasks(setup_info, vcs, general)

        self.will_download = self.check_if_download_task(setup_info)
        self.folders_after_download = self.download_folders()
        self.binaries_after_compile = self.compile_binaries()
        self.dir_list = self.list_required_dirs()
        self.command_list, self.shown_command_list = self.assemble_command_list()

        if verbose > 1:
            self.output()

    def get_subtasks(self, setup_info, vcs, general, complete_config):
        subtasks = []
        if self.todo in setup_info.meta_todos:
            todos = setup_info.meta_command_order[self.todo]
        else:
            todos = [self.todo]
        for todo in todos:
            for subpackage in self.package.subpackages:
                if todo in subpackage.targets:
                    subtasks.append(
                        Task(
                            (
                                todo,
                                subpackage.kind,
                                subpackage.model,
                                subpackage.version,
                                None,
                            ),
                            setup_info,
                            vcs,
                            general,
                            complete_config,
                        )
                    )
        # if subtasks == [] and self.todo in setup_info.meta_todos:
        if self.todo in setup_info.meta_todos:
            for todo in todos:
                if todo in self.package.targets:
                    subtasks.append(
                        Task(
                            (
                                todo,
                                self.package.kind,
                                self.package.model,
                                self.package.version,
                                None,
                            ),
                            setup_info,
                            vcs,
                            general,
                            complete_config,
                        )
                    )
        return subtasks

    def validate_only_subtask(self):
        only = None
        if self.only_subtask:
            only = []
            for task in self.subtasks:
                if task.package.raw_name.startswith(self.only_subtask):
                    only.append(task)
            if self.package.raw_name.startswith(self.only_subtask):
                self.subtasks = []
                return None
            if only == []:
                print()
                print(
                    "Given subtask "
                    + self.only_subtask
                    + " is not a valid subtask of package "
                    + self.raw_name
                    + "."
                )
                print()
                sys.exit(0)

        return only

    def order_subtasks(self, setup_info, vcs, general):
        subtasks = self.subtasks
        if self.only_subtask:
            if self.only_subtask == "NONE":
                return []
            elif type(self.only_subtask) == str:
                return [self.only_subtask]
            else:
                subtasks = self.only_subtask
        if subtasks == []:
            return [self]
        if self.todo in setup_info.meta_todos:
            todos = setup_info.meta_command_order[self.todo]
        else:
            todos = [self.todo]

        ordered_tasks = []
        for todo in todos:
            for task in subtasks:
                if task.todo == todo and task.package.bin_type == "lib":
                    ordered_tasks.append(task)
            for task in subtasks:
                if task.todo == todo and not task.package.bin_type == "lib":
                    ordered_tasks.append(task)  #
        if self.package.kind == "components" and not self.only_subtask:
            ordered_tasks.append(self)
        return ordered_tasks

    def check_if_download_task(self, setup_info):
        if self.todo == "get":
            return True
        if self.todo in setup_info.meta_todos:
            if "get" in setup_info.meta_command_order[self.todo]:
                return True
        return False

    def download_folders(self):
        # if self.package.kind in ["setups", "couplings"]:
        if self.package.subpackages:
            dir_list = [self.package.raw_name]
            for task in self.ordered_tasks:
                if (
                    self.package.raw_name + "/" + task.package.destination
                    not in dir_list
                ):
                    dir_list.append(
                        self.package.raw_name + "/" + task.package.destination
                    )
        else:
            dir_list = []
            for task in self.ordered_tasks:
                if task.package.destination not in dir_list:
                    dir_list.append(task.package.destination)
        return dir_list

    def compile_binaries(self):
        file_list = []
        for task in self.ordered_tasks:
            for binfile in task.package.bin_names:
                if (
                    self.package.raw_name
                    + "/"
                    + task.package.bin_type
                    + "/"
                    + binfile.split("/")[-1]
                    not in file_list
                ):
                    file_list.append(
                        self.package.raw_name
                        + "/"
                        + task.package.bin_type
                        + "/"
                        + binfile.split("/")[-1]
                    )
        return file_list

    def list_required_dirs(self):
        toplevel = self.package.raw_name
        if self.package.kind in ["setups", "couplings"] and self.will_download:
            dir_list = [self.package.raw_name]
        else:
            dir_list = []
        for task in self.ordered_tasks:
            if task.todo == "comp":
                if task.package.bin_names:
                    newdir = toplevel + "/" + task.package.bin_type
                    if newdir not in dir_list:
                        dir_list.append(newdir)
        return dir_list

    def assemble_command_list(self):
        command_list = []
        toplevel = self.package.destination
        # if self.package.kind in ["setups", "couplings"]:
        if self.package.subpackages:  # ???
            command_list.append("mkdir -p " + toplevel)
            command_list.append("cd " + toplevel)
            toplevel = "."
        real_command_list = command_list.copy()
        for task in self.ordered_tasks:
            if task.todo in ["get"]:
                if task.package.command_list[task.todo] is not None:
                    for command in task.package.command_list[task.todo]:
                        command_list.append(command)
                        real_command_list.append(command)

        if self.package.coupling_changes:
            for change in self.package.coupling_changes:
                command_list.append(change)
                real_command_list.append(change)

        for task in self.ordered_tasks:
            if task.todo not in ["get"]:
                if task.todo in ["conf", "comp"]:
                    # if self.package.kind in ["setups", "couplings"]:
                    if task.package.kind not in ["setups", "couplings"]:
                        if self.package.subpackages:
                            real_command_list.append(
                                "cp ../" + task.raw_name + "_script.sh ."
                            )
                        real_command_list.append("./" + task.raw_name + "_script.sh")
                else:
                    if task.package.command_list[task.todo] is not None:
                        for command in task.package.command_list[task.todo]:
                            real_command_list.append(command)
                if task.package.command_list[task.todo] is not None:
                    for command in task.package.command_list[task.todo]:
                        command_list.append(command)
                if task.todo == "comp":
                    if task.package.bin_names:
                        command_list.append(
                            "mkdir -p " + toplevel + "/" + task.package.bin_type
                        )
                        real_command_list.append(
                            "mkdir -p " + toplevel + "/" + task.package.bin_type
                        )
                        for binfile in task.package.bin_names:
                            # PG: Only copy if source and dest aren't the same!
                            # (Prevents cp: ‘/temp/test.txt’ and
                            # ‘/temp/test/test.txt’ are the same file)
                            if task.package.destination != toplevel:
                                command_list.append(
                                    "cp "
                                    + task.package.destination
                                    + "/"
                                    + binfile
                                    + " "
                                    + toplevel
                                    + "/"
                                    + task.package.bin_type
                                )
                                real_command_list.append(
                                    "cp "
                                    + task.package.destination
                                    + "/"
                                    + binfile
                                    + " "
                                    + toplevel
                                    + "/"
                                    + task.package.bin_type
                                )
                elif task.todo == "clean":
                    if task.package.bin_names:
                        for binfile in task.package.bin_names:
                            command_list.append(
                                "rm "
                                + toplevel
                                + "/"
                                + task.package.bin_type
                                + "/"
                                + binfile.split("/", -1)[-1]
                            )
                            real_command_list.append(
                                "rm "
                                + toplevel
                                + "/"
                                + task.package.bin_type
                                + "/"
                                + binfile.split("/", -1)[-1]
                            )
        if self.package.kind in ["setups", "couplings"]:
            command_list.append("cd ..")
            real_command_list.append("cd ..")

        return real_command_list, command_list

    def cleanup_script(self):
        try:
            os.remove("./dummy_script.sh")
        except OSError:
            print("No dummy script to remove!")
        for task in self.ordered_tasks:
            if task.todo in ["conf", "comp"]:
                try:
                    os.remove("./" + task.raw_name + "_script.sh")
                except OSError:
                    print("No file to remove for ", task.raw_name)

    def check_if_target(self, setup_info):
        if not setup_info.has_target2(self.package, self.todo):
            setup_info.output_available_targets(self.raw_name)
            sys.exit(0)

    def check_requirements(self):
        if self.will_download:
            return True
        requirements = self.folders_after_download
        for folder in requirements:
            if not os.path.isdir(folder):
                print()
                print(
                    "Missing folder "
                    + folder
                    + " detected. Please run 'make get-"
                    + self.package.raw_name
                    + "' first."
                )
                print()
                sys.exit(0)
        return True

    def validate(self):
        self.check_requirements()

    def execute(self):
        for task in self.ordered_tasks:
            if task.todo in ["conf", "comp"]:
                if task.package.kind == "components":
                    task.env.write_dummy_script()
                    newfile = task.env.add_commands(
                        task.package.command_list[task.todo], task.raw_name
                    )
                    if os.path.isfile(newfile):
                        os.chmod(newfile, 0o755)
        for command in self.command_list:
            if command.startswith("mkdir"):
                # os.system(command)
                subprocess.run(command.split(), check=True)
            elif command.startswith("cp "):
                # os.system(command)
                subprocess.run(command.split(), check=True)
            elif command.startswith("cd ") and ";" not in command:
                os.chdir(command.replace("cd ", ""))
            else:
                # os.system(command)
                for command in command.split(";"):
                    if "sed" in command:
                        command = command.replace("'", "")
                    subprocess.run(
                        command.split(),
                        check=True,
                        shell=(command.startswith("./") and command.endswith(".sh")),
                    )

    def output(self):
        print()
        subtasklist = []
        osubtasklist = []
        self.package.output()
        print("    Todo: ", self.todo)
        if self.only_subtask:
            if self.only_subtask == "NONE":
                print("    NO VALID SUBTASKS!!!")
            else:
                for subtask in self.only_subtask:
                    print("    Only Subtask:", subtask.package.raw_name)
        for subtask in self.subtasks:
            subtasklist.append(subtask.raw_name)
        for osubtask in self.ordered_tasks:
            osubtasklist.append(osubtask.raw_name)
        if not subtasklist == []:
            print("    Subtasks:", subtasklist)
        if not osubtasklist == []:
            print("    Ordered Subtasks:", osubtasklist)
        self.output_steps()
        if not self.folders_after_download == []:
            print("    The following folders should exist after download:")
            for folder in self.folders_after_download:
                print("        ", folder)
        if not self.binaries_after_compile == []:
            print("    The following files should exist after compiling:")
            for binfile in self.binaries_after_compile:
                print("        ", binfile)

    def output_steps(self):
        if not self.command_list == []:
            print("    Executing commands in this order:")
            for command in self.shown_command_list:
                print("        ", command)


