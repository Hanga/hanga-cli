from os import stat


class TrackedFile(object):
    def __init__(self, filename, callback):
        super(TrackedFile, self).__init__()
        self._file = open(filename, 'rb')
        self._fullsize = stat(self._file.name).st_size
        self._callback = callback

    def __len__(self):
        if not self._fullsize:
            self._fullsize = stat(self._file.name).st_size
        return self._fullsize

    def __iter__(self):
        return iter(self._file)

    def read(self, blocksize=8192):
        if self._callback:
            self._callback(self._file.tell(), len(self))
        return self._file.read(blocksize)

    def __getattr__(self, attr):
        return getattr(self._file, attr)


