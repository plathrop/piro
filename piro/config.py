"""
Configuration for piro.
"""
import getpass
import os

SERVICE_MAP = {}
ALIAS_MAP = {}

try:
    execfile('/etc/piro/config.py')
except IOError:
    pass

try:
    execfile(os.path.join(os.environ['HOME'], '.piro.py'))
except IOError:
    pass

try:
    USERNAME = os.environ['PIRO_USERNAME']
except KeyError:
    USERNAME = getpass.getuser()

try:
    PASSWORD = os.environ['PIRO_PASSWORD']
except KeyError:
    PASSWORD = None
