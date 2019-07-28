#!/bin/env python3

import argparse
import re
import sys

from vyos import Vyos
from generators import generate_firewall, generate_interfaces


def print_filtered(stdout, stderr):
    for line in stdout.decode().split('\n'):
        line = line.strip()
        if line != '':
            if re.match('^Configuration path: \\[.*\\] already exists$', line):
                continue
            if line == 'Nothing to delete (the specified node does not exist)':
                continue
            print(line)

    for line in stderr.decode().split('\n'):
        if line.strip() != 'Welcome to VyOS':
            print(line)


## Parse args

parser = argparse.ArgumentParser(
        description="Generate and deploy VyOS configurations")

parser.add_argument('-a', '--address', required=True,
                    help='Address of the router for deployment')
parser.add_argument('-i', '--interfaces',
                    help='YAML file containing list of interfaces')
parser.add_argument('-f', '--firewall',
                    help='YAML file describing firewall rules')
parser.add_argument('-n', '--number',
                    help='Index of the device when configuring a HA cluster')
parser.add_argument('-c', '--check', action='store_true',
                    help='Compare to current version and exit, no prompt to apply')
parser.add_argument('-d', '--debug', action='store_true',
                    help='Additional debug prints')

args = parser.parse_args()

check_mode = args.check


## Get original configuration

print("--Fetching old config")
v = Vyos(args.address)
v.copy_tools()
original = list(v.get_config())

## Generate configuration

command_groups = []
command_groups_to_apply = []

if args.interfaces:
    print("--Generating interface configs")
    command_groups += generate_interfaces(args.interfaces, int(args.number))

if args.firewall:
    print("--Generating firewall configs")
    command_groups += generate_firewall(args.firewall)

delete_changed = []
print("--Checking for changed trees")
for grp in command_groups:
    if grp.is_changed(original):
        if args.debug:
            print("Changed, recreating: " + grp.prefix)
        delete_changed.append(f"delete {grp.prefix}")
        command_groups_to_apply.append(grp)
    else:
        if args.debug:
            print("Unchanged, ignoring: " + grp.prefix)

## Validate and compare config

commands_by_action = {
    'delete': [],
    'set': [],
}

for grp in command_groups_to_apply:
    for rule in grp.rules:
        commands_by_action[grp.action].append(rule)

commands = commands_by_action['delete'] + delete_changed + commands_by_action['set']

print("--Checking diff:")
status, stdout, stderr = v.configure(commands, action='compare')

print("\n\nChanges:")
print_filtered(stdout, stderr)
assert status == 0

## Exit if checking was all we wanted to do

if check_mode:
    v.cleanup_files()
    sys.exit(0)


## Confirm and apply config

okay = input("Okay? y/n\n> ")

if okay != 'y':
    v.cleanup_files()
    sys.exit(1)

print("\n\nRunning commit")
status, stdout, stderr = v.configure(commands, action='commit')
print_filtered(stdout, stderr)
assert status == 0
