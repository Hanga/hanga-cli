Hanga
=====

Build automation for Python applications targeting mobile devices. This is a
client to https://hanga.io.

.. note::

	The service is actually in a closed BETA


Installation
------------

1. Install hanga: `pip install hanga`
2. Open an account on `https://hanga.io`
3. Grab your API key at `https://hanga.io/settings`
4. Export the APK key in your environment: `export HANGA_API_KEY=YOUR_API_KEY`

Use the tool
------------

You need to have a project managed with `Buildozer <http://github.com/kivy/buildozer>`.

1. Create a `buildozer.spec` by doing `buildozer init`
2. Edit the `buildozer.spec` and adjust the parameters
3. Send your project to Hanga and build for android via: `hanga android debug`

