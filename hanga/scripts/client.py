#!/usr/bin/env python
"""
Hanga client.
Submit an app to build for a specific platform.

Usage:
    hanga [options] android
    hanga [options] importkey <keystore>
    hanga set (apikey | url) <value>
    hanga -h | --help
    hanga --version

Options:
    -h, --help              Show this screen
    -p NAME --profile NAME  Select a specific profile
    -v, --verbose           Activate verbose output level
    --api API_KEY           Use a specific API key for submission
    --url URL               Use a specific URL for submission
    --nowait                Don't wait for the build to finish
    --version               Show the version of hanga
"""

from __future__ import print_function
import getpass
import hanga
import progressbar
import sys
import tempfile
import zipfile
from docopt import docopt
from os import walk, unlink
from os.path import join, exists, basename
from time import sleep
from buildozer import Buildozer
try:
    from configparser import SafeConfigParser
except ImportError:
    from ConfigParser import SafeConfigParser

IS_PY3 = sys.version_info[0] >= 3


class Text(progressbar.Widget):
    __slots__ = ("text_callback", )

    def __init__(self, callback):
        super(Text, self).__init__()
        self.text_callback = callback

    def update(self, pbar):
        return self.text_callback()


class HangaClient(Buildozer):
    def run_command(self, arguments):
        self.arguments = arguments
        if "--profile" in arguments:
            self.config_profile = arguments["--profile"]
        if "--verbose" in arguments:
            self.log_level = 2

        # create the hanga client
        self._hangaapi = hanga.HangaAPI(
            key=arguments.get("--api"),
            url=arguments.get("--url"))

        if arguments["set"]:
            self._run_set(arguments)
            return

        try:
            self._hangaapi.ensure_configuration()
        except hanga.HangaException as e:
            print("")
            print("Error: {}".format(e))
            print("")
            print("To setup your API key:")
            print("")
            print("1. Get the API key at https://hanga.io/settings")
            print("2. Run: hanga set apikey YOUR_API_KEY")
            print("")
            sys.exit(1)

        if arguments["android"]:
            self._run_android_build(arguments)
        elif arguments["importkey"]:
            self._run_importkey(arguments)

    def _run_android_build(self, arguments):
        args = ["android"]

        self._merge_config_profile()

        # fake the target
        self.targetname = "hanga"
        self.check_build_layout()

        # pack the source code and submit it
        self.info("Prepare the source code to pack")
        self._copy_application_sources()
        self.info("Compress the application")
        filename = None
        try:
            filename = self.cloud_pack_sources()
            self.info("Submit the application to build")
            self.cloud_submit(args, filename)
        finally:
            if filename:
                unlink(filename)
        self.info("Done !")

    def cloud_pack_sources(self):
        """Pack all the application sources and dependencies into a single zip.
        This zip file will be sent to the cloud builder.

        :return: fd to the temporary file. It should be closed when you're
        finished to use it.
        """

        # create custom buildozer.spec
        self.debug("Create custom buildozer.spec")
        config = SafeConfigParser()
        config.read("buildozer.spec")
        config.set("app", "source.dir", "app")

        spec_fd = None
        try:
            encoding = {}
            if IS_PY3:
                encoding["encoding"] = " utf-8"
            spec_fd = tempfile.NamedTemporaryFile(
                mode="w", delete=False, **encoding)
            config.write(spec_fd)
            spec_fd.close()

            fd = tempfile.NamedTemporaryFile(suffix=".zip", delete=False)
            with zipfile.ZipFile(fd, "w") as zfile:
                # add the buildozer definition
                zfile.write(spec_fd.name, "buildozer.spec")

                # add the application
                for root, directory, files in walk(self.app_dir):
                    for fn in files:
                        full_fn = join(root, fn)
                        arc_fn = "app{}/{}".format(
                            root[len(self.app_dir):],
                            fn)
                        zfile.write(full_fn, arc_fn)
        finally:
            if spec_fd:
                unlink(spec_fd.name)

        fd.close()
        return fd.name

    def cloud_submit(self, args, filename):
        """Submit a job to the cloud builder. It consists of sending the
        application zip file and the argument used in the command line.
        And then, wait for the build to be done :)
        """

        self.info("Submitting {}".format(self.config.get("app", "title")))
        self._pbar = None
        result = None

        # Part 1 - submit

        widgets = [
            "Upload ", progressbar.Bar(left="[", right="]"),
            " ", progressbar.FileTransferSpeed()]

        try:
            def submit_callback(current, length):
                if not self._pbar:
                    self._pbar = progressbar.ProgressBar(widgets=widgets,
                                                         maxval=length)
                    self._pbar.start()
                self._pbar.update(current)
            result = self._hangaapi.submit(args, filename, submit_callback)
        except hanga.HangaException as e:
            print("")
            print("Error: {}".format(e))
            print("")
            sys.exit(1)
        finally:
            if self._pbar:
                self._pbar.finish()

        package = "{}.{}".format(
            self.config.get("app", "package.domain"),
            self.config.get("app", "package.name"))

        if result.get("result") == "ok":
            uuid = result.get("uuid")
            print("")
            print("Build submitted, uuid is {}".format(uuid))
            print("You can check the build status at:")
            print("")
            print("    https://hanga.io/app/{}".format(package))
            print("")
        else:
            details = result.get("details")
            self.error("Submission error: {}".format(details))
            return

        if self.arguments.get("--nowait"):
            return

        # Part 2, wait.
        print("Or you can wait for the build to finish.")
        print("It will automatically download the package when done.")
        print("")

        status = self._last_status = ""
        progression = 0
        widgets = [
            Text(self._get_last_status),
            " ", progressbar.Bar(left="[", right="]"), " ",
            progressbar.Timer()]
        self._pbar = progressbar.ProgressBar(widgets=widgets, maxval=100)
        self._pbar.start()

        try:
            while status not in ("done", "error"):
                sleep(1)
                try:
                    infos = self._hangaapi.status(uuid)
                except hanga.HangaException as e:
                    print("")
                    print("Error: {}".format(e))
                    print("")
                    sys.exit(1)
                if infos.get("result") != "ok":
                    return
                self._last_status = status = infos["job_status"]
                progression = int(infos["job_progression"])
                self._pbar.update(progression)
        finally:
            self._pbar.finish()

        # if the build is broken, don't do anything
        if status != "done":
            return

        # Part 3: download
        self.api_download(uuid)

    def api_download(self, uuid):
        self.info("Downloading the build result")

        self._pbar = None
        widgets = [
            "Downloading ", progressbar.Bar(left="[", right="]"),
            " ", progressbar.FileTransferSpeed()]

        def download_callback(current, length):
            if self._pbar is None:
                self._pbar = progressbar.ProgressBar(widgets=widgets,
                                                     maxval=length)
                self._pbar.start()
            self._pbar.update(current)

        try:
            filename = self._hangaapi.download(
                uuid, self.bin_dir, callback=download_callback)
        except hanga.HangaException as e:
            print("")
            print("Error: {}".format(e))
            print("")
            sys.exit(1)
        finally:
            if self._pbar:
                self._pbar.finish()

        self.info("{} is available in the bin directory".format(filename))

    def _get_last_status(self):
        return (self._last_status or "waiting").capitalize()

    def _run_set(self, arguments):
        value = arguments.get("<value>")
        if arguments["apikey"]:
            key = "apikey"
            if len(value) != 32:
                self.error("Invalid API key, it should have 32 characters")
                sys.exit(1)
        elif arguments["url"]:
            key = "url"
            if not key.startswith("https://"):
                if key.startswith("http://"):
                    self.error("Warning: You are using HTTP instead of HTTPS")
                    self.error(
                        "Warning: Communication with Hanga will be unsecure")
                else:
                    self.error("Invalid protocol in URL (https or http only)")
        else:
            assert(0)

        self._hangaapi.config.set("auth", key, value)
        self._hangaapi.write_configuration()
        print("Config updated at {}".format(self._hangaapi.config_fn))

    def _run_importkey(self, arguments):
        filename = arguments["<keystore>"]
        print("Importing <{}> to Hanga.io".format(basename(filename)))
        print("")
        if not exists(filename):
            self.error("Unable to find the file {}".format(filename))
            sys.exit(1)

        keystore_password = ""
        alias = ""
        alias_password = ""
        title = ""

        while not keystore_password:
            keystore_password = getpass.getpass("Keystore password: ")
            if keystore_password:
                break
            self.error("Error, empty password")

        while not alias:
            print("Key/alias name: ", end="")
            alias = raw_input()
            if alias:
                break
            self.error("Error, empty key/alias.")

        alias_password = getpass.getpass(
            "Key password (let empty to use the keystore password): ")
        if not alias_password:
            alias_password = keystore_password

        print("Give a name to Hanga for identify this key: ", end="")
        while not title:
            title = raw_input()
            if title:
                break
            self.error("No name, please enter one")
            print("Name this keystore: ", end="")

        print("")
        print("Thanks you, we are adding your key...")

        try:
            ret = self._hangaapi.importkey(
                "android",
                title,
                keystore=filename,
                keystore_password=keystore_password,
                alias=alias,
                alias_password=alias_password)
        except hanga.HangaException as e:
            print("")
            print("Error: {}".format(e))
            print("")
            sys.exit(1)

        if ret["result"] == "ok":
            print("... Key added!")
        else:
            print("... Error: {}".format(ret["details"]))


def main():
    arguments = docopt(__doc__, version="Hanga {}".format(hanga.__version__))
    try:
        HangaClient().run_command(arguments)
    except KeyboardInterrupt:
        print("")
        sys.exit(0)

if __name__ == "__main__":
    main()
