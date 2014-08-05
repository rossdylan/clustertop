from setuptools import setup, find_packages

requires = [
    'pyzabbix',
]

setup(name='clustertop',
      version='0.1.0',
      description='Monitoring a cluster using zabbix to produce near real time data',
      author='Ross Delinger',
      author_email='rossdylan@csh.rit.edu',
      packages=find_packages(),
      install_requires=requires,
      zip_safe=False,
      entry_points="""
      [console_scripts]
      clustertop=clustertop:main
      """)
