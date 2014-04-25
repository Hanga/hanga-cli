import requests
from hanga.utils import TrackedFile
from hanga import appdirs
from json import dumps
from os import environ, makedirs
from os.path import join, exists
try:
    from configparser import ConfigParser
except ImportError:
    from ConfigParser import ConfigParser


class HangaException(Exception):
    pass


class HangaAPI(object):
    """API to communicate with Hanga"""

    def __init__(self, key=None, url=None):
        super(HangaAPI, self).__init__()
        self.read_configuration()
        c = self.config

        # possible url location (in order of importance)
        urls = (url,
                environ.get("HANGA_URL"),
                c.get("auth", "url") if
                c.has_option("auth", "url") else None,
                "https://hanga.io")

        # possible keys location (in order of importance)
        keys = (key,
                environ.get("HANGA_API_KEY"),
                c.get("auth", "apikey") if
                c.has_option("auth", "apikey") else None)

        self._url = next((x for x in urls if x))
        self._key = next((x for x in keys if x), None)

    def submit(self, args, filename, callback=None):
        """Submit a packaged app to build. Filename should point on a
        structured zip containing the app, buildozer.spec adjusted for it,
        and others deps if needed. Args should be the line used for building
        the app.

        The result is a dict that contain::

            {
                "result": "ok",
                "uuid": "f18cafae-c730-11e3-add4-04011676f501",
            }

        Or if there is a failure::

            {
                "result": "error",
                "details": "Something bad happened"
            }

        """
        self.ensure_configuration()
        fd = None
        try:
            fd = TrackedFile(filename, callback=callback)
            params = {"args": dumps(args)}
            r = self._build_request(
                requests.post, "submit", data=fd, params=params, stream=True)
        finally:
            if fd:
                fd.close()

        return r.json()

    def download(self, uuid, dest_dir, callback=None):
        """Download the result of a job build. If a callback is passed, it will
        be called with the size of the content received and the total size of
        the content.

        Return the name of the filename in the dest_dir.
        """
        self.ensure_configuration()
        r = self._build_request(requests.get,
                                "{}/dl".format(uuid), stream=True)

        # ensure the name is shared in the content-disposition
        disposition = r.headers.get("content-disposition")
        if not disposition or not disposition.startswith("attachment;"):
            raise HangaException("File not attached, nothing to download")
        filename = disposition.split("filename=", 1)[-1]
        if not filename:
            raise HangaException("Empty filename")

        dest_fn = join(dest_dir, filename)
        index = 0
        length = int(r.headers.get("Content-Length"))
        if callback:
            callback(0, length)
        with open(dest_fn, "wb") as fd:
            for content in r.iter_content(chunk_size=8192):
                fd.write(content)
                index += len(content)
                if callback:
                    callback(index, length)

        return filename

    def status(self, uuid):
        """Return the status of a job, in a form of a dictionary::

            {
                "result": "ok",
                "job_status": "packaging",
                "job_progression": "78"
            }

        The `result` can be either "OK" or "error" if something happens.
        The `job_status` can be a lot of things, depending on the Hanga
        version running. It ends only with a status of "done" or "error".
        """
        self.ensure_configuration()
        r = self._build_request(requests.get, "{}/status".format(uuid))
        return r.json()

    def importkey(self, platform, name, **infos):
        """Import a key to Hanga. Then you can associate the key to your app.

        `platform` is one of the supported platform in Hanga. Currently, only
        "android" is considered as valid.
        Depending of the platform, you will have multiples informations to
        pass.

        For android, you'll need `keystore`, `keystore_password`, `alias`,
        `alias_password`.

        The result is a dict that contain::

            {
                "result": "ok",
            }

        Or if there is a failure::

            {
                "result": "error",
                "details": "Something bad happened"
            }

        """

        assert(platform == "android")
        assert(name)

        if platform == "android":
            assert(infos.get("keystore"))
            assert(exists(infos.get("keystore")))
            assert(infos.get("keystore_password"))
            assert(infos.get("alias"))
            assert(infos.get("alias_password"))

        self.ensure_configuration()
        fd = None
        try:
            fd = open(infos["keystore"], "rb")
            params = {
                "platform": platform,
                "name": name,
                "keystore-password": infos["keystore_password"],
                "alias-password": infos["alias_password"],
                "alias": infos["alias"]}
            files = {"keystore-file": fd}
            r = self._build_request(
                requests.post, "importkey", data=params, files=files)
        finally:
            if fd:
                fd.close()
        return r.json()

    def _build_request(self, method, path, **kwargs):
        url = "{}api/1/{}".format(self._url, path)
        headers = {"X-Hanga-Api": self._key}
        r = method(url, headers=headers, **kwargs)
        try:
            r.raise_for_status()
        except requests.exceptions.HTTPError:
            if r.status_code:
                msg = "Access denied, invalid HANGA_API_KEY"
            else:
                msg = "Request error ({})".format(r.status_code)
            raise HangaException(msg)
        return r

    def ensure_configuration(self):
        """
        Validate that the configuration is ok to call any API commands
        """
        if not self._key:
            raise HangaException("Missing Hanga API Key")
        if not self._url.endswith("/"):
            self._url += "/"

    def read_configuration(self):
        """
        Read the configuration file. This is already done by the
        constructor.
        """
        self.config = ConfigParser()
        self.config.read(self.config_fn)
        if not self.config.has_section("auth"):
            self.config.add_section("auth")

    def write_configuration(self):
        """
        Write the current configuration to the file
        """
        with open(self.config_fn, "w") as fd:
            self.config.write(fd)

    @property
    def config_fn(self):
        if not exists(self.user_config_dir):
            makedirs(self.user_config_dir)
        return join(self.user_config_dir, 'hanga.conf')

    @property
    def user_config_dir(self):
        return appdirs.user_config_dir('Hanga', 'Melting Rocks')
