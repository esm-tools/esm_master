######################################################################################
############################## Combine all YAMLS #####################################
######################################################################################


def combine_components_yaml():
    """
    Combines various YAML files in esm_master config directory.

    The esm_master config directory is taken from the ``.esmtoolsrc`` file as
    ``${FUNCTION_PATH}/esm_master/``. All files under the ``components``,
    ``setups``, and ``couplings`` sub-directories are read into the dictionary.

    Returns
    -------
    dict :
        A dictionary equivalent of all components, couplings, setups, and
        general information.
    """

    relevant_entries = [
            "git_repository",
            "branch",
            "tag",
            "comp_command",
            "conf_command",
            "clean_command",
            ]

    categories = ["components", "couplings", "setups"]

    relevant_dirs={ 
            "components": COMPONENTS_DIR,
            "couplings": COUPLINGS_DIR,
            "setups": SETUPS_DIR,
            }

    components_dict = {}

    for cat in categories:

        components_dict[cat] = {}
        cat_dir = relevant_dirs[cat]

        for package in os.listdir(cat_dir):
            components_dict[cat][package] = {}
            package_dir = relevant_dir + "/" + cat + "/"

            default_file = package_dir + component + ".yaml"

            versioned_files = [
                    package_dir + i 
                    for i in os.listdir(package_dir) 
                    if i.startswith("component" + "-")
                    ]

            comp_config = esm_parser.yaml_file_to_dict(default_file)
            default_version = comp_config["version"]

            package_conf = get_relevant_info(relevant_entries, comp_config)

            for conf_file in versioned_files:
                add_config = esm_parser.yaml_file_to_dict(conf_file)
                package_conf = get_relevant_info(relevant_entries, add_config, package_conf)

            components_dict[cat][package] = package_conf
            
    return components_dict[cat][package]






def get_correct_entry(in_config, out_config, entry, default = None):
        compile_tag = "compile_info"
        
        if compile_tag in in_config and entry in in_config[compile_tag]:
            out_config[entry] = in_config[compile_tag][entry]
        elif "general" in in_config and compile_tag in in_config["general"] and entry in in_config["general"][compile_tag]:
            out_config[entry] = in_config["general"][compile_tag][entry]
        elif "general" in in_config and entry in in_config["general"]:
            out_config[entry] = in_config["general"][entry]
        elif entry in in_config:
            out_config[entry] = in_config[entry]
        else:
            if default:
                out_config[entry] = default

        return out_config



def get_relevant_info(relevant_entries, raw_config, merge_into_this_config=None):

        relevant_info = {}
        for entry in relevant_entries:
            relevant_info = get_correct_entry(raw_config, relevant_info, entry)
    
        comp_config = get_correct_entry(raw_config, {}, "available_versions", raw_config["version"])
        comp_config = get_correct_entry(raw_config, comp_config, "choose_version", {"*": {}})

        if raw_config["version"] not in comp_config["choose_version"]:
            comp_config["choose_version"][raw_config["version"]] = {}

        if "*" not in comp_config["choose_version"]:
            comp_config["choose_version"]["*"] = {}

        for version in comp_config["choose_version"]:
            for entry, value in relevant_info.items():
                if not entry in comp_config["choose_version"][version]:
                    comp_config["choose_version"][version] = value

        if merge_into_this_config:
            for version in comp_config["available_versions"]:
                merge_into_this_config["available_versions"].append(version) if version not in merge_into_this_config["available_versions"]

            for version in comp_config["choose_version"]:
                if version in merge_into_this_config["choose_version"]:
                    print(f"Error: Version {version} defined two times.")
                    sys.exit(-1)
            merge_into_this_config["choose_version"].update(comp_config["choose_version"])

        else:
            merge_into_this_config = copy.deepcopy(comp_config)

        return merge_into_this_config








######################################################################################
########################### class "setup_and_model_infos" ############################
######################################################################################


class setup_and_model_infos:
    def __init__(self, vcs, general):
        self.config = combine_components_yaml()
        self.model_kinds = list(self.config.keys())
        self.meta_todos = general.meta_todos
        self.meta_command_order = general.meta_command_order
        self.display_kinds = general.display_kinds

        self.model_todos = []
        for kind in self.model_kinds:
            for model in self.config[kind].keys():
                version = None
                if "choose_versions" in self.config[kind][model]:
                    for version in self.config[kind][model]["choose_versions"]:
                        for entry in self.config[kind][model]["choose_version"][
                            version
                        ]:
                            if entry.endswith("_command"):
                                todo = entry.replace("_command", "")
                                if todo not in self.model_todos:
                                    self.model_todos.append(todo)
                for entry in self.config[kind][model]:
                    if entry.endswith("_command"):
                        todo = entry.replace("_command", "")
                        if todo not in self.model_todos:
                            self.model_todos.append(todo)

        self.known_todos = self.model_todos + vcs.known_todos + general.meta_todos
        self.all_packages = self.list_all_packages(vcs, general)
        self.update_packages(vcs, general)

        if verbose > 1:
            self.output()


    def append_to_conf(self, target, reduced_config, toplevel=""):
        (todo, kind, model, version, only_subtarget, raw) = self.split_raw_target(
            target, self
        )
        if not version:
            version = "default"

        if model in self.config[kind]:
            reduced_config[model] = self.config[kind][model]
            reduced_config[model]["version"] = version
            reduced_config[model]["kind"] = kind
            esm_parser.choose_blocks(reduced_config)
        if kind == "setups":
            toplevel = model + "-" + version
            reduced_config[model]["model_dir"] = ESM_MASTER_DIR + "/" + toplevel
            if "couplings" in self.config[kind][model]:
                for coupling in self.config[kind][model]["couplings"]:
                    reduced_config = self.append_to_conf(
                        coupling, reduced_config, toplevel
                    )
        elif kind == "couplings":
            if toplevel == "":
                toplevel = model + "-" + version
            reduced_config[model]["model_dir"] = ESM_MASTER_DIR + "/" + toplevel
            if "components" in self.config[kind][model]:
                for component in self.config[kind][model]["components"]:
                    reduced_config = self.append_to_conf(
                        component, reduced_config, toplevel
                    )
        elif kind == "components":
            sep = ""
            if toplevel == "":
                if "requires" in self.config[kind][model]:
                    toplevel = model + "-" + version
                    sep = "/"
            else:
                sep = "/"

            if "destination" in reduced_config[model]:
                reduced_config[model]["model_dir"] = (
                    ESM_MASTER_DIR
                    + "/"
                    + toplevel
                    + sep
                    + reduced_config[model]["destination"]
                )
            else:
                reduced_config[model]["model_dir"] = (
                    ESM_MASTER_DIR + "/" + toplevel + sep + model + "-" + version
                )

            if "requires" in self.config[kind][model]:
                for requirement in self.config[kind][model]["requires"]:
                    reduced_config = self.append_to_conf(
                        requirement, reduced_config, toplevel
                    )

        return reduced_config

    # def reduce(self, target, env):
    def reduce(self, target):
        blacklist = [re.compile(entry) for entry in ["computer.*"]]

        reduced_config = {}
        reduced_config["defaults"] = self.config["defaults"]
        reduced_config = self.append_to_conf(target, reduced_config)

        esm_parser.choose_blocks(reduced_config)
        esm_parser.recursive_run_function(
            [],
            reduced_config,
            "atomic",
            esm_parser.find_variable,
            reduced_config,
            blacklist,
            True,
        )

        new_config = {}
        for headline in reduced_config:
            if "kind" in reduced_config[headline]:
                if not reduced_config[headline]["kind"] in new_config:
                    new_config[reduced_config[headline]["kind"]] = {
                        headline: reduced_config[headline]
                    }
                else:
                    new_config[reduced_config[headline]["kind"]].update(
                        {headline: reduced_config[headline]}
                    )
            else:
                new_config.update({headline: reduced_config[headline]})

        # esm_parser.pprint_config(new_config)
        # sys.exit(0)
        return new_config

    def replace_last_vars(self, env):

        self.config["computer"] = copy.deepcopy(env.config)
        esm_parser.recursive_run_function(
            [], self.config, "atomic", esm_parser.find_variable, self.config, [], True,
        )

    def update_packages(self, vcs, general):
        for package in self.all_packages:
            package.fill_in_infos(self, vcs, general)

    def list_all_packages(self, vcs, general):
        packages = []
        config = self.config
        for kind in self.model_kinds:
            for model in config[kind]:
                version = None
                if "available_versions" in config[kind][model]:
                    for version in config[kind][model]["available_versions"]:
                        packages.append(
                            software_package(
                                (kind, model, version),
                                self,
                                vcs,
                                general,
                                no_infos=True,
                            )
                        )
                else:
                    packages.append(
                        software_package(
                            (kind, model, version), self, vcs, general, no_infos=True
                        )
                    )
        return packages

    def has_target(self, package, target, vcs):
        if target in self.meta_todos:
            for subtarget in self.meta_command_order[target]:
                if self.has_target(package, subtarget, vcs):
                    return True
        if target in vcs.known_todos:
            for repo in vcs.known_repos:
                answer = self.get_config_entry(package, repo + "-repository")
                if answer:
                    return True
        else:
            answer = self.get_config_entry(package, target + "_command")
            if answer:
                return True
        return False

    def has_target2(self, package, target):
        for testpackage in self.all_packages:
            if (
                testpackage.raw_name == package.raw_name
                and target in testpackage.targets
            ):
                return True
        return False

    def has_package(self, package):
        if package in self.all_packages:
            return True
        else:
            return False

    def has_model(self, model):
        for kind in self.model_kinds:
            for test_model in self.config[kind]:
                if test_model == model:
                    return True
        return False

    def split_raw_target(self, rawtarget, setup_info):
        todo = kind = only_subtarget = None
        model = version = ""
        if "/" in rawtarget:
            rawtarget, only_subtarget = rawtarget.rsplit("/", 1)

        raw = rawtarget
        for this_todo in setup_info.known_todos:
            if rawtarget == this_todo:
                return this_todo, None, None, None, None, raw
            elif rawtarget.startswith(this_todo + "-"):
                todo = this_todo
                rawtarget = rawtarget.replace(todo + "-", "")
                break

        for package in self.all_packages:
            if package.raw_name == rawtarget:
                return (
                    todo,
                    package.kind,
                    package.model,
                    package.version,
                    only_subtarget,
                    raw,
                )

        # package not found:
        self.output_available_targets(rawtarget)
        sys.exit(0)

    def assemble_raw_name(self, todo, kind, model, version):
        raw = sep = ""
        if todo:
            raw = todo
            sep = "-"
        if model:
            raw = raw + sep + model
            sep = "-"
        if version:
            raw = raw + sep + version
            sep = "-"
        if not raw == "":
            return raw
        return None

    def setup_or_model(self, model):
        kind_of_model = "unknown"
        for kind in self.model_kinds:
            if model in self.config[kind]:
                kind_of_model = kind
        return kind_of_model

    def output_available_targets(self, search_keyword):
        display_info = []
        if search_keyword == "":
            display_info = self.all_packages
        else:
            for package in self.all_packages:
                if package.targets:
                    for target in package.targets:
                        if search_keyword in target + "-" + package.raw_name:
                            if package not in display_info:
                                display_info.append(package)

        if display_info == []:
            print()
            print(
                "No targets found for keyword "
                + search_keyword
                + ". Type 'esm_master' to get a full list"
            )
            print("of available targets.")
            print()
        elif display_info == self.all_packages:
            print()
            print(
                "Master Tool for ESM applications, including download and compiler wrapper functions"
            )
            print("		originally written by Dirk Barbi (dirk.barbi@awi.de)")
            print(
                "       further developed as OpenSource, coordinated and maintained at AWI"
            )
            print()
            print(
                "Obtain from:         https://gitlab.dkrz.de/esm-tools/esm-master.git"
            )
            print()
            self.print_nicely(display_info)
            print()
        else:
            print()
            print(
                search_keyword
                + " is not an available target. Did you mean one of those:"
            )
            self.print_nicely(display_info)
            print()

    def print_nicely(self, display_info):
        sorted_display = {}
        for kind in self.display_kinds:
            for package in display_info:
                if package.kind == kind:
                    if not kind in sorted_display.keys():
                        sorted_display.update({kind: {}})
                    if not package.model in sorted_display[kind]:
                        sorted_display[kind].update({package.model: []})
                    if package.version:
                        sorted_display[kind][package.model].append(
                            package.version + ": " + str(package.targets)
                        )
                    else:
                        sorted_display[kind][package.model].append(str(package.targets))

        for kind in sorted_display.keys():
            print(kind + ": ")
            for model in sorted_display[kind]:
                if len(sorted_display[kind][model]) == 1:
                    print("    " + model + ": " + sorted_display[kind][model][0])
                else:
                    print("    " + model + ": ")
                    for version in sorted_display[kind][model]:
                        print("       " + version)

    def get_config_entry(self, package, entry):
        try:
            answer = self.config[package.kind][package.model]["choose_version"][
                package.version
            ][entry]
        except:
            try:
                answer = self.config[package.kind][package.model][entry]
            except:
                answer = None
        return answer

    def output(self):
        print()
        print("Model kinds: " + str(self.model_kinds))
        print("Model todos: " + str(self.model_todos))
        print("All known todos: " + str(self.known_todos))
        for package in self.all_packages:
            package.output()
