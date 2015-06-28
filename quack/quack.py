#!/usr/bin/env python

"""Quack!!"""

import argparse
import git
import os
import shutil
import subprocess
import types
import yaml


_PARSER = argparse.ArgumentParser(description='Quack builder')
_PARSER.add_argument(
    '-y', '--yaml', help='Provide custom yaml. default: quack.yaml')
_PARSER.add_argument(
    '-p', '--profile', help='Run selected profile. default: init', nargs='?')
_ARGS = _PARSER.parse_args()


def _remove_dir(directory):
    """Remove directory."""
    if os.path.exists(directory):
        shutil.rmtree(directory)
        return True
    return False


def _create_dir(directory):
    """Create directory."""
    if not os.path.exists(directory):
        os.makedirs(directory)


def _get_config():
    """Return yaml configuration."""
    yaml_file = _ARGS.yaml or 'quack.yaml'
    with open(yaml_file) as file_pointer:
        return yaml.load(file_pointer)
    return {}


def _fetch_modules(config, specific_module=None):
    """Fetch git submodules."""
    modules = '.quack/modules'
    ignore_list = []
    _remove_dir('.git/modules/.quack')
    _create_dir(modules)
    if os.path.isfile('.gitignore'):
        with open('.gitignore', 'r') as file_pointer:
            ignore_list = list(set(file_pointer.read().split('\n')))
    repo = git.Repo('.')
    for module in config.get('modules').items():
        if specific_module and specific_module != module[0]:
            continue
        _remove_dir(module[0])
        print 'Cloning:', module[1]['repository']
        sub_module = repo.create_submodule(
            module[0], modules + '/' + module[0],
            url=module[1]['repository'],
            branch=module[1].get('branch', 'master')
        )

        if module[1].get('hexsha'):
            subprocess.call(
                ['git', 'checkout', '--quiet', module[1].get('hexsha')],
                cwd=modules + '/' + module[0])
            hexsha = ' (' + module[1].get('hexsha') + ')'
        else:
            hexsha = ' (' + sub_module.hexsha + ')'
        print '\033[1A' + '  Cloned:', module[0] + hexsha
        print '\033[1A' + '\033[32m' + u'\u2713' + '\033[37m'

        path = module[1].get('path', '')
        from_path = '%s/%s/%s' % (modules, module[0], path)
        is_exists = os.path.exists(from_path)
        if (path and is_exists) or not path:
            shutil.copytree(
                from_path, module[0],
                ignore=shutil.ignore_patterns('.git*'))
        elif not is_exists:
            print '%s folder does not exists. Skipped.' % path

        # Remove submodule.
        sub_module.remove()
        if os.path.isfile('.gitmodules'):
            subprocess.call('rm .gitmodules'.split())
            subprocess.call('git rm --quiet --cached .gitmodules'.split())

        with open('.gitignore', 'a') as file_pointer:
            if module[0] not in ignore_list:
                file_pointer.write('\n' + module[0])
                ignore_list.append(module[0])


def _clean_modules(config, specific_module=None):
    """Remove all given modules."""
    for module in config.get('modules').items():
        if specific_module and specific_module != module[0]:
            continue
        if _remove_dir(module[0]):
            print 'Cleaned', module[0]


def _run_dependencies(dependency):
    """Execute all required dependencies."""
    if not dependency:
        return
    quack = dependency[1].get('quack')
    slash_index = quack.rfind('/')
    command = ['quack']
    if slash_index == -1:
        print '..' + quack
        git.Repo.init(quack)
        subprocess.call(command, cwd=quack)
        _remove_dir(quack + '/.git')
    elif slash_index > 0:
        module = quack[:slash_index]
        colon_index = quack.find(':')
        if len(quack) > colon_index + 1:
            command.append('-p')
            command.append(quack[colon_index + 1: len(quack)])
        if colon_index > 0:
            command.append('-y')
            command.append(quack[slash_index + 1:colon_index])
        print '..' + module
        git.Repo.init(module)
        subprocess.call(command, cwd=module)
        _remove_dir(module + '/.git')
    print


def _run_tasks(config, profile):
    """Run given tasks."""
    dependencies = profile.get('dependencies', {})
    if isinstance(dependencies, types.DictionaryType):
        for dependency in profile.get('dependencies', {}).items():
            _run_dependencies(dependency)
    tasks = profile.get('tasks', [])
    for command in tasks:
        is_negate = command[0] == '-'
        if is_negate:
            command = command[1:]
        command = command + ':'
        module = None
        is_modules = False
        if 'modules:' in command:
            module = command.replace('modules:', '')
            module = module[0: len(module) - 1]
            is_modules = True

        if is_modules and not is_negate:
            _fetch_modules(config, module)
        elif is_modules and is_negate:
            _clean_modules(config, module)


def main():
    """Entry point."""
    _create_dir('.quack')
    config = _get_config()
    if not _ARGS.profile:
        _ARGS.profile = 'init'
    profile = config.get('profiles', {}).get(_ARGS.profile, {})
    # print _ARGS.profile, profile
    _run_tasks(config, profile)

if __name__ == '__main__':
    main()