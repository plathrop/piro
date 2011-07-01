"""
Configuration for piro.
"""
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
