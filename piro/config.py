PLUGIN_DIRS = ['/usr/share/piro/plugins']
SERVICE_MAP = {'DEFAULT', 'piro.service.Service'}

try:
    execfile('/etc/piro/config.py')
except IOError:
    pass
