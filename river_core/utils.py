# See LICENSE for details
"""Provide Utility functions for river_core"""
import sys
import os
import subprocess
import shlex
from river_core.log import logger
import ruamel
import signal
from ruamel.yaml import YAML
from threading import Timer


def sys_command(command, timeout=240):
    '''
        Wrapper function to run shell commands with a timeout.
        Uses :py:mod:`subprocess`, :py:mod:`shlex`, :py:mod:`os`
        to ensure proper termination on timeout

        :param command: The shell command to run.

        :param timeout: The value after which the framework exits.
        Default set to configured to 240 seconds

        :type file1: list

        :type file2: int

        :return: Error Code (int) ; STDOUT ; STDERR

    '''
    # test = 'exec ' + command
    # logger.debug(test)
    logger.warning('$ timeout={1} {0} '.format(' '.join(shlex.split(command)),
                                               timeout))
    out = ''
    err = ''
    with subprocess.Popen(shlex.split(command),
                          stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE,
                          start_new_session=True) as process:
        try:
            out, err = process.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            process.kill()
            pgrp = os.getpgid(process.pid)
            os.killpg(pgrp, signal.SIGTERM)
            return 1, "GuruMeditation", "TimeoutExpired"

    # timer = Timer(timeout, process.kill)
    # try:
    #     timer.start()
    #     out, err = process.communicate()
    # finally:
    #     timer.cancel()

    #eprocess.ept subprocess.TimeoutExpired:
    #    process.kill()
    #    out, err = process.communicate()

    # out = process.stdout
    # err = process.stderr

    out = out.rstrip()
    err = err.rstrip()
    if process.returncode != 0:
        if out:
            logger.error(out.decode("ascii"))
        if err:
            logger.error(err.decode("ascii"))
    else:
        if out:
            logger.debug(out.decode("ascii"))
        if err:
            logger.debug(err.decode("ascii"))
    return (process.returncode, out.decode("ascii"), err.decode("ascii"))


def sys_command_file(command, filename, timeout=500):
    cmd = command.split(' ')
    cmd = [x.strip(' ') for x in cmd]
    cmd = [i for i in cmd if i]
    logger.warning('$ {0} > {1}'.format(' '.join(cmd), filename))
    fp = open(filename, 'w')
    x = subprocess.Popen(cmd, stdout=fp, stderr=fp)
    timer = Timer(timeout, x.kill)
    try:
        timer.start()
        stdout, stderr = x.communicate()
    finally:
        timer.cancel()

    fp.close()

    return (x.returncode, None, None)
