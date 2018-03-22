#!/usr/bin/python
# coding: utf-8

DOCUMENTATION = '''
---
module: mas
author:
    - "Toshiya NISHIO (@toshiya240)"
short_description: Package manager for Mac App Store
description:
    - Manage Mac App Store applications
options:
    appid:
        description:
            - identifier of application to install
        required: true
    name:
        description:
            - name of application to install
        required: false
    state:
        description:
            - state of the application
        choices: ['latest', 'present']
        required: false
        default: present
'''

EXAMPLES = '''
- mas:
  appid: 999999999
  name: foo

- mas:
  appid: 999999999
  state: present

- mas:
  appid: 999999999
  state: latest
'''

import os
import re

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.six import iteritems, string_types

# exceptions -------------------------------------------------------------- {{{
class MasException(Exception):
    pass
# /exceptions ------------------------------------------------------------- }}}

# utils ------------------------------------------------------------------- {{{
def _create_regex_group(s):
    lines = (line.strip() for line in s.split('\n') if line.strip())
    chars = filter(None, (line.split('#')[0].strip() for line in lines))
    group = r'[^' + r''.join(chars) + r']'
    return re.compile(group)
# /utils ------------------------------------------------------------------ }}}

class Mas(object):
    ''' A class to manage Mac App Store applications.'''

    # class regexes ------------------------------------------------ {{{
    VALID_MAS_PATH_CHARS = r'''
        \w                  # alphanumeric characters (i.e., [a-zA-Z0-9_])
        \s                  # spaces
        {sep}               # the OS-specific path separator
        .                   # dots
        -                   # dashes
    '''.format(sep=os.path.sep)

    VALID_PACKAGE_CHARS = r'''
        \d                  # numeric characters (i.e., [0-9])
    '''

    INVALID_MAS_PATH_REGEX = _create_regex_group(VALID_MAS_PATH_CHARS)
    INVALID_PACKAGE_REGEX  = _create_regex_group(VALID_PACKAGE_CHARS)
    # /class regexes ----------------------------------------------- }}}

    # class validations -------------------------------------------- {{{

    @classmethod
    def valid_mas_path(cls, mas_path):
        '''
        `mas_path` must be one of:
         - None
         - a string containing only:
             - alphanumeric characters
             - dashes
             - dots
             - spaces
             - os.path.sep
        '''

        if mas_path is None:
            return True

        return (
            isinstance(mas_path, string_types)
            and not cls.INVALID_MAS_PATH_REGEX.search(mas_path)
        )

    @classmethod
    def valid_package(cls, package):
        '''A valid package is either None or numeric.'''

        if package is None:
            return True

        return (
            isinstance(package, string_types)
            and not cls.INVALID_PACKAGE_REGEX.search(package)
        )

    @classmethod
    def valid_module(cls, module):
        '''A valid module is an instance of AnsibleModule.'''

        return isinstance(module, AnsibleModule)

    # /class validations ------------------------------------------- }}}

    # class properties --------------------------------------------- {{{
    @property
    def module(self):
        return self._module

    @module.setter
    def module(self, module):
        if not self.valid_module(module):
            self._module = None
            self.failed = True
            self.message = 'Invalid module: {0}.'.format(module)
            raise MasException(self.message)

        else:
            self._module = module
            return module

    @property
    def mas_path(self):
        return self._mas_path

    @mas_path.setter
    def mas_path(self, mas_path):
        if not self.valid_mas_path(mas_path):
            self._mas_path = None
            self.failed = True
            self.message = 'Invalid mas_path: {0}.'.format(mas_path)
            raise MasException(self.message)

        else:
            self._mas_path = mas_path
            return mas_path

    @property
    def current_package(self):
        return self._current_package

    @current_package.setter
    def current_package(self, package):
        if not self.valid_package(package):
            self._current_package = None
            self.failed = True
            self.message = 'Invalid package: {0}.'.format(package)
            raise MasException(self.message)

        else:
            self._current_package = package
            return package
    # /class properties -------------------------------------------- }}}

    def __init__(self, module, packages=None, state=None):
        self._setup_status_vars()
        self._setup_instance_vars(
                module=module,
                packages=packages,
                state=state, )
        self._prep()

    # prep --------------------------------------------------------- {{{
    def _setup_status_vars(self):
        self.failed = False
        self.changed = False
        self.changed_count = 0
        self.unchanged_count = 0
        self.message = ''

    def _setup_instance_vars(self, **kwargs):
        for key, val in iteritems(kwargs):
            setattr(self, key, val)

    def _prep(self):
        self._prep_mas_path()

    def _prep_mas_path(self):
        if not self.module:
            self.mas_path = None
            self.failed = True
            self.message = 'AnsibleModule not set.'
            raise MasException(self.message)

        self.mas_path = self.module.get_bin_path(
                'mas',
                required=True,
                )
        if not self.mas_path:
            self.mas_path = None
            self.failed = True
            self.message = 'Unable to locate mas executable.'
            raise MasException(self.message)

        return self.mas_path

    def _status(self):
        return (self.failed, self.changed, self.message)
    # /prep -------------------------------------------------------- }}}

    def run(self):
        try:
            self._run()
        except MasException:
            pass

        if not self.failed and (self.changed_count + self.unchanged_count > 1):
            self.message = "Changed: %d, Unchanged: %d" % (
                self.changed_count,
                self.unchanged_count,
            )
        (failed, changed, message) = self._status()

        return (failed, changed, message)

    # checks ------------------------------------------------------- {{{
    def _current_package_is_installed(self):
        if not self.valid_package(self.current_package):
            self.failed = True
            self.message = 'Invalid package: {0}.'.format(self.current_package)
            raise MasException(self.message)

        cmd = [
            "{mas_path}".format(mas_path=self.mas_path),
            "list",
        ]
        rc, out, err = self.module.run_command(cmd)
        for line in out.split('\n'):
            if line.find(self.current_package) != -1:
                return True

        return False

    def _current_package_is_outdated(self):
        if not self.valid_package(self.current_package):
            return False

        rc, out, err = self.module.run_command([
            self.mas_path,
            'outdated',
        ])
        for line in out.split('\n'):
            if line.find(self.current_package) != -1:
                return True

        return False

    # /checks ------------------------------------------------------ }}}

    # commands ----------------------------------------------------- {{{
    def _run(self):
        if self.packages:
            if self.state == 'present':
                return self._install_packages()
            elif self.state == 'latest':
                return self._upgrade_packages()

    # installed ------------------------------ {{{
    def _install_current_package(self):
        if not self.valid_package(self.current_package):
            self.failed = True
            self.message = 'Invalid package: {0}.'.format(self.current_package)
            raise MasException(self.message)

        if self._current_package_is_installed():
            self.unchanged_count += 1
            self.message = 'Package already installed: {0}'.format(
                self.current_package,
            )
            return True

        if self.module.check_mode:
            self.changed = True
            self.message = 'Package would be installed: {0}'.format(
                self.current_package
            )
            raise MasException(self.message)

        opts = (
            [self.mas_path, 'install']
            + [self.current_package]
        )
        cmd = [opt for opt in opts if opt]
        rc, out, err = self.module.run_command(cmd)

        if self._current_package_is_installed():
            self.changed_count += 1
            self.changed = True
            self.message = 'Package installed: {0}'.format(self.current_package)
            return True
        else:
            self.failed = True
            self.message = err.strip()
            raise MasException(self.message)

    def _install_packages(self):
        for package in self.packages:
            self.current_package = package
            self._install_current_package()

        return True
    # /installed ----------------------------- }}}

    # upgraded ------------------------------- {{{
    def _upgrade_current_package(self):
        if not self.valid_package(self.current_package):
            self.failed = True
            self.message = 'Invalid package: {0}.'.format(self.current_package)
            raise MasException(self.message)

        if self._current_package_is_installed() and not self._current_package_is_outdated():
            self.message = 'Package is already upgraded: {0}'.format(
                self.current_package,
            )
            self.unchanged_count += 1
            return True

        if self.module.check_mode:
            self.changed = True
            self.message = 'Package would be upgraded: {0}'.format(
                self.current_package
            )
            raise MasException(self.message)

        opts = (
            [self.mas_path, 'install']
            + [self.current_package]
        )
        cmd = [opt for opt in opts if opt]
        rc, out, err = self.module.run_command(cmd)

        if self._current_package_is_installed() and not self._current_package_is_outdated():
            self.changed_count += 1
            self.changed = True
            self.message = 'Package upgraded: {0}'.format(self.current_package)
            return True
        else:
            self.failed = True
            self.message = err.strip()
            raise MasException(self.message)

    def _upgrade_packages(self):
        for package in self.packages:
            self.current_package = package
            self._upgrade_current_package()
        return True
    # /upgraded ------------------------------ }}}
    # /commands ---------------------------------------------------- }}}

def main():
    module = AnsibleModule(
        argument_spec=dict(
            appid=dict(
                required=True,
                type='list',
            ),
            name=dict(
                required=False,
                type='list',
            ),
            state=dict(
                default="present",
                choices=[
                    "present",
                    "latest",
                ],
            )
        ),
        supports_check_mode=True,
    )

    module.run_command_environ_update = dict(LANG='C', LC_ALL='C', LC_MESSAGES='C', LC_CTYPE='C')

    p = module.params

    if p['appid']:
        packages = p['appid']

    state = p['state']

    mas = Mas(module=module, packages=packages, state=state)
    (failed, changed, message) = mas.run()
    if failed:
        module.fail_json(msg=message)
    else:
        module.exit_json(changed=changed, msg=message)


if __name__ == '__main__':
    main()
