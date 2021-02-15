==========
ESM MASTER
==========

ESM Master tool for downloading, configuring and compiling of earth system model components and coupled setups

* Free software: GNU General Public License v2

* Download, configure, and compile various Earth System Models

Installing
----------

Please see the instructions for installation here: https://gitlab.awi.de/esm_tools/esm_tools

Example
-------

To use the command line tool ``esm_master``, just enter at a prompt::

    esm_master

The tool may ask you to configure your settings; which are stored in your home folder under ``${HOME}/.esmtoolsrc.`` A list of avaiable commands and models are printed to the screen. To download, compile, and install awicm-2.0; you can say::

    esm_master install-awicm-2.0

This will trigger a download, if needed a configuration, and a compilation process. Similarly, you can recompile with ``recomp-XXX``, clean with ``clean-XXX``, or do individual steps, e.g. get, configure, comp.
The download and installation will always occur in the current working directory.
You can get further help with::

    esm_master --help

Tab Completion
--------------
A tab completion script can be generated for the user::

    $ esm_master --generate_tab_complete
    Wrote file: esm_master_tabcomplete.bash
    Have your shell source this file to allow tab completion of available targets
    This works for both bash and zsh
    $ source esm_master_tabcomplete.bash
    $ esm_master <tab>

Voila! 🎉


Configuration
-------------

The ``esm_master`` tool is configured via YAML files, which can be found under your ``esm_tools`` directory: ``configs/esm_software/esm_master/``. This contains two files:

* ``esm-software.yaml``

* ``esm_master.yaml``

The first file stores the information on where to download different components of ``esm_tools``, while the second configures which commands the ``esm_master`` binary provides. Information on how to download specific versions of each Earth System Model can be found in ``esm_tools/configs/components/`` folder under ``choose_version`` section of YAML file specific for each model.

Credits
-------

This package was created with Cookiecutter_ and the `audreyr/cookiecutter-pypackage`_ project template.

.. _Cookiecutter: https://github.com/audreyr/cookiecutter
.. _`audreyr/cookiecutter-pypackage`: https://github.com/audreyr/cookiecutter-pypackage
