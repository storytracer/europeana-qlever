---
tags:
  - '#apidocs'
---

[Europeana APIs Documentation](../Europeana%20APIs%20Documentation.md)

# Libraries and Plugins

Interacting with the [Europeana REST API](https://pro.europeana.eu/page/intro) is possible in a multitude of ways, the easiest of which is probably a [Console](https://pro.europeana.eu/page/intro#console). If you want to use your coding language of choice to interact with an API, there are a few different code libraries that can help you access and use the API in exactly the way you want. Below is a list of libraries and plugins for the Europeana API, sorted by coding language/software suite.

![](../../attachments/d80a7df5-8ab3-4e8c-806e-a62ccfd5ad2c.png)

- [Python Libraries](#python-libraries)
- [Java Libraries](#java-libraries)
- [Node.JS Libraries](#node-js-libraries)
- [Plugins](#plugins)

## Python Libraries

### PyEuropeana

PyEuropeana is a library that provides streamlined functions to interact with several of Europeana's APIs through Python. It was first created in 2020 and is currently being actively maintained. It can easily be installed as a pip package, and has comprehensive and clear documentation. The PyEuropeana library gives access to:

- [Search](https://pro.europeana.eu/page/search): for finding objects giving a query
- [Record](https://pro.europeana.eu/page/record): for finding metadata about a given object
- [Entity](https://pro.europeana.eu/page/entity): for finding metadata about entities (agents, concepts, places, timespans)
- [IIIF](https://pro.europeana.eu/page/iiif): for finding content and metadata of documents following the IIIF standard

Get [access to PyEuropeana via GitHub](https://www.google.com/url?q=https://github.com/europeana/rd-europeana-python-api&sa=D&source=docs&ust=1695057810605366&usg=AOvVaw06mKHR8vEU_CCz5YarngZq)

## Java Libraries

### REPOX

REPOX is a framework to manage metadata spaces developed in Java. It comprises several channels to import metadata from data providers, services to transform metadata between schemas according to user's specified rules, and services to expose the results to the exterior. REPOX aims to provide to all the TEL and Europeana partners a simple solution to import, convert and expose their bibliographic data via [OAI-PMH](https://pro.europeana.eu/page/oai-pmh-service). It was developed along EuropeanaConnect, Europeana Local, and Europeana Libraries projects. All code is available openly licensed (EUPL v.1.1) on [GitHub](https://github.com/europeana/REPOX). You can also find more information on the [Original REPOX website](http://repox.sysresearch.org/) or on the [REPOX Wiki](https://github.com/europeana/REPOX/wiki).

### Entity API library

This Java library for the [Entity API Documentation](API%20Suite/Entity%20API%20Documentation.md) V2 is published by [AIT](https://www.ait.ac.at/) and maintained by Europeana staff. Access it on [Github](https://github.com/europeana/entity-api-client-v2-java).

## Node.JS Libraries

### Node.JS module

This unofficial Node.js module for the Europeana API was published as public domain code. You can install it through npm with the command `npm install europeana`. All code is available openly licensed and via [GitHub](https://github.com/fvdm/nodejs-europeana) or find this module on [**npm**.](https://www.npmjs.com/package/europeana)

## Plugins

### Open in IIIF viewer

A Firefox andChrome extension to open a IIIF manifest link in your favorite IIIF viewer. When the web page you are browsing contains a link to a IIIF manifest, by clicking on the toolbar button of this extension, you can open the link in the IIIF viewer specified on the options page. Find the plugin on [Firefox](https://2sc1815j.net/open-in-iiif-viewer/open_in_iiif_viewer.xpi), [Chrome](https://chrome.google.com/webstore/detail/pdkbceoglenaneaoebcagpbkocpkhajl), or on [Github](https://github.com/2SC1815J/open-in-iiif-viewer).
