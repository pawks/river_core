# See LICENSE for details
"""Provide Utility functions for river_core"""
import sys
import os
import subprocess
import shlex
from river_core.log import logger
import distutils.util
import ruamel
import signal
from ruamel.yaml import YAML
from threading import Timer
import pathlib

yaml = YAML(typ="safe")
yaml.default_flow_style = False
yaml.allow_unicode = True


def str_2_bool(string):
    """
        Simple String to Bool conversion
        
        :param string: A string to convert

        :returns: Boolean value (True or False)
        
        :rtype: bool
    """
    return bool(distutils.util.strtobool(string))


def save_yaml(data, out_file):
    """
        Save a dict to a file

        :param data: Input data 

        :param out_file: Full/Abs path of Output file 

        :type data: dict 

        :type out_file: str 
    """
    try:
        with open(out_file, 'w') as outfile:
            ruamel.yaml.dump(data, outfile)
    except FileNotFoundError:
        logger.error("File doesn't exist")


def load_yaml(input_yaml):
    """
        Save a dict to a file

        :param input_yaml: YAML file to read 

        :type input_yaml: str 

        :returns: The loaded yaml 

        :rtype: dict
    """
    try:
        with open(input_yaml, "r") as file:
            return dict(yaml.load(file))
    except ruamel.yaml.constructor.DuplicateKeyError as msg:
        raise SystemExit


def sys_command(command, timeout=240):
    '''
        Wrapper function to run shell commands with a timeout.
        Uses :py:mod:`subprocess`, :py:mod:`shlex`, :py:mod:`os`
        to ensure proper termination on timeout

        :param command: The shell command to run.

        :param timeout: The value after which the framework exits. Default set to configured to 240 seconds

        :type command: list

        :type timeout: int

        :returns: Error Code (int) ; STDOUT ; STDERR

        :rtype: list
    '''
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
    '''
        Wrapper function to run shell commands with a timeout which involve operating with a file.
        Uses :py:mod:`subprocess`, :py:mod:`shlex`, :py:mod:`os`
        to ensure proper termination on timeout

        :param command: The shell command to run.

        :param filename: File on which the operation is performed. 

        :param timeout: The value after which the framework exits.
        Default set to configured to 240 seconds

        :type command: list

        :type filename: str 

        :type timeout: int

        :returns: Error Code (int) ; None ; None 

        :rtype: list

    '''
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


class makeUtil():
    """
    Utility for ease of use of make commands like `make` and `pmake`.
    Supports automatic addition and execution of targets. Uses the class
    :py:class:`shellCommand` to execute commands.
    """

    def __init__(self, makeCommand='make', makefilePath="./Makefile"):
        """ Constructor.

        :param makeCommand: The variant of make to be used with optional arguments.
            Ex - `pmake -j 8`

        :type makeCommand: str

        :param makefilePath: The path to the makefile to be used.

        :type makefilePath: str

        """
        self.makeCommand = makeCommand
        self.makefilePath = makefilePath
        makefile = open(makefilePath, 'w')
        makefile.close()
        self.targets = []

    def add_target(self, command, tname=""):
        """
        Function to add a target to the makefile.

        :param command: The command to be executed when the target is run.

        :type command: str

        :param tname: The name of the target to be used. If not specified, TARGET<num> is used as the name.

        :type tname: str
        """
        if tname == "":
            tname = "TARGET" + str(len(self.targets))
        with open(self.makefilePath, "a") as makefile:
            makefile.write("\n\n.PHONY : " + tname + "\n" + tname + " :\n\t" +
                           command.replace("\n", "\n\t"))
            self.targets.append(tname)

    def execute_target(self, tname, cwd="./"):
        """
        Function to execute a particular target only.

        :param tname: Name of the target to execute.

        :type tname: str

        :param cwd: The working directory to be set while executing the make command.

        :type cwd: str

        :raise AssertionError: If target name is not present in the list of defined targets.

        """
        assert tname in self.targets, "Target does not exist."
        return shellCommand(self.makeCommand + " -f " + self.makefilePath +
                            " " + tname).run(cwd=cwd)

    def execute_all(self, cwd):
        """
        Function to execute all the defined targets.

        :param cwd: The working directory to be set while executing the make command.

        :type cwd: str

        """
        return shellCommand(self.makeCommand + " -f " + self.makefilePath +
                            " " + " ".join(self.targets)).run(cwd=cwd)


class Command():
    """
    Class for command build which is supported
    by :py:mod:`suprocess` module. Supports automatic
    conversion of :py:class:`pathlib.Path` instances to
    valid format for :py:mod:`subprocess` functions.
    """

    def __init__(self, *args, pathstyle='auto', ensure_absolute_paths=False):
        """Constructor.

        :param pathstyle: Determine the path style when adding instance of
            :py:class:`pathlib.Path`. Path style determines the slash type
            which separates the path components. If pathstyle is `auto`, then
            on Windows backslashes are used and on Linux forward slashes are used.
            When backslashes should be prevented on all systems, the pathstyle
            should be `posix`. No other values are allowed.

        :param ensure_absolute_paths: If true, then any passed path will be
            converted to absolute path.

        :param args: Initial command.

        :type pathstyle: str

        :type ensure_absolute_paths: bool
        """
        self.ensure_absolute_paths = ensure_absolute_paths
        self.pathstyle = pathstyle
        self.args = []

        for arg in args:
            self.append(arg)

    def append(self, arg):
        """Add new argument to command.

        :param arg: Argument to be added. It may be list, tuple,
            :py:class:`Command` instance or any instance which
            supports :py:func:`str`.
        """
        to_add = []
        if type(arg) is list:
            to_add = arg
        elif type(arg) is tuple:
            to_add = list(arg)
        elif isinstance(arg, type(self)):
            to_add = arg.args
        elif isinstance(arg, str) and not self._is_shell_command():
            to_add = shlex.split(arg)
        else:
            # any object which will be converted into str.
            to_add.append(arg)

        # Convert all arguments to its string representation.
        # pathlib.Path instances
        to_add = [
            self._path2str(el) if isinstance(el, pathlib.Path) else str(el)
            for el in to_add
        ]
        self.args.extend(to_add)

    def clear(self):
        """Clear arguments."""
        self.args = []

    def run(self, **kwargs):
        """Execute the current command.

        Uses :py:class:`subprocess.Popen` to execute the command.

        :return: The return code of the process     .
        :raise subprocess.CalledProcessError: If `check` is set
                to true in `kwargs` and the process returns
                non-zero value.
        """
        kwargs.setdefault('shell', self._is_shell_command())
        cwd = self._path2str(kwargs.get(
            'cwd')) if not kwargs.get('cwd') is None else self._path2str(
                os.getcwd())
        kwargs.update({'cwd': cwd})
        logger.debug(cwd)
        # When running as shell command, subprocess expects
        # The arguments to be string.
        logger.debug(str(self))
        cmd = str(self) if kwargs['shell'] else self
        x = subprocess.Popen(cmd,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE,
                             **kwargs)
        out, err = x.communicate()
        out = out.rstrip()
        err = err.rstrip()
        if x.returncode != 0:
            if out:
                logger.error(out.decode("ascii"))
            if err:
                logger.error(err.decode("ascii"))
        else:
            if out:
                logger.warning(out.decode("ascii"))
            if err:
                logger.warning(err.decode("ascii"))
        return x.returncode

    def _is_shell_command(self):
        """
        Return true if current command is supposed to be executed
        as shell script otherwise false.
        """
        return any('|' in arg for arg in self.args)

    def _path2str(self, path):
        """Convert :py:class:`pathlib.Path` to string.

        The final form of the string is determined by the
        configuration of `Command` instance.

        :param path: Path-like object which will be converted
                     into string.
        :return: String representation of `path`
        """
        path = pathlib.Path(path)
        if self.ensure_absolute_paths and not path.is_absolute():
            path = path.resolve()

        if self.pathstyle == 'posix':
            return path.as_posix()
        elif self.pathstyle == 'auto':
            return str(path)
        else:
            raise ValueError(f"Invalid pathstyle {self.pathstyle}")

    def __add__(self, other):
        cmd = Command(self,
                      pathstyle=self.pathstyle,
                      ensure_absolute_paths=self.ensure_absolute_paths)
        cmd += other
        return cmd

    def __iadd__(self, other):
        self.append(other)
        return self

    def __iter__(self):
        """
        Support iteration so functions from :py:mod:`subprocess` module
        support `Command` instance.
        """
        return iter(self.args)

    def __repr__(self):
        return f'<{self.__class__.__name__} args={self.args}>'

    def __str__(self):
        return ' '.join(self.args)


class shellCommand(Command):
    """
        Sub Class of the command class which always executes commands as shell commands.
    """

    def __init__(self, *args, pathstyle='auto', ensure_absolute_paths=False):
        """
        :param pathstyle: Determine the path style when adding instance of
            :py:class:`pathlib.Path`. Path style determines the slash type
            which separates the path components. If pathstyle is `auto`, then
            on Windows backslashes are used and on Linux forward slashes are used.
            When backslashes should be prevented on all systems, the pathstyle
            should be `posix`. No other values are allowed.

        :param ensure_absolute_paths: If true, then any passed path will be
            converted to absolute path.

        :param args: Initial command.

        :type pathstyle: str

        :type ensure_absolute_paths: bool

        """
        return super().__init__(*args,
                                pathstyle=pathstyle,
                                ensure_absolute_paths=ensure_absolute_paths)

    def _is_shell_command(self):
        return True
