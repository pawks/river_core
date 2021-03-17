# See LICENSE file for details
""" Main file containing all necessary functions of river_core """
import sys
import os
import shutil
import datetime
import importlib
import configparser
import filecmp
import json

from river_core.log import *
import river_core.utils as utils
from river_core.constants import *
from river_core.__init__ import __version__
from river_core.sim_hookspecs import *
# import riscv_config.checker as riscv_config
# from riscv_config.errors import ValidationError
from envyaml import EnvYAML
from jinja2 import Template

# TODO List:
# [ ] Improve logging errors


# Misc Helper Functions
def generate_report(output_dir, json_data, config, log_cmp_status):
    '''
        Work in Progress

        Function to create an HTML report from the JSON files generated by individual plugins

        :param output_dir: Output directory for programs generated

        :param json_list: JSON List exported from the plugins ; (Optional)

        :param config: Config ini with the loaded by the configparser module

        :type output_dir: str

        :type json_data: st

        :type config: list

    '''

    #TODO:NEEL: This report is currently useless. Need pass fail results per
    #test. Why not send the test_list here and print the info

    # Filter JSON files
    final_data = []
    ## Remove the initial info
    for json_row in json_data:
        # NOTE: Playing with fire here, pytest developers could (potentially) change this
        if json_row.get('$report_type', None) == 'TestReport':
            final_data.append(json_row)
    json_data = final_data
    ## Get the proper stats about passed and failed test
    # NOTE: This is the place where you determine when your test passed fail, just add extra things to compare in the if condition if the results become to high
    num_passed = num_total = 0
    for json_row in json_data:
        if json_row.get('when', None) == 'call':
            num_total = num_total + 1
        if json_row.get('outcome', None) == 'passed' and json_row.get(
                'when', None) == 'call':
            num_passed = num_passed + 1

    num_failed = num_total - num_passed

    # DONE:NEEL The below should be constants in constants.py with automatic
    # absolute path detection. Please check riscof for this.
    root = os.path.abspath(os.path.dirname(__file__))
    str_report_template = root + '/templates/report.html'
    str_css_template = root + '/templates/style.css'
    report_file_name = 'report_{0}.html'.format(
        datetime.datetime.now().strftime("%Y%m%d-%H%M"))
    report_dir = output_dir + '/reports/'
    # TODO: WIP still finalizing the template
    # - [X] Shutil to copy style.css
    html_objects = {}
    html_objects['name'] = "RiVer Core Verification Report"
    html_objects['date'] = (datetime.datetime.now().strftime("%d-%m-%Y"))
    html_objects['time'] = (datetime.datetime.now().strftime("%H:%M"))
    html_objects['version'] = __version__
    html_objects['isa'] = config['river_core']['isa']
    html_objects['dut'] = config['river_core']['target']
    html_objects['generator'] = config['river_core']['generator']
    html_objects['reference'] = config['river_core']['reference']
    html_objects['diff_result'] = log_cmp_status
    html_objects['results'] = json_data
    html_objects['num_passed'] = num_passed
    html_objects['num_failed'] = num_failed
    if not os.path.exists(report_dir):
        os.makedirs(report_dir)

    with open(str_report_template, "r") as report_template:
        template = Template(report_template.read())

    output = template.render(html_objects)

    shutil.copyfile(str_css_template, report_dir + 'style.css')

    report_file_path = report_dir +'/' + report_file_name
    with open(report_file_path, "w") as report:
        report.write(output)

    logger.info(
        'Final report saved at {0}\nMay the debugging force be with you!'.
        format(report_file_path))


def confirm():
    """
    Ask user to enter Y or N (case-insensitive).
    :return: True if the answer is Y.
    :rtype: bool
    """
    answer = ""
    while answer not in ["y", "n"]:
        answer = input("Type [Y/N] to continue execution ? ").lower()
    return answer == "y"


def rivercore_clean(config_file, verbosity):
    '''
        Alpha
        Work in Progress

    '''

    config = configparser.ConfigParser()
    config.read(config_file)
    output_dir = config['river_core']['work_dir']
    logger.level(verbosity)
    logger.info('****** RiVer Core {0} *******'.format(__version__))
    logger.info('****** Cleaning Mode ****** ')
    logger.info('Copyright (c) 2021, InCore Semiconductors Pvt. Ltd.')
    logger.info('All Rights Reserved.')

    suite = config['river_core']['generator']
    target = config['river_core']['target']
    ref = config['river_core']['reference']

    if not os.path.exists(output_dir):
        logger.info(output_dir + ' directory does not exist. Nothing to delete')
        return
    else:
        logger.info('The following directory will be removed : ' +str(output_dir))
        logger.info('Hope you took a backup of the reports')
        res = confirm()
        if res:
            shutil.rmtree(output_dir)
            logger.info(output_dir + ' directory deleted')



def rivercore_generate(config_file, verbosity):
    '''
        Function to generate the assembly programs using the plugin as configured in the config.ini.

        :param config_file: Config.ini file for generation

        :param output_dir: Output directory for programs generated

        :param verbosity: Verbosity level for the framework

        :type config_file: click.Path

        :type output_dir: click.Path

        :type verbosity: str
    '''

    logger.level(verbosity)
    config = configparser.ConfigParser()
    config.read(config_file)
    logger.debug('Read file from {0}'.format(config_file))

    output_dir = config['river_core']['work_dir']

    logger.info('****** RiVer Core {0} *******'.format(__version__))
    logger.info('Copyright (c) 2021, InCore Semiconductors Pvt. Ltd.')
    logger.info('All Rights Reserved.')
    logger.info('****** Generation Mode ****** ')

    # TODO Test multiple plugin cases
    # Current implementation is using for loop, which might be a bad idea for parallel processing.

    suite_list = config['river_core']['generator'].split(',')
    for suite in suite_list:

        generatorpm = pluggy.PluginManager("generator")
        generatorpm.add_hookspecs(RandomGeneratorSpec)

        path_to_module = config['river_core']['path_to_suite']
        plugin_suite = suite + '_plugin'

        # Get ISA and pass to plugin
        isa = config['river_core']['isa']
        config[suite]['isa'] = isa
        logger.info('Now loading {0} Suite'.format(suite))
        abs_location_module = path_to_module + '/' + plugin_suite + '/' + plugin_suite + '.py'
        logger.debug("Loading module from {0}".format(abs_location_module))
        # generatorpm_name = 'river_core.{0}_plugin.{0}_plugin'.format(suite)
        try:
            generatorpm_spec = importlib.util.spec_from_file_location(
                plugin_suite, abs_location_module)
            generatorpm_module = importlib.util.module_from_spec(
                generatorpm_spec)
            generatorpm_spec.loader.exec_module(generatorpm_module)

        except FileNotFoundError as txt:
            logger.error(suite + " not found at : " + path_to_module + ".\n" +
                         str(txt))
            raise SystemExit

        # TODO:NEEL: I don't like this hard-coding below. Everything should come
        # from config.ini or the names should be consistant for autodetection.

        #TODO:NEEL isa fields should not be local to plugins. They have to be
        #common for all plugins

        if suite == 'microtesk':
            generatorpm.register(generatorpm_module.MicroTESKPlugin())
        if suite == 'aapg':
            generatorpm.register(generatorpm_module.AapgPlugin())
        if suite == 'dv':
            generatorpm.register(generatorpm_module.RiscvDvPlugin())

        generatorpm.hook.pre_gen(spec_config=config[suite],
                                 output_dir='{0}/{1}'.format(output_dir, suite))
        test_list = generatorpm.hook.gen(
            gen_config='{0}/{1}_plugin/{1}_gen_config.yaml'.format(
                path_to_module, suite),
            module_dir=path_to_module,
            output_dir=output_dir)
        generatorpm.hook.post_gen(
            output_dir='{0}/{1}'.format(output_dir, suite),
            regressfile='{0}/{1}/regresslist.yaml'.format(output_dir, suite))

        test_list_file = output_dir + '/test_list.yaml'
        testfile = open(test_list_file, 'w')
        utils.yaml.dump(test_list[0],
                       testfile)
        testfile.close()

        logger.info('Test list is generated and available at {0}'.format(
            test_list_file))


def rivercore_compile(config_file, test_list, coverage, verbosity):
    '''
        Work in Progress

        Function to compile generated assembly programs using the plugin as configured in the config.ini.

        :param config_file: Config.ini file for generation

        :param output_dir: Output directory for programs generated

        :param test_list: Test List exported from generate sub-command 

        :param coverage: Enable coverage merge and stats from the reports 

        :param verbosity: Verbosity level for the framework

        :type config_file: click.Path

        :type output_dir: click.Path

        :type test_list: click.Path

        :type verbosity: str
    '''

    logger.level(verbosity)
    config = configparser.ConfigParser()
    config.read(config_file)
    logger.debug('Read file from {0}'.format(config_file))

    logger.info('****** RiVer Core {0} *******'.format(__version__))
    logger.info('Copyright (c) 2021, InCore Semiconductors Pvt. Ltd.')
    logger.info('All Rights Reserved.')
    logger.info('****** Compilation Mode ******')

    #TODO:NEEL: Worthwhile to print some useful config values like work_dir,
    # isa, etc here as logger.info output

    if coverage:
        logger.info("Coverage mode is enabled")
        logger.info("Just a reminder to ensrue that you have installed things with coverage enabled")

    output_dir = config['river_core']['work_dir']
    asm_gen = config['river_core']['generator']
    target_list = config['river_core']['target'].split(',')
    # Load coverage stats
    if coverage:
        coverage_config = config['coverage']
    else:
        coverage_config = None
    if '' in target_list:
        logger.info('No targets configured, so moving on the reference')
    else:
        for target in target_list:

            # compilepm = pluggy.PluginManager('compile')
            dutpm = pluggy.PluginManager('dut')
            # compilepm.add_hookspecs(CompileSpec)
            dutpm.add_hookspecs(DuTSpec)

            isa = config['river_core']['isa']
            config[target]['isa'] = isa
            path_to_module = config['river_core']['path_to_target']
            plugin_target = target + '_plugin'
            logger.info('Now running on the Target Plugins')
            logger.info('Now loading {0}-target'.format(target))

            abs_location_module = path_to_module + '/' + plugin_target + '/' + plugin_target + '.py'
            logger.debug("Loading module from {0}".format(abs_location_module))

            dutpm_spec = importlib.util.spec_from_file_location(
                plugin_target, abs_location_module)
            dutpm_module = importlib.util.module_from_spec(dutpm_spec)
            dutpm_spec.loader.exec_module(dutpm_module)

            # DuT Plugins
            # TODO:NEEL: I don't like this hard-coding below. Everything should come
            # from config.ini or the names should be consistant for autodetection.
            if target == 'chromite_verilator' or 'chromite_cadence' or 'chromite_questa' :
                dutpm.register(dutpm_module.ChromitePlugin())
                # NOTE: Add more plugins here :)
            else:
                logger.error(
                    "Sorry, requested plugin is not really supported ATM")
                raise SystemExit

            dutpm.hook.init(ini_config=config[target],
                            test_list=test_list,
                            work_dir=output_dir,
                            coverage_config=coverage_config)
            dutpm.hook.build()
            target_json = dutpm.hook.run(module_dir=path_to_module)
            target_log = dutpm.hook.post_run()

    ref_list = config['river_core']['reference'].split(',')
    if '' in ref_list:
        logger.info('No references, so exiting the framework')
        raise SystemExit
    else:
        for ref in ref_list:

            # compilepm = pluggy.PluginManager('compile')
            dutpm = pluggy.PluginManager('dut')
            # compilepm.add_hookspecs(CompileSpec)
            dutpm.add_hookspecs(DuTSpec)

            path_to_module = config['river_core']['path_to_ref']
            plugin_ref = ref + '_plugin'
            logger.info('Now loading {0}-target'.format(ref))
            # Get ISA from river
            isa = config['river_core']['isa']
            config[ref]['isa'] = isa

            abs_location_module = path_to_module + '/' + plugin_ref + '/' + plugin_ref + '.py'
            logger.debug("Loading module from {0}".format(abs_location_module))

            dutpm_spec = importlib.util.spec_from_file_location(
                plugin_ref, abs_location_module)
            dutpm_module = importlib.util.module_from_spec(dutpm_spec)
            dutpm_spec.loader.exec_module(dutpm_module)

            # DuT Plugins
            # TODO:NEEL: I don't like this hard-coding below. Everything should come
            # from config.ini or the names should be consistant for autodetection.
            if ref == 'spike':
                dutpm.register(dutpm_module.SpikePlugin())
                # NOTE: Add more plugins here :)
            else:
                logger.error(
                    "Sorry, requested plugin is not really supported ATM")
                raise SystemExit

            dutpm.hook.init(ini_config=config[ref],
                            test_list=test_list,
                            work_dir=output_dir,
                            coverage_config=coverage_config)  
            dutpm.hook.build()
            ref_json = dutpm.hook.run(module_dir=path_to_module)
            ref_log = dutpm.hook.post_run()

        ## Comparing Dumps

        result = 'Unavailable'
        test_dict = utils.load_yaml(test_list) 
        for test, attr in test_dict.items():
            test_wd = attr['work_dir']
            if not os.path.isfile(test_wd+'/dut.dump'):
                logger.error('Dut dump for Test: {0} is missing'.format(test))
                continue
            if not os.path.isfile(test_wd+'/ref.dump'):
                logger.error('Ref dump for Test: {0} is missing'.format(test))
                continue
            result = filecmp.cmp(test_wd+'/dut.dump', test_wd+'/ref.dump')
            if not result:
                logger.error(
                    "Dumps for test {0}. Do not match. TEST FAILED".format(test))
            else:
                logger.info(
                    "Dumps for test {0} Match. TEST PASSED".format(test))

        # TODO:NEEL: I have replaced the below with the above. The dumps shuold
        # always be dut.dump and ref.dump. Will come back to this when multiple
        # dumps need to be checked. If you agree delete the below code.

        # Start comparison between files
        # TODO Replace with a signature based model
#        if '' in ref_log[0] or '' in target_log[
#                0] or not ref_log[0] or not target_log[0]:
#            logger.error(
#                'Files don\'t seem to exist ; Expect more errors on the way')
#        # TODO Improve error catching here
#        # Check if the logs are same number
#        logger.info('Starting comparison between logs')
#        result = 'Unavailable'
#        if len(ref_log[0]) == len(target_log[0]):
#            for i in range(len(ref_log)):
#                # NOTE This is absolutely strange! Why is a double list is created
#                result = filecmp.cmp(ref_log[0][i], target_log[0][i])
#                logger.info(
#                    "Matching {0} and {1} \n Result : Are files same?: {2}".
#                    format(ref_log[i], target_log[i], result))
#        else:
#            logger.info(
#                'Something is not right with the logs, manual inspection is reccomended, after program termination'
#            )

        # Start checking things after running the commands
        # Report generation starts here
        # Target
        # Move this into a function
        if not target_json[0] or not ref_json[0]:
            logger.error(
                'JSON files not available exiting\nPossible reasons:\n1. Pytest crashed internally\n2. Log files are were not returned by the called plugin.\nI\'m sorry, no HTML reports for you :('
            )
            raise SystemExit

        json_file = open(target_json[0] + '.json', 'r')
        # NOTE Ignore first and last lines cause; Fails to load the JSON
        # target_json_list = json_file.readlines()[1:-1]
        # json_file.close()
        target_json_list = json_file.readlines()
        json_file.close()
        target_json_data = []
        for line in target_json_list:
            target_json_data.append(json.loads(line))

        json_file = open(ref_json[0] + '.json', 'r')
        # NOTE Ignore first and last lines cause; Fails to load the JSON
        # ref_json_list = json_file.readlines()[1:-1]
        # json_file.close()
        ref_json_list = json_file.readlines()
        json_file.close()
        ref_json_data = []
        for line in ref_json_list:
            ref_json_data.append(json.loads(line))

        json_data = target_json_data + ref_json_data
        logger.info("Now generating some good HTML reports for you")
        generate_report(output_dir, json_data, config, result)
