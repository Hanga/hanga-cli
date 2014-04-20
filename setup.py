'''
Hanga - Build automation for Python applications
'''

import os
try:
    from ez_setup import use_setuptools
    use_setuptools()
except:
    pass
from setuptools import setup


def get_version():
    basedir = os.path.dirname(__file__)
    with open(os.path.join(basedir, 'hanga', '__init__.py')) as f:
        locals = {}
        exec(f.read(), locals)
        return locals['__version__']
    raise RuntimeError('No version info founds.')


setup(
    name='hanga',
    version=get_version(),
    url='http://hanga.io',
    license='MIT',
    author='Mathieu Virbel',
    author_email='mat@hanga.io',
    description=(
        'Hanga client - Build automation for Python applications '
        'targeting mobile devices.'),
    keywords=['build', 'android', 'buildozer', 'kivy'],
    install_requires=['requests', 'buildozer', 'progressbar2', 'docopt'],
    packages=['hanga', 'hanga.scripts'],
    include_package_data=True,
    zip_safe=False,
    platforms='any',
    entry_points='''\
    [console_scripts]
    hanga = hanga.scripts.client:main
    ''',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Intended Audience :: End Users/Desktop',
        'Intended Audience :: Information Technology',
        'Intended Audience :: Science/Research',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: MIT License',
        'Operating System :: POSIX',
        'Operating System :: MacOS',
        'Operating System :: Unix',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 3',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Software Development :: Build Tools',
        'Topic :: Internet',
        'Topic :: System :: Systems Administration',
        'Topic :: System :: Monitoring'])
