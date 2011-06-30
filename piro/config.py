PLUGIN_DIRS = []
SERVICE_MAP = {}

try:
    execfile('/etc/piro/config.py')
except IOError:
    pass
