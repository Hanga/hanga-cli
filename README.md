# Hanga

<img align="right" height="300" src="http://hanga.io/icon.png"/>

Build automation for Python applications targeting mobile devices. This is a
client to [Hanga](https://hanga.io).

## Installing Hanga

1. Install hanga: `pip install hanga`
2. Open an account on `https://hanga.io`
3. Grab your API key at `https://hanga.io/settings`
4. Export the APK key in your environment: `export HANGA_API_KEY=YOUR_API_KEY`


## Usage

You need to have a project managed with [Buildozer](http://github.com/kivy/buildozer).

##### Create the specification file with Buildozer, and adjust it
```
buildozer init
```
##### Submit your application to bower
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

The build result goes directly in your `bin/` directory.
