# See LICENSE for details

import importlib
import sys

import pluggy

gen_hookspec = pluggy.HookspecMarker("generator")
dut_hookspec = pluggy.HookspecMarker("dut")


class RandomGeneratorSpec(object):
    """ Test generator specification"""

    @gen_hookspec
    def pre_gen(self, spec_config, output_dir):
        """ 
        This stage is used to configure the generator, check and install
        dependencies, download artifacts, create necessary directories, parse and capture the plugin 
        specific parameters present in the ``config.ini``  etc. 
        Before random generation of ASM begins

        :param spec_config: Plugin specific paramters and general parameters captured from the original input `config.ini` 

        :param output_dir:  absolute path of the ``work_dir`` where the tests and artifacts need to be generated/placed

        :type spec_config: dict 

        :type output_dir: str 
        """

    @gen_hookspec
    def gen(self, module_dir, output_dir):
        """ 
        This stage is where the actual tests are generated. RIVER CORE uses
        the inherent pytest framework to run parallelized commands. Using pytest,
        enables using default report templates which are quite verbose and helpful in
        debugging as well. 

        The major output of this stage is a test-list YAML which
        follows the syntax/schema mentioned in :ref:`Test List Format<testlist>`.
        this test list capture all the information about the test and necessary
        collaterals required to compile each test. By adopting a standard test-list 
        format, we inherently allow any source of tests to be integrated into RIVER 
        CORE as a generator plugin as long as a valid test list is created.

        :param module_dir:  absolute path of the module directory

        :param output_dir:  absolute path of the ``work_dir`` where the tests and artifacts need to be generated/placed

        :type module_dir: str 

        :type output_dir: str 

        :return: Test List basically containing the info about the tests generated and required compiler options as per the Test List Format

        :rtype: dict
        """

    @gen_hookspec
    def post_gen(self, output_dir):
        """ 
        This stage is called after all the tests are generated and can
        be used to post-process the tests, validate the tests, profile the tests, remove
        unwanted artifacts, etc.

        :param output_dir:  absolute path of the ``work_dir`` where the tests and artifacts need to be generated/placed

        :type output_dir: str 
        """


### creation of regress list into parameterize of tests: D
### simulate_test fixture in pytest calls compilespec plugin and model plugin and dut plugin
# DUT Class Specification
class DuTSpec(object):
    """ DuT plugin specification"""

    @dut_hookspec
    def init(self, ini_config, test_list, work_dir, coverage_config,
             plugin_path):
        """ 
        This stage is used to capture configurations from the input ``config.ini`` and build
        and set up the environment. If a core generator is the target, then this stage can be used to
        configure it and generate and instance, build the relevant toolchain, setup simulator args like
        coverage, verbosity, etc. The test list is also available at this stage. Which must be captured and
        stored by the plugin for future use.

        :param ini_config: Plugin specific configuration dictionary. 

        :param test_list: Path to the Test List YAML generated by Generator Plugin 

        :param work_dir: Path to the file where the output (files, logs, binaries, etc.) will be generated  

        :param coverage_config: Configuration options for coverage. 

        :param plugin_path: Path to the plugin module to be loaded  

        :type ini_config: dict 

        :type test_list: str  

        :type work_dir: str  

        :type coverage_config: dict 

        :type plugin_path: str  

        """

    @dut_hookspec
    def build(self):
        """ This stage is used to create a Makefile or script to actually compile each test,
   simulate it on the target. A typical use case is to create a makefile-target for each test
   that needs to be run on the target.
        """

    @dut_hookspec
    def run(self, module_dir):
        """ 
        This stage is used to run the tests on the DUT. It is recommended to run the tests in
        parallel. RIVER CORE uses the inherent pytest framework to run terminal commands in parallel
        fashion. This stage will generate all the artifacts of the simulation like : signature file, 
        execution logs, test-binary, target executable binary, coverage database, simulation logs, etc.

        :param module_dir: Path to the module to be loaded. 

        :type module_dir: str 

        :return: Location of the JSON report generated by Pytest used for the final HTML report.

        :rtype: str
        """

    @dut_hookspec
    def post_run(self, test_dict, config):
        """ 
        This stage is run after the pass-fail results have been captured. This stage can be
        used to clean up unwanted artifacts like : elfs, hexfiles, objdumps, logs, etc which are no
        longer of consequence. One can further choose to only delete artifacts of passed tests and retain
        it for tests that failed (the pass/fail result is captured in the test-list itself). 

        This stage can also further also be used to merge coverage databases of all the test runs, rank
        the tests and generate appropriate reports. This is completely optional and upto the user to
        define what happens as a "clean-up" process in this stage.

        :param test_dict: The test-list YAML 

        :param config: Config.ini configuration options 

        :type test_dict: dict 

        :type config: dict 

        """

    @dut_hookspec
    def merge_db(self, db_files, output_db, config):
        """ Merging different databases together 
            
            :param db_files: List of coverage files detected. 

            :param output_db: Final output name 

            :param config: Config file for RiVerCore

            :type db_files: list 

            :type output_db: str 

            :type config: str 

            :return: HTML files generated by merge 

            :rtype: list 
            """
