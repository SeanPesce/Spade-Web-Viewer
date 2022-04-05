# MJPEG Mirror for Spade "Smart" Ear Cleaners  
**Author: Sean Pesce**  

<p align="center">
<img align="center" title="Example clip from MJPEG stream" src="https://github.com/SeanPesce/Spade-Web-Viewer/blob/master/image/example.webp?raw=true" alt="Example clip from MJPEG stream" width="320px">
</p>  


## Overview  
A utility for converting [Axel Glade Spade "smart" earwax cleaner](https://www.axelglade.com/collections/e) video streams to MJPEG for general-purpose use.  

## Usage  

 * Power on the Spade device  
 * Connect to the Spade WiFi  
 * Start the stream mirror: `python3 spade_mirror.py --no-ssl`  

With the stream mirror running, you can view the live video in a number of ways:  

 * In a web browser; navigate to `http://127.0.0.1:45100`  
 * In VLC (GUI); go to *Media*→*Open Network Stream...*, set the URL to `http://127.0.0.1:45100/stream`, and then click *Play*  
 * In VLC (command-line); run `vlc http://127.0.0.1:45100/stream`  
 * With ffmpeg; run `ffplay -i http://127.0.0.1:45100/stream`  


## Contact  
If you find any bugs, please open a new [GitHub issue](https://github.com/SeanPesce/Spade-Web-Viewer/issues/new).  


## Acknowledgements  
 * **[Damien Corpataux](https://github.com/damiencorpataux)**, whose [MJPEG implementation](https://github.com/damiencorpataux/pymjpeg) was used as a reference for this project.  


## License  
None yet.


---------------------------------------------

For unrelated inquiries and/or information about me, visit my **[personal website](https://SeanPesce.github.io)**.  

