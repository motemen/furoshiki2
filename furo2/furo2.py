#!/usr/bin/env python3
# coding: utf-8

import getpass
import json
import os
import os.path
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from . import version

logs_dir = os.getenv('FURO_LOGS_DIR') or '~/.furo2/logs'


def get_logs_repo():
    logs_repo = os.getenv('FURO_LOGS_REPOSITORY')
    if not logs_repo:
        raise Exception('FURO_LOGS_REPOSITORY not set')
    return logs_repo


def script_command(out_file, command):
    if sys.platform == 'darwin':
        return script_command_darwin(out_file, command)
    elif sys.platform == 'linux':
        return script_command_linux(out_file, command)
    else:
        raise 'platform not supported: %s' % sys.platform


def script_command_linux(out_file, command):
    escaped_command = [shlex.quote(c) for c in command]
    return ['script', '--quiet', '--command',
            'sh -c "%s"' % ' '.join(escaped_command), out_file]


def script_command_darwin(out_file, command):
    return ['script', '-q', out_file] + command


def git(args, **kwargs):
    if os.getenv('FURO_DEBUG'):
        sys.stderr.write('>>> RUN %s\n' % (['git'] + args))
    subprocess.check_call(['git'] + args, **kwargs)


def git_output(args, **kwargs):
    if os.getenv('FURO_DEBUG'):
        sys.stderr.write('>>> RUN %s\n' % (['git'] + args))
    return subprocess.check_output(['git'] + args, **kwargs).decode()


def _init_project():
    root_dir = git_output(['rev-parse', '--show-toplevel']).strip()
    project_file = Path(root_dir) / 'project.yml'

    repository = git_output(['config', 'remote.origin.url']).strip()
    repo_path = re.sub(r'^https?://|\.git$', '', repository)
    repo_path = re.sub(
        r'^[a-zA-Z0-9_]+@([a-zA-Z0-9._-]+):(.*)$', r'\1/\2', repo_path)

    project_path = None
    if project_file.exists():
        import yaml
        with project_file.open('r') as f:
            project_config = yaml.safe_load(f)
            project_path = project_config.get('project')

    if not project_path:
        project_path = repo_path

    project_logs_dir = Path(os.path.expanduser(logs_dir)) / project_path

    return repo_path, project_path, project_logs_dir


def command_exec(command):
    if len(command) == 0:
        raise UsageError()

    repo_path, project_path, project_logs_dir = _init_project()

    log_file = project_logs_dir / \
        datetime.now().strftime('%Y/%m/%d/%H%M%S.%f.log')

    git_revision = git_output(['rev-parse', 'HEAD']).strip()

    temp_file = Path(tempfile.NamedTemporaryFile(
        prefix='furo2', delete=False).name)

    os.environ['FURO'] = '1'
    if os.getenv('FURO_DEBUG'):
        sys.stderr.write('>>> RUN %s\n' % command)
    return_code = subprocess.call(
        script_command(str(temp_file), command))

    if not log_file.parent.exists():
        log_file.parent.mkdir(parents=True)

    with log_file.open('w') as f:
        f.write('command:     %s\n' % json.dumps(command))
        f.write('user:        %s\n' % getpass.getuser())
        f.write('repoPath:    %s\n' % repo_path)
        f.write('projectPath: %s\n' % project_path)
        f.write('gitRevision: %s\n' % git_revision)
        f.write('furoVersion: %s\n' % version)
        f.write('exitCode:    %d\n' % return_code)
        f.write('---\n')
    with log_file.open('ab') as f:
        f.write(temp_file.open('rb').read(None))

    temp_file.unlink()

    os.chdir(str(project_logs_dir))

    # Upload execution log to logs repository

    current_remote = ''
    try:
        current_remote = git_output(['config', 'remote.origin.url']).strip()
    except subprocess.CalledProcessError:
        pass

    # XXX: what if current_remote differs from get_logs_repo()?
    if not current_remote:
        git(['init', '--quiet'])
        git(['remote', 'add', 'origin', get_logs_repo()])

    headline = (return_code != 0 and '[failed] ' or '') + ' '.join(command)

    git(['checkout', '--quiet', '-B', project_path])

    has_branch = False
    try:
        git(['ls-remote', '--exit-code', 'origin',
             project_path], stdout=subprocess.DEVNULL)
        has_branch = True
    except subprocess.CalledProcessError as e:
        if e.returncode != 2:
            raise e

    git(['add', '--force', str(log_file)])
    git(['commit', '--quiet', '--message', headline])

    if has_branch:
        git(['pull', '--quiet', '--rebase', 'origin', project_path])

    git(['push', '--quiet', 'origin', project_path])

    # TODO: post-execution hook like posting to Slack?
    # TODO: displaying log URL?

    sys.exit(return_code)


def command_history(args):
    repo_path, project_path, project_logs_dir = _init_project()

    if len(args) == 0:
        cmd = None
    else:
        cmd, *args = args

    if cmd == 'show':
        os.chdir(str(project_logs_dir))
        os.environ['GIT_EXTERNAL_DIFF'] = 'sh -c "cat $5"'
        git(['show', '--pretty=format:', '--ext-diff'] + args)
    elif cmd == 'pull':
        if not project_logs_dir.exists():
            try:
                project_logs_dir.parent.mkdir(parents=True)
            except FileExistsError:
                pass
            logs_repo = get_logs_repo()
            git(['clone', logs_repo,
                '-b', project_path, str(project_logs_dir)])
        else:
            os.chdir(str(project_logs_dir))
            git(['pull', 'origin', project_path])
    elif cmd == 'fix':
        logs_repo = get_logs_repo()
        os.chdir(str(project_logs_dir.parent))
        if input('rm -rf %s [y/N]: ' % project_logs_dir) == 'y':
            shutil.rmtree(str(project_logs_dir))
            try:
                git(['clone', logs_repo,
                     '-b', project_path, str(project_logs_dir)])
            except subprocess.CalledProcessError:
                pass
    elif cmd == 'git':
        os.chdir(str(project_logs_dir))
        git(args)
    else:
        os.chdir(str(project_logs_dir))
        git(['log', '--no-decorate', '--pretty=%h [%ad] (%an) %s'] + args)


def command_version(args):
    print('furoshiki2 version %s' % version)


def command_help():
    print("""
furo2 exec COMMAND [ARGS...]
furo2 history [pull | show COMMIT | fix]
furo2 version
""".strip(), file=sys.stderr)
    sys.exit(129)


class UsageError(BaseException):
    pass


def run():
    if len(sys.argv) == 1:
        command_help()

    try:
        cmd, *args = sys.argv[1:]
        if cmd == 'exec':
            command_exec(args)
        elif cmd == 'history':
            command_history(args)
        elif cmd == 'version':
            command_version(args)
        else:
            raise UsageError()
    except UsageError:
        command_help()


if __name__ == '__main__':
    run()
