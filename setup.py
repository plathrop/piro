from setuptools import setup, find_packages

setup(name='piro',
      version="1.0.0",
      description='Piro is a tool for intelligently controlling services.',
      author='Paul Lathrop',
      author_email='paul@simplegeo.com',
      url='https://github.com/plathrop/piro',
      namespace_packages=['piro', 'piro.plugins', 'piro.util'],
      packages=find_packages(),
      install_requires=['argparse', 'sphinx'],
      entry_points={'console_scripts':
                        ['piro = piro.cli:main']}
      )
