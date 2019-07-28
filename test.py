#!/bin/env python3

import sys
import time

from vyos import Vyos

v = Vyos('fw2')
v.copy_tools()

print("\n\nCandidate config:")
status, stdout, stderr = v.configure(
        ['set firewall name TEST default-action reject'],
        action='compare')

print(stdout.decode())

# Confirm
okay = input("Okay? y/n\n> ")

if okay != 'y':
    v.cleanup_files()
    sys.exit(1)

print("\n\nRunning commit")
status, stdout, stderr = v.configure(
        ['set firewall name TEST default-action reject'],
        action='commit')

print(stdout)
print(stderr)
assert status == 0


#print("Waiting a moment")
#time.sleep(30)
#
#print("Confirming")
#v.confirm()
