#!/bin/env python3

import subprocess
import tempfile
import textwrap


def clean(list):
    return filter(lambda x: x is not None and x != '', list)


def formatstring(string):
    if string == "":
        return string

    # Remove leading empty lines:
    lines = string.split('\n')
    while lines[0].strip() == "":
        del lines[0]
    string = '\n'.join(lines)

    # Remove extra indentation:
    return textwrap.dedent(string)


class Vyos():
    def __init__(self, hostname):
        self.hostname = hostname
        self.tools_copied = False
        self.basedir = '/config/configurator'
        self.toolsdir = self.basedir + '/tools'
        self.files = []

    def copy_file(self, source, destination, recursive=False, keep=False):
        cmd = [
            'scp',
            '-r' if recursive else None,
            source,
            self.hostname + ':' + destination
        ]
        status = subprocess.call(clean(cmd), stdout=subprocess.DEVNULL)
        assert status == 0, "Failed to copy files"

        if not keep:
            self.files.append(destination)

    def cleanup_files(self):
        for file in self.files:
            print(f"Would remove {self.hostname}:{file}")

    def execute_command(self, command):
        proc = subprocess.Popen(
                ['ssh', self.hostname, command],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = proc.communicate()
        return proc.returncode, stdout, stderr

    def copy_tools(self):
        if not self.tools_copied:
            print("Pushing updated scripts")
            self.execute_command('mkdir -p ' + self.basedir)
            self.copy_file('tools/', self.basedir, recursive=True, keep=True)
            self.tools_copied = True

    def get_config(self):
        self.copy_tools()
        status, stdout, stderr = \
            self.execute_command(self.toolsdir + '/get_configuration.sh')
        assert status == 0, "Failed to get config"

        config = stdout.decode().split('\n')
        return clean(config)

    def push_config(self, config, action='compare'):
        assert type(config) is str
        assert action in ['compare', 'commit', 'commit-confirm']
        self.copy_tools()
        
        if action == 'commit-confirm':
            action = "echo 'y' | commit-confirm 5"

        script = f"""
        #!/bin/vbash
        source /opt/vyatta/etc/functions/script-template
        configure

        {config}

        {action}
        exit
        """

        with tempfile.NamedTemporaryFile() as f:

            # Write configuration to a file
            f.write(formatstring(script).encode())
            f.flush()
            # Copy file to router
            self.copy_file(f.name, f.name)
            # Return file name
            return f.name

    def configure(self, commands, action='compare'):
        assert type(commands) is list

        config = '\n        '.join(commands)

        filename = self.push_config(config, action)
        print("Executing: " + 'vbash ' + filename)
        status, stdout, stderr = self.execute_command('vbash ' + filename)
        return status, stdout, stderr

    def confirm(self):
        self.execute_command('vbash' + self.toolsdir + '/confirm.sh')
