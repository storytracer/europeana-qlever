---
tags:
  - '#iiif'
---

# IIIF Image Conversion (Compact Version)

This compact guide describes **how to apply** the scripts for[ web server & IIIF image server installation](#web-server-iiif-image-server-installation) and [IIIF image conversion](#iiif-image-conversion).

If you are interested in a detailed explanation of the scripts, please take a look at full version of the [IIIF Image Conversion Guide](IIIF%20Image%20Conversion%20Guide.md)

- [1 What is IIIF Image Conversion?](#key-1-what-is-iiif-image-conversion)
  - [1.1 Who is the training for image conversion aimed at?](#key-1-1-who-is-the-training-for-image-conversion-aimed-at)
  - [1.2 What will you learn in this training?](#key-1-2-what-will-you-learn-in-this-training)
  - [1.3 How will you learn this?](#key-1-3-how-will-you-learn-this)
  - [1.4 What will you need?](#key-1-4-what-will-you-need)
- [2 Image Conversion](#key-2-image-conversion)
- [3 Memory consumption](#key-3-memory-consumption)

# **1 What is IIIF Image Conversion?**

IIIF image conversion is the process of changing your original images to a multi-resolution format (e.g. TIFFs) to make them IIIF compatible and at the same time store them on an IIIF image server. The goal is to implement the IIIF APIs as described on the [IIIF website](https://iiif.io/get-started/how-iiif-works/) and thus enhance the possibilities of working with your images in an interoperable way.

## 1.1 Who is the training for image conversion aimed at?

To take advantage of the IIIF framework, your images need to be available in multi-resolution format on a web server and a IIIF-compliant image server.

Generally, content providers have web servers where their images can be accessed on the Internet. To implement the IIIF standard for these images, it is necessary to install an IIIF compatible image server and to convert the images to multi-resolution format.

Europeana aggregators may support their content providers in adapting to the IIIF framework. They can do this by guiding their content partners through the process of image preparation with the help of this guide. Most importantly, they can make the content providers aware of the two scripts available [IIIF Image Conversion Guide](IIIF%20Image%20Conversion%20Guide.md).

## 1.2 What will you learn in this training?

In this training we will go through the process of image conversion to IIIF format as described in the [IIIF Image Conversion Guide](IIIF%20Image%20Conversion%20Guide.md). For providing the images on the Internet we use the [Apache web server](https://httpd.apache.org/) and the IIIF-compliant [IIPImage server](https://iipimage.sourceforge.io/documentation/server).

## 1.3 How will you learn this?

The workflow of image conversion is described step by step and the successful execution of each step can be verified using the included screenshots in this training.

## 1.4 What will you need?

For this training you will need a set of images (e.g. jpeg images) that you want to convert to multi-resolution format.

You could use your own images or download a test set of 10 images from here: [ConversionGuide_Images_TestSet.zip](https://europeana.atlassian.net/wiki/download/attachments/2355396609/ConversionGuide_Images_TestSet.zip?version=1&modificationDate=1688718814636&cacheVersion=1&api=v2).

We will use [Apache web server](https://httpd.apache.org/) and [IIPImage server](https://iipimage.sourceforge.io/documentation/server) in this training.

To follow all steps with your own images or the test set images, you must have successfully completed the installation of the Apache web server and the IIPImage Server. You can easily perform these two steps by running the [**iiif-install.sh**](https://github.com/AITProjectAssistant/OpenUp/tree/main/IIIF) script with administrator permissions. (see also [IIIF Image Conversion Guide](IIIF%20Image%20Conversion%20Guide.md))

At first you have to make the script executable:

```java
sudo chmod +x iiif-install.sh
```

![](https://europeana.atlassian.net/wiki/download/attachments/2355396609/f1_ict_sudoinstal.png?version=1&modificationDate=1688997902366&cacheVersion=1&api=v2)

Then you have to run the script in your terminal by simply typing:

```java
sudo ./iiif-install.sh
```

![](https://europeana.atlassian.net/wiki/download/attachments/2355396609/Figure14.png?version=1&modificationDate=1688715394750&cacheVersion=1&api=v2)

# 2 Image Conversion

To facilitate transport, the images are saved in a zip file so that they are not transferred individually, but all together. Your next step should be decompressing the zip file in your Home directory.

![](https://europeana.atlassian.net/wiki/download/attachments/2355396609/f2_ict_decompr.png?version=1&modificationDate=1688722760240&cacheVersion=1&api=v2)

After that, you have to move the [**iiif-image-converter.sh**](https://github.com/AITProjectAssistant/OpenUp/tree/main/IIIF) file into the folder with the decompressed images.

![](https://europeana.atlassian.net/wiki/download/attachments/2355396609/f3_ict_script.png?version=1&modificationDate=1688722935137&cacheVersion=1&api=v2)

Make the script executable with:

```java
sudo chmod +x iiif-image-converter.sh
```

![](https://europeana.atlassian.net/wiki/download/attachments/2355396609/f2_ict_sudoconv.png?version=1&modificationDate=1688998545380&cacheVersion=1&api=v2)

In your terminal, open the TestSet folder where your images and the script are located (**cd TestSet** if you are not already in that folder).

![](https://europeana.atlassian.net/wiki/download/attachments/2355396609/f2-1_ict_sudoconv.png?version=1&modificationDate=1688998623172&cacheVersion=1&api=v2)

And run the script from there by simply typing:

```java
./iiif-image-converter.sh. 
```

In the following screenshot you can see that during the execution of this script there is a corresponding TIFF image generated for every original image.

![](https://europeana.atlassian.net/wiki/download/attachments/2355396609/f4_ict_conv.png?version=1&modificationDate=1688723296194&cacheVersion=1&api=v2)

A better view example of the original versus corresponding tiff image is shown in the next figure. There you can see that the TIFF image consists of 3 layers that represent different resolutions of the original image.

![](https://europeana.atlassian.net/wiki/download/attachments/2355396609/f5_ict_image.png?version=1&modificationDate=1688723370031&cacheVersion=1&api=v2)

At the end of execution the script demands sudo password in order to move the generated TIFF images to the image server folder.

![](https://europeana.atlassian.net/wiki/download/attachments/2355396609/f6_ict_move.png?version=1&modificationDate=1688723524544&cacheVersion=1&api=v2)

After correctly entering the sudo password the script ends with no outputs in the terminal and the images are moved to the */var/www/iipimage-server* folder.   
To check if the images are really there, go to this folder and type *ls* into your terminal. The following output should be obtained.

![](https://europeana.atlassian.net/wiki/download/attachments/2355396609/f7_ict_check.png?version=1&modificationDate=1688724496224&cacheVersion=1&api=v2)

Now, you can access the images from the browser with a URL.   
For example, you can type into the browsers address bar: **http://localhost/iiif/15513\_4892.tif/full/400,/0/default.jpg**

![](https://europeana.atlassian.net/wiki/download/attachments/2355396609/f8_ict_browser.png?version=1&modificationDate=1688724655384&cacheVersion=1&api=v2)

The identifiers after .tif image in the URL represent the required image request that must be in the following order: region, size, rotation and quality. “The order of the parameters is also intended as a mnemonic for the order of the operations by which the service should manipulate the image content. Thus, the requested image content is first extracted as a region of the complete image, then scaled to the requested size, mirrored and/or rotated, and finally transformed into the colour quality and format. This resulting image content is returned as the representation for the URI. Image and region dimensions in pixels are always given as integer numbers. Intermediate calculations may use floating point numbers and the rounding method is implementation specific. Some parameters, notably percentages, may be specified with floating point numbers. These should have at most 10 decimal digits and  consist only of decimal digits and “.” with a leading zero if less than  1.0.”

In accordance with these guidelines, the image representation on your computer can be as follows ***http://localhost/iiif/15513\_4892.tif/full/100,70,120,140/90/gray.jpg***

With this url the region of the image consisting of pixels that have x coordinate between 100 and 140 and y coordinate between 70 and 120 is extracted. The extracted region is not scaled, and is returned at its full size (from size=full in url), rotated 90 degrees and in grayscale quality. The result of this url can be seen in the following figure.

![](https://europeana.atlassian.net/wiki/download/attachments/2355396609/f9_ict_browser2.png?version=1&modificationDate=1688724809107&cacheVersion=1&api=v2)

For all TIFF images the image server creates an info.json file that can be accessed via the browser address bar and contains all necessary information (image width and height, available qualities, formats etc.) about the corresponding image.

![](https://europeana.atlassian.net/wiki/download/attachments/2355396609/f10_ict_json.png?version=1&modificationDate=1688724929317&cacheVersion=1&api=v2)

With the adequate manifest you are able to access and view these images further with IIIF-compliant image viewers like [Mirador, Universal Viewer, OpenSeadragon etc.](https://iiif.io/get-started/iiif-viewers/)

# **3 Memory consumption**

The size of the resulting TIFF image depends on the size of the original image and the tiling parameter specified for the conversion. Our training test set includes 10 images, which together are 4.4 MB in size. The resulting TIFF images require significantly more disk space. In our case, each resulting TIFF image has a size between 1.9 and 7.8 MB, which adds up to a total of 52.8 MB. This is an increase of 1200%.
