#!/usr/bin/env python
"""
Hanga client.
Submit a app to build for a specific platform.

Usage:
    hanga [options] android debug
    hanga -h | --help
    hanga --version

Options:
    -h, --help              Show this screen.
    -p NAME --profile NAME  Select a specific profile
    -v, --verbose           Activate verbose level
    --api API_KEY           Use a specific API key for submission
    --url URL               Use a specific URL for submission
    --nowait                Don't wait for the build to finish
    --version               Show the hanga version
"""

import sys
import hanga
import tempfile
import zipfile
import progressbar
from docopt import docopt
from os import walk
from os.path import join
from time import sleep
from buildozer import Buildozer
try:
    from configparser import SafeConfigParser
except ImportError:
    from ConfigParser import SafeConfigParser


class Text(progressbar.Widget):
    __slots__ = ('text_callback', )

    def __init__(self, callback):
        super(Text, self).__init__()
        self.text_callback = callback

    def update(self, pbar):
        return self.text_callback()


class HangaClient(Buildozer):
    def run_command(self, arguments):
        args = []
        self.arguments = arguments
        if 'android' in arguments:
            args += ['android']
        if 'debug' in arguments:
            args += ['debug']
        if '--profile' in arguments:
            self.config_profile = arguments['--profile']
        if '--verbose' in arguments:
            self.log_level = 2

        self._merge_config_profile()

        # create the hanga client
        try:
            self._hangaapi = hanga.HangaAPI(
                key=arguments.get('--api'),
                url=arguments.get('--url'))
        except hanga.HangaException as e:
            print('')
            print('Error: {}'.format(e))
            print('')
            print('You have 2 way to setup your API Key:')
            print('')
            print('1. export HANGA_API_KEY=YOUR_API_KEY')
            print('2. or add "--api YOUR_API_KEY" in your command line')
            print('')
            print('Get your API key at https://hanga.io/settings')
            print('')
            sys.exit(1)

        # fake the target
        self.targetname = 'hanga'
        self.check_build_layout()

        # pack the source code and submit it
        self.info('Prepare the source code to pack')
        self._copy_application_sources()
        self.info('Compress the application')
        try:
            fd = None
            fd = self.cloud_pack_sources()
            self.info('Submit the application to build')
            self.cloud_submit(args, fd.name)
        finally:
            if fd:
                fd.close()
        self.info('Done !')

    def cloud_pack_sources(self):
        """Pack all the application sources and dependencies into a single zip.
        This zip file will be sent to the cloud builder.

        :return: fd to the temporary file. It should be closed when you're
        finished to use it.
        """

        # create custom buildozer.spec
        self.debug('Create custom buildozer.spec')
        config = SafeConfigParser()
        config.read('buildozer.spec')
        config.set('app', 'source.dir', 'app')

        try:
            spec_fd = tempfile.NamedTemporaryFile(mode="w", encoding="utf-8")
            config.write(spec_fd)
            spec_fd.file.flush()

            fd = tempfile.NamedTemporaryFile(suffix='.zip')
            with zipfile.ZipFile(fd, 'w') as zfile:
                # add the buildozer definition
                zfile.write(spec_fd.name, 'buildozer.spec')

                # add the application
                for root, directory, files in walk(self.app_dir):
                    for fn in files:
                        full_fn = join(root, fn)
                        arc_fn = 'app{}/{}'.format(
                            root[len(self.app_dir):],
                            fn)
                        zfile.write(full_fn, arc_fn)
        finally:
            if spec_fd:
                spec_fd.close()

        fd.file.flush()
        return fd

    def cloud_submit(self, args, filename):
        """Submit a job to the cloud builder. It consist of sending the
        application zip file and the argument used in the command line.
        And then, wait for the build to be done :)
        """

        self.info('Submitting {}'.format(self.config.get('app', 'title')))
        self._pbar = None
        result = None

        # Part 1 - submit

        widgets = [
            'Upload ', progressbar.Bar(left='[', right=']'),
            ' ', progressbar.FileTransferSpeed()]

        try:
            def submit_callback(current, length):
                if not self._pbar:
                    self._pbar = progressbar.ProgressBar(widgets=widgets,
                                                         maxval=length)
                    self._pbar.start()
                self._pbar.update(current)
            result = self._hangaapi.submit(args, filename, submit_callback)
        finally:
            if self._pbar:
                self._pbar.finish()

        package = '{}.{}'.format(
            self.config.get('app', 'package.domain'),
            self.config.get('app', 'package.name'))

        if result.get('result') == 'ok':
            uuid = result.get('uuid')
            print('')
            print('Build submitted, uuid is {}'.format(uuid))
            print('You can check the build status at:')
            print('')
            print('    https://hanga.io/app/{}'.format(package))
            print('')
        else:
            details = result.get('details')
            self.error('Submission error: {}'.format(details))
            return

        if self.arguments.get('--nowait'):
            return

        # Part 2, wait.
        print('Or you can wait the build to finish.')
        print('It will automatically download the package when done.')
        print('')

        status = self._last_status = ''
        progression = 0
        widgets = [
            Text(self._get_last_status),
            ' ', progressbar.Bar(left='[', right=']'), ' ',
            progressbar.Timer()]
        self._pbar = progressbar.ProgressBar(widgets=widgets, maxval=100)
        self._pbar.start()

        try:
            while status not in ('done', 'error'):
                sleep(1)
                infos = self._hangaapi.status(uuid)
                if infos.get('result') != 'ok':
                    return
                self._last_status = status = infos['job_status']
                progression = int(infos['job_progression'])
                self._pbar.update(progression)
        finally:
            self._pbar.finish()

        # if the build is broken, don't do anything
        if status != 'done':
            return

        # Part 3: download
        self.api_download(uuid)

    def api_download(self, uuid):
        self.info('Downloading the build result')

        self._pbar = None
        widgets = [
            'Downloading ', progressbar.Bar(left='[', right=']'),
            ' ', progressbar.FileTransferSpeed()]

        def download_callback(current, length):
            if self._pbar is None:
                self._pbar = progressbar.ProgressBar(widgets=widgets,
                                                     maxval=length)
                self._pbar.start()
            self._pbar.update(current)

        try:
            filename = self._hangaapi.download(
                uuid, self.bin_dir, callback=download_callback)
        finally:
            if self._pbar:
                self._pbar.finish()

        self.info('{} available in the bin directory'.format(filename))

    def _get_last_status(self):
        return (self._last_status or 'waiting').capitalize()


def main():
    arguments = docopt(__doc__, version="Hanga {}".format(hanga.__version__))
    try:
        HangaClient().run_command(arguments)
    except KeyboardInterrupt:
        print('')
        sys.exit(0)

if __name__ == '__main__':
    main()
