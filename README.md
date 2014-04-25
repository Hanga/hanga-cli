# Hanga Command Line Interface

<img align="right" height="200" src="http://hanga.io/static/icon.png"/>

Hanga is a build automation tool for Python applications targeting mobile devices. Hanga-CLI is a
client for [Hanga](https://hanga.io).

Hanga is a build service in the cloud, specialized to build Python applications, as long as your application is managed with [Buildozer](https://github.com/kivy/buildozer). Hanga currently works only for Android - iOS support will come soon - and will also manage signing with your keystore. It is easy to install and setup. You can be ready in a few minutes!

Hanga is currently in closed Beta.


## Installing Hanga

1. Install hanga: `pip install hanga`
1. [Open an account](https://hanga.io)
1. [Grab your API key](https://hanga.io/settings)
1. Save your API key into hanga::

	hanga set apikey YOUR_API_KEY


## Usage

You need to have a project managed with [Buildozer](http://github.com/kivy/buildozer).

##### Create the specification file with Buildozer, and adjust it
```
buildozer init
```

##### Submit your application to Hanga
```
hanga android debug
```

A typical output will look like:
```
$ hanga android debug
# Check configuration tokens
# Ensure build layout
# Prepare the source code to pack
# Compress the application
# Submit the application to build
# Submitting Flat Jewels
Upload [############################################################################################] 536.66 kB/s

Build submitted, uuid is 3c49499a-c762-11e3-bbbc-04011676f501
You can check the build status at:

    https://hanga.io/app/com.meltingrocks.flatjewels

Or you can wait the build to finish.
It will automatically download the package when done.

Done [####################################################################################] Elapsed Time: 0:02:22
# Downloading the build result
Downloading [#######################################################################################]   4.47 MB/s
# FlatJewels-0.4.1-debug.apk available in the bin directory
# Done !
```

The build result goes directly into a `bin/` directory in your project.

##### Importing keys
By default, any application build with Hanga will be compiled with the default
Hanga.io development key. If you want to get unsigned build, go to your
application page, and select "Don't sign the application".

Or you can import your key to Hanga.io from https://hanga.io/settings, or using
the command line:
```
$ hanga importkey ~/code/keys/myapp.keystore
Importing <myapp.keystore> to Hanga.io

Keystore password:
Key/alias name: my_alias
Key password (let empty to use the keystore password):
Give a name to Hanga for identify this key: Android key

Thanks you, we are adding your key...
... Done!
```
