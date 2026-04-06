---
tags:
  - '#apidocs'
---

# Dataset download and OAI-PMH service

Besides our main [Europeana APIs](#europeana-apis) for searching and retrieving metadata about objects, we also offer other methods for downloading and harvesting metadata that are better suited if you want to extract large amounts of data. On this page, you can explore the two available solutions.

If you want a full discrete dataset from a single data provider, or if you want just a snapshot of our data, then we suggest downloading object metadata from [our FTP server ](#our-ftp-server)as pre-generated compressed ZIP files.

If you want to be kept up-to-date as metadata is changed or if you already use harvesting software, then we recommend using our [Harvesting](#harvesting) solution using the OAI-PMH service. OAI-PMH serves your files in XML format, which is ideal for data processing activities, especially for digital cultural heritage research. For researchers who are used to working with semantic frameworks and tools such as [JENA](https://jena.apache.org/) and [SPARQL](https://www.w3.org/TR/rdf-sparql-query/), we also offer compressed zip files for download formatted in [Turtle](https://www.w3.org/TR/turtle/).

Before starting to use either of these options, please read our Introduction page on how data is structured into [Page not accessible (ID: 2385313809)], the [API Terms of Use](https://www.europeana.eu/en/rights/terms-of-use#Europeana-API) and [the Usage Guidelines for metadata](https://www.europeana.eu/rights/usage-guidelines-for-metadata).

- [Europeana’s FTP server](#europeana-s-ftp-server)

  - [FTP listing and file structure](#ftp-listing-and-file-structure)
  - [Example](#example)- [Accessing images in high resolution: downloading data](#accessing-images-in-high-resolution-downloading-data)
    - [List of datasets](#list-of-datasets)
      - [Legend:](#legend)
    - [Dataset structure](#dataset-structure)
- [OAI-PMH](#oai-pmh)

  - [Available requests](#available-requests)
  - [Structure and Format of the Data](#structure-and-format-of-the-data)
  - [Known limitations](#known-limitations)- [Console](#console)
    - [Roadmap and Changelog](#roadmap-and-changelog)

# Europeana’s FTP server

Our FTP server serves ZIP files containing the metadata of all objects in Europeana's repository, organised by dataset, readily available for bulk download. These files are generated on *Sunday evening each week*, which guarantees that the data is as up-to-date as possible.

### **FTP listing and file structure**

All the files are available on our FTP server at <ftp://download.europeana.eu/dataset/>. You can connect to an FTP server by using software programs like [FileZilla](https://filezilla-project.org/), or you can connect to an FTP server as a [Shared Network Location](https://www.howtogeek.com/272176/how-to-connect-to-ftp-servers-in-windows-without-extra-software/) or using the Command Prompt. If you are using a Linux OS, you can run the command: wget -m <ftp://download.europeana.eu/dataset/XML>

Europeana’s FTP server login credentials:

|           |                                        |
|:----------|:---------------------------------------|
| Host:     | <ftp://download.europeana.eu/dataset/> |
| User:     | anonymous                              |
| Password: | [leave blank]                          |
| Port:     | 21                                     |

Our FTP server is structured as follows:

- two top-level directories, ‘XML’ and ‘TTL’, split the data in RDF-XML format and in Turtle format respectively.
- Within those directories, every ZIP file has all of the metadata for each [Page not accessible (ID: 2385313809)] in Europeana, where the name of the file is the dataset identifier (e.g. 2021672.zip). Every ZIP file has a corresponding MD5 checksum file under the file extension .md5sum (e.g. 2021672.zip.md5sum) which can be used to validate the file upon download.
- In each compressed zip file there will be a file for each Europeana metadata record where the name of the file will be the [Page not accessible (ID: 2385313809)] in Europeana.

### **Example**

The data for the [Girl with the Pearl Earring from the Mauritshuis](http://data.europeana.eu/item/2021672/resource_document_mauritshuis_670) encoded using the RDF-XML format will be available at the following URL <ftp://download.europeana.eu/dataset/XML/2021672.zip>. To find to which dataset any record belongs, you can check the URL of the record (for the Girl with the pearl earring, the Europeana item URL is [https://www.europeana.eu/item/2021672/resource\_document\_mauritshuis\_670](https://www.europeana.eu/nl/item/2021672/resource_document_mauritshuis_670) ), or you can find the dataset name next to the field 'Collection Name' in the 'More Metadata' tab on the item page.

The FTP server will provide you with a ZIP file with the metadata for all the objects in the dataset with the dataset number '2021672' if you request the URL <ftp://download.europeana.eu/dataset/XML/2021672.zip>. Unzipping the ZIP File will give you an XML file for every digital cultural heritage object. You can find the metadata for the “Girl with the Pearl Earring” in the ZIP file with the ID of that object, 'resource\_document\_mauritshuis\_670' in the XML file named "resource\_document\_mauritshuis\_670.xml"

## Accessing images in high resolution: downloading data

To foster the reuse of the data that is published in Europeana as part of the Newspapers Thematic Collections, we make both the metadata and the full-text available for bulk download as compressed zip files. The metadata is available as [CC0](http://creativecommons.org/publicdomain/zero/1.0/) the same way as all the metadata exposed via the API (see [Terms of Use](https://www.europeana.eu/en/rights/terms-of-use)) while the full-text is available as [Public Domain Mark](http://creativecommons.org/publicdomain/mark/1.0/).

### List of datasets

The table below lists all the datasets that are published and available for download. If you are looking for the complete text of a Newspaper then we suggest using the (4) option, as opposed to using (3) where the trascription is partioned per page.

Given the fact that the files are very big and can take many hours to download, as an alternative to download directly via the browser, you can login to the FTP server at "[download.europeana.eu](http://download.europeana.eu/)" with username "anonymous". This will allow you to resume if the download gets stuck.

|  dataset number    |  Metadata[^1]                                                                                                                                                     |  Full-text (ALTO)[^2]                                                                                                                                                       |  Page level full-text (EDM)[^3]                                                                                                                                           |  Issue level full-text (EDM)[^4]                                                                                                                                                      |
|:-------------------|:------------------------------------------------------------------------------------------------------------------------------------------------------------------|:----------------------------------------------------------------------------------------------------------------------------------------------------------------------------|:--------------------------------------------------------------------------------------------------------------------------------------------------------------------------|:--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **9200300**        | [download](ftp://download.europeana.eu/newspapers/metadata/9200300.zip) <br/>  (229M) ([MD5](ftp://download.europeana.eu/newspapers/metadata/9200300.zip.md5sum)) | [download](ftp://download.europeana.eu/newspapers/fulltext/alto/9200300.zip) <br/>  (63G) ([MD5](ftp://download.europeana.eu/newspapers/fulltext/alto/9200300.zip.md5sum))  | [download](ftp://download.europeana.eu/newspapers/fulltext/edm/9200300.zip) <br/>  (116G) ([MD5](ftp://download.europeana.eu/newspapers/fulltext/edm/9200300.zip.md5sum)) | [download](ftp://download.europeana.eu/newspapers/fulltext/edm_issue/9200300.zip) <br/>  (113G) ([MD5](ftp://download.europeana.eu/newspapers/fulltext/edm_issue/9200300.zip.md5sum)) |
| **9200301**        | [download](ftp://download.europeana.eu/newspapers/metadata/9200301.zip) <br/>  (37M) ([MD5](ftp://download.europeana.eu/newspapers/metadata/9200301.zip.md5sum))  | [download](ftp://download.europeana.eu/newspapers/fulltext/alto/9200301.zip) <br/>  (13G) ([MD5](ftp://download.europeana.eu/newspapers/fulltext/alto/9200301.zip.md5sum))  | [download](ftp://download.europeana.eu/newspapers/fulltext/edm/9200301.zip) <br/>  (20G) ([MD5](ftp://download.europeana.eu/newspapers/fulltext/edm/9200301.zip.md5sum))  | [download](ftp://download.europeana.eu/newspapers/fulltext/edm_issue/9200301.zip) <br/>  (20G) ([MD5](ftp://download.europeana.eu/newspapers/fulltext/edm_issue/9200301.zip.md5sum))  |
| **9200338**        | [download](ftp://download.europeana.eu/newspapers/metadata/9200338.zip) <br/>  (213M) ([MD5](ftp://download.europeana.eu/newspapers/metadata/9200338.zip.md5sum)) | [download](ftp://download.europeana.eu/newspapers/fulltext/alto/9200338.zip) <br/>  (158G) ([MD5](ftp://download.europeana.eu/newspapers/fulltext/alto/9200338.zip.md5sum)) | [download](ftp://download.europeana.eu/newspapers/fulltext/edm/9200338.zip) <br/>  (278G) ([MD5](ftp://download.europeana.eu/newspapers/fulltext/edm/9200338.zip.md5sum)) | [download](ftp://download.europeana.eu/newspapers/fulltext/edm_issue/9200338.zip) <br/>  (277G) ([MD5](ftp://download.europeana.eu/newspapers/fulltext/edm_issue/9200338.zip.md5sum)) |
| **9200339**        | [download](ftp://download.europeana.eu/newspapers/metadata/9200339.zip) <br/>  (39M) ([MD5](ftp://download.europeana.eu/newspapers/metadata/9200339.zip.md5sum))  | [download](ftp://download.europeana.eu/newspapers/fulltext/alto/9200339.zip) <br/>  (11G) ([MD5](ftp://download.europeana.eu/newspapers/fulltext/alto/9200339.zip.md5sum))  | [download](ftp://download.europeana.eu/newspapers/fulltext/edm/9200339.zip) <br/>  (21G) ([MD5](ftp://download.europeana.eu/newspapers/fulltext/edm/9200339.zip.md5sum))  | [download](ftp://download.europeana.eu/newspapers/fulltext/edm_issue/9200339.zip) <br/>  (17G) ([MD5](ftp://download.europeana.eu/newspapers/fulltext/edm_issue/9200339.zip.md5sum))  |
| **9200355**        | [download](ftp://download.europeana.eu/newspapers/metadata/9200355.zip) <br/>  (212M) ([MD5](ftp://download.europeana.eu/newspapers/metadata/9200355.zip.md5sum)) | [download](ftp://download.europeana.eu/newspapers/fulltext/alto/9200355.zip) <br/>  (97G) ([MD5](ftp://download.europeana.eu/newspapers/fulltext/alto/9200355.zip.md5sum))  | [download](ftp://download.europeana.eu/newspapers/fulltext/edm/9200355.zip) <br/>  (159G) ([MD5](ftp://download.europeana.eu/newspapers/fulltext/edm/9200355.zip.md5sum)) | [download](ftp://download.europeana.eu/newspapers/fulltext/edm_issue/9200355.zip) <br/>  (157G) ([MD5](ftp://download.europeana.eu/newspapers/fulltext/edm_issue/9200355.zip.md5sum)) |
| **9200356**        | [download](ftp://download.europeana.eu/newspapers/metadata/9200356.zip) <br/>  (137M) ([MD5](ftp://download.europeana.eu/newspapers/metadata/9200356.zip.md5sum)) | [download](ftp://download.europeana.eu/newspapers/fulltext/alto/9200356.zip) <br/>  (40G) ([MD5](ftp://download.europeana.eu/newspapers/fulltext/alto/9200356.zip.md5sum))  | [download](ftp://download.europeana.eu/newspapers/fulltext/edm/9200356.zip) <br/>  (17G) ([MD5](ftp://download.europeana.eu/newspapers/fulltext/edm/9200356.zip.md5sum))  | [download](ftp://download.europeana.eu/newspapers/fulltext/edm_issue/9200356.zip) <br/>  (17G) ([MD5](ftp://download.europeana.eu/newspapers/fulltext/edm_issue/9200356.zip.md5sum))  |
| **9200357**        | [download](ftp://download.europeana.eu/newspapers/metadata/9200357.zip) <br/>  (23M) ([MD5](ftp://download.europeana.eu/newspapers/metadata/9200357.zip.md5sum))  | [download](ftp://download.europeana.eu/newspapers/fulltext/alto/9200357.zip) <br/>  (5G) ([MD5](ftp://download.europeana.eu/newspapers/fulltext/alto/9200357.zip.md5sum))   | [download](ftp://download.europeana.eu/newspapers/fulltext/edm/9200357.zip) <br/>  (9G) ([MD5](ftp://download.europeana.eu/newspapers/fulltext/edm/9200357.zip.md5sum))   | [download](ftp://download.europeana.eu/newspapers/fulltext/edm_issue/9200357.zip) <br/>  (9G) ([MD5](ftp://download.europeana.eu/newspapers/fulltext/edm_issue/9200357.zip.md5sum))   |
| **9200396**        | [download](ftp://download.europeana.eu/newspapers/metadata/9200396.zip) <br/>  (4M) ([MD5](ftp://download.europeana.eu/newspapers/metadata/9200396.zip.md5sum))   | [download](ftp://download.europeana.eu/newspapers/fulltext/alto/9200396.zip) <br/>  (849M) ([MD5](ftp://download.europeana.eu/newspapers/fulltext/alto/9200396.zip.md5sum)) | [download](ftp://download.europeana.eu/newspapers/fulltext/edm/9200396.zip) <br/>  (2G) ([MD5](ftp://download.europeana.eu/newspapers/fulltext/edm/9200396.zip.md5sum))   | [download](ftp://download.europeana.eu/newspapers/fulltext/edm_issue/9200396.zip) <br/>  (1G) ([MD5](ftp://download.europeana.eu/newspapers/fulltext/edm_issue/9200396.zip.md5sum))   |

#### Legend:

1. The original metadata in EDM XML format before being ingested into Europeana. There are slight differences between this data and the one published. For more information see the [Page not accessible (ID: 2385313809)].
2. The full-text encoded using ALTO (Analyzed Layout and Text Object) as it was delivered to Europeana. The ALTO is an open XML Schema meant to describe text coming from OCR and layout information of pages for digitized material. For more information see the [official documentation page at the Library of Congress](https://www.loc.gov/standards/alto/about.html).
3. The full-text encoded using the [EDM profile for IIIF fullltext](https://docs.google.com/document/d/1t5yGEzQ0KV2rqU0sFDoKnI2bIDBGrmj0f1gSOCRUgJ4) after being preprocessed for publication in Europeana. A note that as opposed to the format used by the API (ie. JSON-LD), the data is in RDF/XML as it is the format used for ingestion into Europeana.
4. Very similar to (3) but wih the full-text represented at the Issue level. This means that the edm:FullTextResource will convey the complete transcription of the Newspaper.

### Dataset structure

On each compressed zip file, there will typically be a file per each item (ie. metadata or issue level full-text) or page (ie. ALTO and page level full-text) with the following structure:

|      |                                    |
|:-----|:-----------------------------------|
| Item | DATASET\_ID/LOCAL\_ID.xml          |
| Page | DATASET\_ID/LOCAL\_ID/PAGE\_ID.xml |

That structure can be translated into links to the Europeana Collection portal where the item can be displayed or into the several APIs described on this page.

# OAI-PMH

The Europeana OAI-PMH Service offers a way to collect large amounts of Europeana data from our repository through a protocol named [OAI-PMH](http://www.openarchives.org/OAI/openarchivesprotocol.html) (Open Archives Initiative Protocol for Metadata Harvesting, presently in v2.0). This service allows you to harvest the entirety of our database or a selection of our database. You can select which parts of the Europeana database to download by specifying which datasets you want to download, or by filtering on the date of creation or date of modification of the data.

You can learn more about the harvesting protocol on the [Open Archives Initiative](http://www.openarchives.org/) (OAI) website and also by reading the [OAI for beginners tutorial](https://www.oaforum.org/tutorial/) from the Open Archives Forum.

### **Available requests**

Below you can find the available requests. The **base URL** for all requests is [https://api.europeana.eu/oai/record/](https://api.europeana.eu/oai/record). These links and requests return XML, for which you need to use an XML-aware browser or viewing application.

List of available requests defined by the OAI-PMH protocol:

- [Identify](https://api.europeana.eu/oai/record/oaicat/identify.shtml)
- [GetRecord](https://api.europeana.eu/oai/record/oaicat/getRecord.shtml)
- [ListIdentifiers](https://api.europeana.eu/oai/record/oaicat/listIdentifiers.shtml) ([Resumption](https://api.europeana.eu/oai/record/oaicat/listIdentifiersResumption.shtml))
- [ListMetadataFormats](https://api.europeana.eu/oai/record/oaicat/listMetadataFormats.shtml)
- [ListRecords](https://api.europeana.eu/oai/record/oaicat/listRecords.html)([Resumption](https://api.europeana.eu/oai/record/oaicat/listRecordsResumption.html))
- [ListSets](https://api.europeana.eu/oai/record/oaicat/listSets.html) ([Resumption](https://api.europeana.eu/oai/record/oaicat/listSetsResumption.html))

### **Structure and Format of the Data**

The records in the OAI-PMH service are grouped into [Datasets](https://pro.europeana.eu/page/intro#edm) and are available as EDM RDF/XML. An example of a dataset ID that is accepted by the OAI-PMH service is 2022608\_Ag\_NO\_ELocal\_DiMu. The records are identified by their URIs. An example of such an identifier is <http://data.europeana.eu/item/2022608/AAK_AAKS_2007_02_0206>. To learn more about <http://data.europeana.eu> and its resources please see the [Page not accessible (ID: 2385313809)].

### **Known limitations**

Europeana currently doesn't maintain a deleted record registry. Therefore we recommend you re-harvest or download the entire collection at least every six months to ensure your copy of the Europeana repository is up-to-date.

## Console

(temporarily removed the Swagger console because it has an issue causing a very high CPU load)

### **Roadmap and Changelog**

We deploy new versions of the service primarily to fix any outstanding issues or introduce new features. The current version of the OAI-PMH Service is 0.8 Beta (2020-10). To see the changes made for this version and also all previous releases, see the [API changelog in the project GitHub](https://github.com/europeana/OAI-PMH2/releases).
