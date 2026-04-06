---
tags:
  - '#iiif'
---

# IIIF Image Conversion Guide

The Europeana Natural History Aggregator OpenUp! has developed scripts for the IIIF image conversion process that can be used to install a IIIF server and perform a IIIF image conversion. The scripts are available for download and reuse from a [GitHub repository](https://github.com/AITProjectAssistant/OpenUp/tree/main/IIIF).

This guide describes in detail how image collection owners and their technical support may utilise the scripts to make their collections IIIF-compatible.

- [1 Goal](#key-1-goal)
- [2 Prior knowledge and technology](#key-2-prior-knowledge-and-technology)
- [3 Web server setup](#key-3-web-server-setup)
- [4 Install the IIPImage Server](#key-4-install-the-iipimage-server)
- [5 Convert images to pyramid TIFFs](#key-5-convert-images-to-pyramid-tiffs)
  - [Installation of the image processor VIPS](#installation-of-the-image-processor-vips)
  - [Image transformation](#image-transformation)
- [6 Accessing Images in the Browser via a URL](#key-6-accessing-images-in-the-browser-via-a-url)
- [7 Accessing Images in the Browser via the Manifest](#key-7-accessing-images-in-the-browser-via-the-manifest)
- [8 Glossary](#key-8-glossary)
- [9 Scripts](#key-9-scripts)

# **1 Goal**

[IIIF](https://iiif.io/) stands for [International Image Interoperability Framework](https://iiif.io/) (spoken Triple-Eye-F). The framework was created to offer the scientific community a way to productively interact with their digital objects (visual or audio/visual) and use them across different platforms. [Here you can learn about the benefits of IIIF](https://iiif.io/get-started/why-iiif/).

If you are looking for a general introduction to the IIIF framework, please check out the [What is IIIF?](https://training.iiif.io/europeana/index.html) training resources for aggregators.

The **goal** of this guide is to give you an example of how to **make your digital images IIIF compliant**. For that purpose you will have to run a [**web server**](https://en.wikipedia.org/wiki/Web_server) and a [**IIIF-compatible image server**](https://iiif.io/get-started/image-servers/)and provide your [**images in a multi-resolution format (pyramid TIFFs)**](https://www.loc.gov/preservation/digital/formats/fdd/fdd000237.shtml). Pyramid TIFFs are layered documents that contain multiple, mapped versions of the same image in different resolutions. This allows image servers to optimize zooming, as they switch to higher resolution images as the user zooms deeper and deeper into the document.

![img-conv-process.png](https://europeana.atlassian.net/wiki/download/attachments/2343010305/img-conv-process.png?version=1&modificationDate=1712310527658&cacheVersion=1&api=v2)

Main contents of the guide

- How to run a **web server** [(chapter 3)](#chapter-3)
- How to run a **IIIF-compatible image server** [(chapter 4)](#chapter-4)
- How to **convert images to a multi-resolution format** [(chapter 5)](#chapter-5)
- How to **access your IIIF images** through an Internet browser URL ([Chapter 6](#chapter-6)), and how to access images via a [IIIF manifest](https://iiif.io/get-started/how-iiif-works/) ([chapter 7](#chapter-7)).

Glossary and scripts

- You will find links and information on the most important technical terms in the **glossary** of [chapter 8](#chapter-8).
- And finally, in [chapter 9](#chapter-9), you will find the information from where to download the **image conversion script** and a **script to install the web server and the IIPImage Server**.

Overall workflow

![Workflow](https://europeana.atlassian.net/wiki/download/attachments/2343010305/workflow1.png?version=1&modificationDate=1685514372775&cacheVersion=1&api=v2)

The first two steps “**Web server setup**” and “**Install the IIPImage Server**” are described in detail in [chapter 3](#chapter-3) and [4](#key-4) of this guide, but they can be easily executed automatically by running the script “**iiif-install.sh**” on your computer (find the script in [chapter 9](#chapter-9)).  
The step “**Convert images to pyramid TIFFs**”, described in [chapter 5](#chapter-5), can be carried out by running the “**iiif-image-converter.sh**” script (find the script in [chapter 9](#chapter-9)).

# **2 Prior knowledge and technology**

This guide is intended for people with basic **prior knowledge** of the Linux operating system (e.g. opening the terminal, basic Linux commands (<https://opensource.com/article/22/5/essential-linux-commands> ), difference between normal and sudo user, etc.). In addition, it would be good if you would familiarize yourself with the following points: [IIIF](https://iiif.io/) and Image API (<https://iiif.io/get-started/how-iiif-works/> ); multi-resolution image file formats (<https://iipimage.sourceforge.io/documentation/images/> ).

In-depth technical knowledge is not required, i.e. it is possible to install and set up the Apache and Image Server, perform image format conversion and access the images via a URL by simply following the steps in this guide.

**Technology** used within the scope of this guide:

- **Operating system**: Linux Debian, i.e. Ubuntu

  - sudo user with administration permissions
- **Webserver**: Apache2
- **Image server**: IIPImage Server

# **3 Web server setup**

Web servers are used to serve web pages requested by client computers. Apache is a widely used web server application. It is very secure, fast and reliable. It makes it possible to share your content (the offline web page) with other users in your network on a real website.

**Update packages on your computer**

Enter the following command in the Linux terminal to install and set up Apache server:

```java
sudo apt-get update
```

After entering this command, the command line will prompt for user and password.

![](https://europeana.atlassian.net/wiki/download/attachments/2343010305/Figure2.png?version=1&modificationDate=1685514673130&cacheVersion=1&api=v2)

**Install Apache 2 (additionally install sub-software package fcgid)**

```java
sudo apt-get install apache2 libapache2-mod-fcgid
```

![](https://europeana.atlassian.net/wiki/download/attachments/2343010305/Figure3.png?version=2&modificationDate=1685514994860&cacheVersion=1&api=v2)

**Start web server**

```java
sudo systemctl start apache2
```

![](https://europeana.atlassian.net/wiki/download/attachments/2343010305/Figure4.png?version=1&modificationDate=1685515026835&cacheVersion=1&api=v2)

**Make sure that the Apache server is actually running**

Open your browser, enter your IP address into your browser’s address bar and the Apache2 Debian Default Page should appear as in the screenshot below.

![](https://europeana.atlassian.net/wiki/download/attachments/2343010305/Figure5.png?version=1&modificationDate=1685531677574&cacheVersion=1&api=v2)

**Move your content (files you want to access via the browser e.g. html and css files) to the default folder Apache points to (/var/www/html/)**

Enter your IP address into your browser and if all goes well, your content will be loaded.

# **4 Install the IIPImage Server**

“The [IIPImage Server](https://iipimage.sourceforge.io/documentation/server) is a feature-rich high performance image server engineered to be stable, fast and lightweight. It is designed for streaming extremely high resolution images and is capable of handling advanced image features such as 16 and 32 bit per channel depths, floating point data, CIELAB colorimetric images and scientific imagery such as multispectral or hyperspectral images and digital elevation map data.”

IIPImage Server installation and setup is done with the following steps:

**Install iipimage-server package with command below**

```java
sudo apt-get install iipimage-server
```

The command will prompt you for installing some dependencies for this package. To do this, type “y” (yes) and press *Enter*.

![](https://europeana.atlassian.net/wiki/download/attachments/2343010305/Figure6.png?version=1&modificationDate=1685531764811&cacheVersion=1&api=v2)

**Change your image server’s data directory**

With the following command the default data directory of your image server */usr/lib/iipimage-server/* is copied to apache2 folder */var/www/*:

```java
sudo cp -r /usr/lib/iipimage-server/ /var/www/iipimage-server/
```

![](https://europeana.atlassian.net/wiki/download/attachments/2343010305/Figure7.png?version=1&modificationDate=1685532849335&cacheVersion=1&api=v2)

Now you need to run the image server as an Apache module. The modules are configured in directory */etc/Apache2/mods-available/*.   
Change to this directory and open from there the image server’s *iipsrv.conf* config file with following command:

```java
sudo nano /etc/apache2/mods-available/iipsrv.conf
```

In this file **change the following line**:

*ScriptAlias /iipsrv/ "/usr/lib/iipimage-server/"*  
**to**  
*ScriptAlias /iiif "/var/www/iipimage-server/iipsrv.fcgi"*

In addition, you can configure the server to serve through a "cleaner" url. You do that by adding this line in the environment variables:

*FcgidInitialEnv URI\_MAP "iiif=>IIIF"*

Save the file with *Ctrl+o* and press *Enter* to confirm and close nano with *Ctrl+x*.   
All these changes are illustrated in Figure 8 (red arrows). With this module enabled, Apache knows where you put the image server’s data directory.

![](https://europeana.atlassian.net/wiki/download/attachments/2343010305/Figure8.png?version=1&modificationDate=1685532981539&cacheVersion=1&api=v2)

**Enable the necessary Apache modules for the image server (fcgid already installed and enabled above)**

Use the commands:

```java
sudo a2enmod headers
```

If fcgid or headers was not enabled before you will have to restart Apache now with the following command:

```java
sudo systemctl restart apache2
```

Then you need to check if the image server‘s module (iipsrv) is enabled:

```java
sudo a2enmod iipsrv
```

Now, that all three modules are enabled you need to restart Apache again:

```java
sudo systemctl restart apache2
```

![](https://europeana.atlassian.net/wiki/download/attachments/2343010305/Figure9.png?version=1&modificationDate=1685533051122&cacheVersion=1&api=v2)

**Enable CORS**

In the image server’s config file you enable CORS ([cross origin resource sharing](https://en.wikipedia.org/wiki/Cross-origin_resource_sharing)) to make sure that the image server is IIIF-compliant, because it allows others to embed your images into their website. To enable CORS open the config file with following command:

```java
sudo nano /etc/apache2/apache2.conf
```

Move down to the end of the file and the following line:

Header set Access-Control-Allow-Origin \*

It is important that there are no spelling mistakes in the line above. Then you save changes with *Ctrlt+o* and exit nano with *Ctrl+x*.

![](https://europeana.atlassian.net/wiki/download/attachments/2343010305/Figure10.png?version=1&modificationDate=1685533086757&cacheVersion=1&api=v2)

Now you restart Apache once again:

```java
sudo systemctl restart apache2
```

**Check if the IIPImage server works**

Enter in your browser address bar:

***your.ip.address*****/iiif/**

If the start screen of the IIPImage server is shown then you are sure that the server configuration was successful and it runs correctly.

![](https://europeana.atlassian.net/wiki/download/attachments/2343010305/Figure11.png?version=1&modificationDate=1685533165904&cacheVersion=1&api=v2)

# **5 Convert images to pyramid TIFFs**

With a multi-resolution format, large raster image files are compressed and can be quickly viewed without having to decompress the entire file. IIPImage Server supports multi-resolution images of the format TIFF and JEPG2000. Thus you need to convert your images to one of these types. In this guide we show how you can convert your images to TIFF format.  
Figure 12 shows graphically how pyramid TIFFs are constructed. The Tiled Multi-Resolution (or Tiled Pyramidal) TIFF type allows the image server to enhance zoom options in a way that it switches to higher resolution images of the pyramid as the zoom goes deeper and deeper.

![](https://europeana.atlassian.net/wiki/download/attachments/2343010305/Figure12.png?version=1&modificationDate=1685533220335&cacheVersion=1&api=v2)

## Installation of the image processor VIPS

**Before image transformation the installation of the image processor VIPS is necessary**

Use **apt-get** to install the the package **libvips-tools** on Ubuntu:

```java
sudo apt-get install libvips-tools
```

![](https://europeana.atlassian.net/wiki/download/attachments/2343010305/Figure13.png?version=1&modificationDate=1685533251405&cacheVersion=1&api=v2)

Now go to the folder where the original images are stored (e.g: **cd /var/www/html/images/**)

## Image transformation

This is the main part of this chapter: image transformation.   
If you have original images in .png format and you want to transform them into .tif then the following command is executed:

```java
sudo vips im_vips2tiff image1.png image1.tif:deflate,tile:256x256,pyramid 
```

The execution of the command above can take some time because the pyramid tiffs are huge files.   
This command is only for one image!   
If you need to convert a large number of images, the shell script (**iiif-image-converter.sh**) that contains the conversion command automates this process for all images. The content of the **iiif-image-converter.sh** shell script looks like this:

![](https://europeana.atlassian.net/wiki/download/attachments/2343010305/CovertImagesToPyramidsTIFFs_script.png?version=1&modificationDate=1685533317780&cacheVersion=1&api=v2)

You need to place the script in the same folder where the images are located (**e.g.: /var/www/html/images/** ) and execute the script by typing the following command into your terminal:

```java
./iiif-image-converter.sh
```

Note: If you don’t not have the appropriate permissions to make changes to the folder where the images and the script **iiif-image-converter.sh** are located, or if you do not have the permissions for the folder where the resulting images are to be moved after conversion, then you can obtain these permissions by either executing **iiif-image-converter.sh** with the sudo command or by modifying the **iiif-image-convert.sh script** and inserting the sudo command before the vips and mv commands.

**Move the converted images to the image servers’ data directory**

In a final step, the script moves the converted images to the image servers’ data directory in order to make them accessible via the image server module.

# **6 Accessing Images in the Browser via a URL**

When you call an image via an IIPImage server URL, the image server will show you this image according to some parameters that you have set in the URL.

For example you can type the following in your browser’s address bar:

***your.ip.address*****/iiif/image1.tif/full/400,/0/default.jpg**

The IIIF consortium provides a detailed documentation of the IIIF Image API’s parameters [here](https://iiif.io/api/image/3.0/).

# **7 Accessing Images in the Browser via the Manifest**

The Manifest is a container file (in the [JSON](https://en.wikipedia.org/wiki/JSON) format), that contains metadata about an image collection as well as the IIIF compliant URLs to the contained images.

The sample manifest can be viewed and downloaded from [here](https://iiif.io/api/cookbook/recipe/0005-image-service/manifest.json).

![](https://europeana.atlassian.net/wiki/download/attachments/2343010305/sampleManifest.png?version=1&modificationDate=1685533553926&cacheVersion=1&api=v2)

However, this manifest needs to be updated according to your needs. For that you may use for example the nano command. Updating means in this context: changing *MY\_IP\_ADDRESS* to **your** **actual** IP Address or host name (if known), changing the content of “label” tag etc. Then if everything is adapted and changed correctly the manifest should be loaded in the browser by entering the following in the browser’s address bar:

***your.ip.address*****/manifest\_name.json**

Using the manifest the images can be accessed and viewed with a **IIIF-compliant image viewer** like [Mirador, Universal Viewer, OpenSeadragon etc.](https://iiif.io/get-started/iiif-viewers/)

Please see the [IIIF Image Conversion (Compact Version)](IIIF%20Image%20Conversion%20(Compact%20Version).md) for a detailed use case description.

# **8 Glossary**

|                             |                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
|:----------------------------|:------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Linux Debian i.e. Ubuntu    | Ubuntu develops and maintains a cross-platform, open-source operating system based on Debian, with a focus on release quality, enterprise  security updates and leadership in key platform capabilities for  integration, security and usability. <br/> <https://ubuntu.com/community/governance/debian>                                                                                                                                                                                              |
| Apache                      | The Apache HTTP Server Project is an effort to develop and maintain an open-source HTTP server for modern operating systems including UNIX and Windows. <br/> <https://httpd.apache.org/>                                                                                                                                                                                                                                                                                                             |
| IIPImage Server             | The IIPImage server is a feature-rich high performance image server engineered to be stable, fast and lightweight. It is designed for  streaming extremely high resolution images and is capable of handling  advanced image features such as 16 and 32 bit per channel depths,  floating point data, CIELAB colorimetric images and scientific imagery  such as multispectral or hyperspectral images and digital elevation map  data. <br/> <https://iipimage.sourceforge.io/documentation/server/> |
| Pyramid TIFF                | Tiled Multi-Resolution (or Tiled Pyramidal) TIFF is simply a tiled multi-page TIFF image, with each resolution stored as a separate layer within the TIFF. <br/> <https://iipimage.sourceforge.io/documentation/images/>                                                                                                                                                                                                                                                                              |
| libapache2-mod-fcgid        | This package contains mod\_fcgid, a high-performance alternative to mod\_cgi or mod\_cgid. It starts a sufficient number of instances of the CGI program to handle concurrent requests. These programs remain running to handle further incoming requests. <br/> [libapache2-mod-fcgid](https://packages.debian.org/buster/libapache2-mod-fcgid)                                                                                                                                                      |
| IIIF                        | IIIF is a way to standardise the delivery of images and audio/visual files from servers to different environments on the Web where they can  then be viewed and interacted with in many ways. <br/> <https://iiif.io/>                                                                                                                                                                                                                                                                                |
| IIIF Image API’s parameters | The IIIF Image API specifies a web service that returns an image in response to a standard HTTP or HTTPS request. The URI can specify the region, size, rotation, quality characteristics and format of the requested image. <br/> <https://iiif.io/api/image/3.0/>                                                                                                                                                                                                                                   |

# **9 Scripts**

Access this [GitHub repository](https://github.com/AITProjectAssistant/OpenUp/tree/main/IIIF) to download the two scripts:

[iiif-image-converter.sh](https://github.com/AITProjectAssistant/OpenUp/tree/main/IIIF)

[iiif-install.sh](https://github.com/AITProjectAssistant/OpenUp/tree/main/IIIF)
