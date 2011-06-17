#!/usr/bin/env python

from distutils.core import setup

setup(name='MinistryOfPackages',
      version='0.9.1',
      description='A minimal PyPI implementation meant for use behind a firewall.',
      author='Brian K. Jones',
      author_email='bkjones@gmail.com',
      url='http://github.com/bkjones/MinistryOfPackages',
      packages=['MinistryOfPackages', 'MinistryOfPackages.core', 'MinistryOfPackages.handlers'],
      data_files=[('/opt/MinistryOfPackages/etc', ['etc/config.yaml']),
                  ('/opt/MinistryOfPackages/bin', ['bin/ministry_server.py']),
                  ('/opt/MinistryOfPackages/templates', ['templates/dlist.html']),
                  ('/var/log/MinistryOfPackages', ['README.rst']),
                  ('/etc/init.d', ['init/MinistryOfPackages'])
                  ],
      classifiers=[
          'Development Status :: 3 - Alpha',
          'Environment :: Console',
          'Environment :: Web Environment',
          'Intended Audience :: Developers',
          'Intended Audience :: System Administrators',
          'License :: OSI Approved :: BSD License',
          'Natural Language :: English',
          'Operating System :: POSIX',
          'Operating System :: MacOS :: MacOS X',
          'Programming Language :: Python',
          'Programming Language :: Python :: 2.6',
          'Programming Language :: Python :: 2.7',
          'Programming Language :: Python :: 3.2',
          'Topic :: System :: Software Distribution',
          ]
     )

