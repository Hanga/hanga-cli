import requests
from hanga.utils import TrackedFile
from json import dumps
from os import environ
from os.path import join


class HangaException(Exception):
    pass


class HangaAPI(object):
    """API to communicate with Hanga"""

    def __init__(self, key=None, url=None):
        super(HangaAPI, self).__init__()
        self._url = url or environ.get("HANGA_URL", "https://hanga.io")
        self._key = key or environ.get("HANGA_API_KEY")
        if not self._key:
            raise HangaException("Missing Hanga API Key")
        if not self._url.endswith("/"):
            self._url += "/"

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
        """Return the status of a job, in a form of a dictonnary::

            {
                "result": "ok",
                "job_status": "packaging",
                "job_progression": "78"
            }

        The `result` can be either "ok" or "error" if something happen.
        the `job_status` can be lot of things, depending the latest Hanga
        version running. It ends only with status: "done" or "error".
        """
        r = self._build_request(requests.get, "{}/status".format(uuid))
        return r.json()

    def _build_request(self, method, path, **kwargs):
        url = "{}api/1/{}".format(self._url, path)
        headers = {"X-Hanga-Api": self._key}
        r = method(url, headers=headers, **kwargs)
        r.raise_for_status()
        return r
