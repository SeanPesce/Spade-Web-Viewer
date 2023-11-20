# MJPEG Mirror for Spade "Smart" Ear Cleaners  
**Author: Sean Pesce**  

<p align="center">
<img align="center" title="Example clip from MJPEG stream" src="https://github.com/SeanPesce/Spade-Web-Viewer/blob/master/image/example.webp?raw=true" alt="Example clip from MJPEG stream" width="320px">
</p>  


## Overview  
A utility for converting [Axel Glade Spade "smart" earwax cleaner](https://www.axelglade.com/collections/e) video streams to MJPEG for general-purpose use.  

**NOTE:** This tool has only been tested with the [Spade Mini](https://www.axelglade.com/collections/e/products/spade-mini), but it should work for any product that uses `libmlcamera-2.5.so` or the Spade mobile app (`com.molink.john.spade` - [Google Play](https://play.google.com/store/apps/details?id=com.molink.john.spade)/[iOS](https://apps.apple.com/us/app/spade-by-axel-glade/id1535193019)) for video streaming in its client implementation.  


## Usage  

 * Power on the Spade device  
 * Connect to the Spade WiFi  
 * Start the stream mirror: `python3 spade_mirror.py --no-ssl`  

With the stream mirror running, you can view the live video in a number of ways:  

 * In a web browser; navigate to `http://127.0.0.1:45100`  
 * In VLC (GUI); go to *Media*→*Open Network Stream...*, set the URL to `http://127.0.0.1:45100/stream`, and then click *Play*  
 * In VLC (command-line); run `vlc http://127.0.0.1:45100/stream`  
 * With ffmpeg; run `ffplay -i http://127.0.0.1:45100/stream`  


## SSL/TLS    

The video stream can also be transported over TLS for security. This document won't walk you through setting up your own [PKI](https://myhomelab.gr/linux/2019/12/13/local-ca-setup.html), but the following command will generate a key pair for encrypting traffic with TLS:  

```
openssl req -new -newkey rsa:4096 -x509 -sha256 -days 365 -nodes -out cert.crt -keyout private.key
```

To start the stream mirror over HTTPS, specify the TLS key pair in the shell command:  

```
python3 spade_mirror.py cert.crt private.key
```

The HTTPS stream will then be accessible at `https://127.0.0.1:45100/stream`.  


## Contact  
If you find any bugs, please open a new [GitHub issue](https://github.com/SeanPesce/Spade-Web-Viewer/issues/new).  


## Related Projects  
 * **[Suear Web Viewer](https://github.com/SeanPesce/Suear-Web-Viewer)**, a similar project for [Suear](https://play.google.com/store/apps/details?id=com.i4season.bkCamera) "smart" earwax cleaners (sold under brand names such as [LEIPUT](https://www.amazon.com/Ear-Wax-Removal-Remover-Android%EF%BC%88Black%EF%BC%89/dp/B09KZ8TS7L)).  


## Acknowledgements  
 * **[Damien Corpataux](https://github.com/damiencorpataux)**, whose [MJPEG implementation](https://github.com/damiencorpataux/pymjpeg) was used as a reference for this project.  


## License  

[GNU General Public License v2.0](LICENSE)  


---------------------------------------------

For unrelated inquiries and/or information about me, visit my **[personal website](https://SeanPesce.github.io)**.  

