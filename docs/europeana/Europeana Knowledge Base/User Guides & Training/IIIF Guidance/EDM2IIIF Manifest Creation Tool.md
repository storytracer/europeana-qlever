---
tags:
  - '#iiif'
---

# EDM2IIIF Manifest Creation Tool

The Europeana Natural History Aggregator OpenUp! has published an online tool that supports the automated creation of IIIF manifests out of uploaded EDM metadata.

This guide describes in detail **how to use the tool** and what it delivers.

The tool is currently available in **version 1**, i.e. it supports the conversion of EDM metadata for **digital images** hosted in IIIF compliant image servers. Subsequent versions will integrate the creation of IIIF manifests for audio and video data.

The tool is realised in co-operation with Europeana and uses the same IIIF mapping as Europeana. For more information on the mapping see [chapter 9](#chapter-9) of this guide.

- [1 Goal of the EDM2IIIF Manifest Creation tool v01](#key-1-goal-of-the-edm2iiif-manifest-creation-tool-v01)
- [2 Where to find the EDM2IIIF Manifest Creation tool](#key-2-where-to-find-the-edm2iiif-manifest-creation-tool)
- [3 How to prepare your dataset](#key-3-how-to-prepare-your-dataset)
- [4 General interface elements](#key-4-general-interface-elements)
  - [4.1 The Welcome screen](#key-4-1-the-welcome-screen)
  - [4.2 The Home screen](#key-4-2-the-home-screen)
    - [4.2.1 Input fields](#key-4-2-1-input-fields)
    - [4.2.2 Buttons](#key-4-2-2-buttons)
- [5 Upload a new dataset](#key-5-upload-a-new-dataset)
  - [5.1 Data input](#key-5-1-data-input)
  - [5.2 The harvest protocol](#key-5-2-the-harvest-protocol)
    - [5.2.1 OAI-PMH](#key-5-2-1-oai-pmh)
    - [5.2.2 Zip file](#key-5-2-2-zip-file)
- [6 Track dataset processing](#key-6-track-dataset-processing)
- [7 Record report](#key-7-record-report)
- [8 Data Download](#key-8-data-download)
- [9 Manifest Creation](#key-9-manifest-creation)
- [10 EDM enrichment](#key-10-edm-enrichment)
- [11 Troubleshooting](#key-11-troubleshooting)
- [Samples](#samples)
  - [Original EDM (from OAI provider)](#original-edm-from-oai-provider)
  - [.json Manifest](#json-manifest)
  - [Enriched EDM](#enriched-edm)

# 1 Goal of the EDM2IIIF Manifest Creation tool v01

This guide introduces you to the [EDM2IIIF Manifest Creation Tool](http://openup.ait.co.at/edm2manifest/). It was initially created as a successor of the [Image Conversion Guide](http://openup.ait.co.at/wp-content/uploads/2023/08/EF-IIIF-Image-Conversion-Guide-110723-081947.pdf) to facilitate the workflow towards making your digital images IIIF compliant.

[IIIF](https://iiif.io/) stands for [International Image Interoperability Framework](https://iiif.io/) (spoken Triple-Eye-F). The framework was created to offer the scientific community a way to productively interact with their digital objects (visual or audio/visual) and use them across different platforms. [Here you can learn about the benefits of IIIF](https://iiif.io/get-started/why-iiif/).

If you are looking for a general introduction to the IIIF framework, please check out the [What is IIIF?](https://training.iiif.io/europeana/index.html) training resources for aggregators.

When deciding to use the IIIF standard for publishing your images on the internet there are a few obstacles to take, because: the more images you want to convert and equip with the Image API and the Presentation API, the more time you will have to invest to create IIIF compliant images and manifests. (A [IIIF manifest](https://library.harvard.edu/services-tools/iiif-manifests-digital-objects) is the package that contains all the information related to a particular digital object, including the image itself as well as the metadata.) The manifest creation tool aims to make this process less time-consuming by automating the creation of IIIF manifests for your images.

With this tool you can:

1. use EDM metadata (of **IMAGE** type - cultural heritage objects) to automatically create **IIIF manifests for images** and enrich the **EDM metadata with IIIF descriptions**
2. download the IIIF manifests that were created based on your EDM metadata (about manifest creation details see chapter 9)
3. download the enriched EDM metadata with IIIF descriptions (about enrichment of EDM details see chapter 10)

# 2 Where to find the EDM2IIIF Manifest Creation tool

The EDM2IIIF Manifest Creation Tool can be accessed through <https://openup.ait.co.at/edm2manifest/> *.*

This tool was developed in the **Python** programming language, using the **Flask** framework. To use this tool, the user only needs Internet connection and a browser.

# 3 How to prepare your dataset

In order to use the EDM2IIIF Manifest Creation tool you have to **prepare** your data appropriately. You need to verify that your dataset can be used with the tool before proceeding. Several considerations must be made:

- Your IIIF images **should** be stored in the correct location on the image server, because you need to enter your IIIF service base URL as input to the tool. (N.B. The process of generating the IIIF service URL is described in the [IIIF Image Conversion Guide](http://openup.ait.co.at/wp-content/uploads/2023/08/EF-IIIF-Image-Conversion-Guide-110723-081947.pdf).) “Correct location” in this context means: a folder with your IIIF images which the web server makes accessible through the URL address.
- Your EDM metadata records **must** to follow the Europeana Data Model specifications. You can find more information about EDM in the [Documentation](https://pro.europeana.eu/page/edm-documentation).
- Your dataset **must** be uploaded using the [OAI-PMH](https://www.openarchives.org/OAI/openarchivesprotocol.html) protocol or a zip file.

# 4 General interface elements

Below is a list of the general interface elements and their uses.

## 4.1 The Welcome screen

The default screen, the screen you land on when navigating to the tool is the Welcome screen.

![](https://europeana.atlassian.net/wiki/download/attachments/2517368849/AD_4nXcCd8j_Qcom7HELNTojtuJCcLSk_mTMJuAfkqe7LnvBHXdvdMSQ6_SiEGdTw0fW1_Q2mRJPfrf9FXTCFzWJW3Gwusa9G3_5LFtlIPdt6LGgNcxHi436GE5MpHE1kQ_3orAPcqgfMEHlt2et9LMo1U5LeF_6%3Fkey=yDJ2wl4wJcrsr0iw5AUDmg?version=1&modificationDate=1718707401052&cacheVersion=1&api=v2)

You can click ‘Start’ to navigate to the Home screen (see section below).

## 4.2 The Home screen

This screen allows you to start accessing the EDM2IIIF Manifest Creation tool. Here you can track existing data or initiate a new upload. It looks like this:

![](https://europeana.atlassian.net/wiki/download/attachments/2517368849/AD_4nXcDoHDShFIcHrXyg__buHHznDwy4N2iImVTL0l1UXCj_df9mhoR9vIVvmv6U52AMWgV-5giHj8m_dgokRe3RZz5DJh-5TejOPHRbIf2_ogf6PpNYKTUX9JiY5122DkML9IST9KMb2WOb9lCfIOLAZ2FMYmt%3Fkey=yDJ2wl4wJcrsr0iw5AUDmg?version=1&modificationDate=1718707401075&cacheVersion=1&api=v2)

### 4.2.1 Input fields

The input fields are the white boxes where information must be entered by you. The description above the input field states what information should be entered. Every input field comes with a possible input example. **Each field is mandatory**.

![](https://europeana.atlassian.net/wiki/download/attachments/2517368849/AD_4nXdOT_CScNtGIJYxqZMIIE2x9SY7vU18JwMAf6WWFeKPUdAixMuuVVEpx1X8eJ8_659piQJ7OCfsKZ2Mu5hSHNt1y1Rbqt8dC8B8iQ4Aj1z9gfbvrTFG3NHCdlgcQEu9UGK4n28xLJ8b8gamhFYKwZ3-cwE%3Fkey=yDJ2wl4wJcrsr0iw5AUDmg?version=1&modificationDate=1718708629109&cacheVersion=1&api=v2)

### 4.2.2 Buttons

The radio buttons are used to select the upload method to upload EDM metadata records through OAI-PMH or file upload and to download the resulting manifests and enriched EDM data:

![](https://europeana.atlassian.net/wiki/download/attachments/2517368849/AD_4nXcOaRuCGpPEHU5NL4IuyObdoXSX9DExfAGbIAEt9wkgDXCcDJpxZy-I1bm7SxyX-4mI6ppPqohRGHq9oRCA0003oRqndBnd0fAu5lBnYllaGcX8HtYsh2cBb_gFPqF74LTOCx6476IbhevPRWT21h9MQjjj%3Fkey=yDJ2wl4wJcrsr0iw5AUDmg?version=1&modificationDate=1718708629128&cacheVersion=1&api=v2)

…or to refresh your harvesting results.

![](https://europeana.atlassian.net/wiki/download/attachments/2517368849/AD_4nXcddzcJf5ESKETAbJhtPXB8zqe-VYNFnnoGEWIBxCEGZM5oADwVtNEiLzGNgn1jlL9MwmaAiHp2kOHE9Ibqwo5rZdVD9y_WSiAZiBA9MmSXks7aSo2OTydhCeT74uTpXxBbynFi6SVe0N2QywER1L8Uey0%3Fkey=yDJ2wl4wJcrsr0iw5AUDmg?version=1&modificationDate=1718708629136&cacheVersion=1&api=v2)

# 5 Upload a new dataset

The EDM2IIIF Manifest Creation tool was implemented as an open web service. Therefore it is not possible yet to create a user account (this may be implemented in v02). When uploading your EDM metadata records you have to make sure to choose a **unique** name for the upload. If the name already exists, you will be requested to confirm the override of the previous set. Please try not to delete other uploads by choosing the same name.

![](https://europeana.atlassian.net/wiki/download/attachments/2517368849/AD_4nXeW5XJr66yqi0l7WgMui2ALxuXneIdNRWrCOXIjAsiHUGMYrk9rk2Kvpq2EmTWBn__yMdGahSDSU-yi9CS4LXPofWF6HTceEH7fFerdZgMGoG51qh1dhtWspAYUcIgyYkcFlYyuhJVNUOVA3eXXJyHTzVVE%3Fkey=yDJ2wl4wJcrsr0iw5AUDmg?version=1&modificationDate=1718708629143&cacheVersion=1&api=v2)

## 5.1 Data input

This screen allows you to start accessing the EDM2IIIF Manifest Creation tool. Here you can track existing data or initiate a new upload. The “Upload Data” form looks like shown in the figure below and can at the same time be used to track or later download a previous dataset.

![](https://europeana.atlassian.net/wiki/download/attachments/2517368849/AD_4nXcWrj1sMVZRFpbxjJsngxjgLtdLoF0vaBzsMKTd5xiXMjvrHAByFPwzzhWTICoFosuQNIndgJvwymFW9dHFViZHEnCx9amNjK1qcS_ySbqGt8iMYIV42CtI4gUaKRfmnqQfZw9HAvXbKBW1fXD6VxZ56KNM%3Fkey=yDJ2wl4wJcrsr0iw5AUDmg?version=1&modificationDate=1718708629150&cacheVersion=1&api=v2)

1. *Dataset Name Input*: used to enter the **unique** name of a new dataset you want to **create** or a previously uploaded dataset you want to **track.**
2. *Base URL for images*: used to enter the base URL for your **IIIF images**.
3. *Base URL for manifests*: used to enter the base URL where you want to store your resulting **IIIF manifests**.
4. *OAI-PMH upload:* this box opens an input field for your **OAI-PMH link**.
5. *File upload:* this box opens an input field for uploading your EDM records via **zip file.**
6. *Track dataset:* this box enables **tracking** the status as well as **downloading** the created manifests and enriched EDM records.

First, enter a descriptive name for your dataset in the input field “Name”. The next step is to set the base URLs (where they are/will be located) for both the IIIF images and the IIIF manifests. We suggest taking the pre-filled URLs as an example.

The next step is to determine the “Harvest protocol”: how you want to upload your dataset. This is described in detail below. The “Submit” button at the bottom will be enabled when all information is filled in.

## 5.2 The harvest protocol

There are two ways to upload your datasets to the EDM2IIIF Manifest Creation tool:

1. *OAI-PMH upload:* Ingestion with OAI-PMH
2. *File upload:* upload a zip file

The “Submit” button will become enabled once you have filled all fields. Click the **“Submit”** button to upload your dataset. To track and download your data, see [chapter 6](https://docs.google.com/document/d/1SuP92OntkH8P4teScm0zv_AfK054McX-Us-yLd9qrM4/edit#heading=h.4c2sgjnnrgp1).

If the upload has been successful, a green information window will appear (see following paragraphs).

### 5.2.1 OAI-PMH

To use the harvesting protocol OAI-PMH, you should enter an URL for harvesting your data. The URL of your OAI-PMH should look like this:

![](https://europeana.atlassian.net/wiki/download/attachments/2517368849/AD_4nXdlHgJTh2KDZVrAhFaLWr5T652tbm4mPm6wNhpNZ6I_mM4xBIK5crWVaQJRsjLPUlbnLNNCz-wb3PCVfvxKLmRXub-BL6HyJ4tiQE2_y3NhswnsuYfXWrduB3wpPDpHalmdCRyCjoNpnQf05FbQx_weCOw%3Fkey=yDJ2wl4wJcrsr0iw5AUDmg?version=1&modificationDate=1718708629157&cacheVersion=1&api=v2)

For more details on the appearance of the URL, please see the [OAI-PMH specifications](https://www.openarchives.org/OAI/openarchivesprotocol.html).

If the upload of your data was successful, the following message appears:

![](https://europeana.atlassian.net/wiki/download/attachments/2517368849/AD_4nXemiFRkgH5vjerzhl80ztFfJd6pvD0O_I1yy9qiQHc_hNkIT_S8g0QZeccLonwNXB2zZWztD_lQhKFH5Mi3cGX_ajW9YlA1YA2qGNNvDgLrn5htuECcMOA825Mm7kfuqcSqGIji0XJSfq4QLGxpfOxGuWs%3Fkey=yDJ2wl4wJcrsr0iw5AUDmg?version=1&modificationDate=1718708629165&cacheVersion=1&api=v2)

### 5.2.2 Zip file

This option allows you to upload a zip file with an EDM dataset (xml files) that is stored locally. Click on “Durchsuchen” (or “Search”; depending on the language setting on your computer) and choose the zip file with your data. It is important to know that only files with the ending .zip can be uploaded successfully.

![](https://europeana.atlassian.net/wiki/download/attachments/2517368849/AD_4nXcxma4QbtxKpDrmp6QLWAlvZ1kOvC80FuTRKsB3SeaVwvN1_KZzjinQ3cHzxA1AKLysjZsFt_VQ9EcxQQuCRj1tko6WRA5Jg0Qjt_46thuYAF1jTdQ5xnoaySylkkhdPBL1HArD3s9UnfC0Pq8Bb6ndSmk%3Fkey=yDJ2wl4wJcrsr0iw5AUDmg?version=1&modificationDate=1718708629173&cacheVersion=1&api=v2)

If the upload of your data was successful, the following message appears:

![](https://europeana.atlassian.net/wiki/download/attachments/2517368849/AD_4nXfxr9aXaxQ6SbRwbB0EWhmJ8s2qNBSNcA-Cx2oNXIkzgAN-CpIBb_Qk3n5wzk0k40imT7dcWcbSoB9QFGykl0xm4-nm6H_R9s9wrhKnmtZMFB2J_a-o2aK9YUMyRho5K6yUK9mlD26kcEQLOJeTDejrk4I%3Fkey=yDJ2wl4wJcrsr0iw5AUDmg?version=1&modificationDate=1718708629181&cacheVersion=1&api=v2)

# 6 Track dataset processing

After successfully submitting your dataset to be processed, the status can be checked in the following steps:

1. Enter dataset name
2. Choose *Track/download harvested dataset* as harvest protocol
3. Click the *Submit* button

As a result of the above steps, the new page with the harvest details will be opened. The following figure shows what the resulting page looks like. While the process is not completed, the "Refresh" button is enabled in the "Results" column.

![](https://europeana.atlassian.net/wiki/download/attachments/2517368849/AD_4nXdM22AR0SAtWQyp1t1fHc_tK9M3EmzSm78MPEJ3I4BaMNPySp5VMEtrXZKsaD1cSzr3a1Nz2PTjjHBV6BUdUTVLW2M5GBltKxiBLqrDqTskAkKYkOjqN-HVqHvNUxNCSTCBNlA_zP_CSZPvCwS7SJ8bnF4h%3Fkey=yDJ2wl4wJcrsr0iw5AUDmg?version=1&modificationDate=1718708629189&cacheVersion=1&api=v2)

When the process of data harvest is complete, the "Download" button becomes available (see figure below), which allows to download the resulting manifests, the enriched EDMs and the log.json file, with all of them compressed into a zip file.

![](https://europeana.atlassian.net/wiki/download/attachments/2517368849/AD_4nXfJ4HDXVhAtpdl8eNdGInHyuuiBb-uCEtvdX9iZnLYuRDEKOG0DUma8ekqz0iSW98b4ip-LC0jsdTvE4uclUxN2bxNQ9Jw04UMxB6HR31dDDeVbPrrTnTE_9LBR75tZFwBVd_4p5c8mU0q6RS-0lKyQ0xBI%3Fkey=yDJ2wl4wJcrsr0iw5AUDmg?version=1&modificationDate=1718708629197&cacheVersion=1&api=v2)

The log.json file can also be downloaded from the "Process Info" column at any time so that you know what is happening with the processing of the records. More details about this file are provided in the next chapter.

# 7 Record report

The log.json file, which can be downloaded from the project results page, contains information about the records that could be:

1. "**OK**" indicates that the EDM record has been successfully processed and the IIIF manifest and corresponding enriched EDM have been created for this record.

![](https://europeana.atlassian.net/wiki/download/attachments/2517368849/AD_4nXdl2esqWqM7l1Fq0MH7D9DT9Kap04_rtd9vAO4BlukRG-XMkSzkppGtj2QQ8TpfAOypef1-fGYZ5UqePMEDb087PlpFHy_9Z49Xy5uFn8llW4njcmf7FWzC0p8Il9r1ygRwyMlOVmrEXJrrIr-5_QEeJ3S1%3Fkey=yDJ2wl4wJcrsr0iw5AUDmg?version=1&modificationDate=1718708924148&cacheVersion=1&api=v2)

2. An "**Error**" with error details indicates the EDM record processing cannot be performed due to this error and its IIIF manifest and enriched EDM are not provided.

![](https://europeana.atlassian.net/wiki/download/attachments/2517368849/AD_4nXe9baY0oJd8dYp0sEFEdJuDssJzPvgRfpnQrzk-iy0p0dEoiH1tMN982N_4oxk4lAq-cnPAoE1_8gvqoGB4c1Ukw5uap2diGfzi5FOH8DzsZITH_ZWAeGWG5m9VlmApiU9w4kOcfh7KEfsc17l_T6SqSVc%3Fkey=yDJ2wl4wJcrsr0iw5AUDmg?version=1&modificationDate=1718708924169&cacheVersion=1&api=v2)

3. A "**Warning**" indicates that there are problems processing the EDM record, but the IIIF manifest and enriched EDM are still generated. It warns you of a problem that you can fix in the future to make processing the record more efficient.

![](https://europeana.atlassian.net/wiki/download/attachments/2517368849/AD_4nXf261ywu2szhR0qy_fsF0SbzPe0-vffx2Qhyd2nlRa_f-JiNgBLlUfc6a_rNuDCugO4x4iygcva26oT3mX8WpoRmlz-oLHT6zeoHwY9BGq3VGOaK6EovCcspPtxiz0wxdyh7BU0tEsn7_l_SXzHvCR2yY_B%3Fkey=yDJ2wl4wJcrsr0iw5AUDmg?version=1&modificationDate=1718708924180&cacheVersion=1&api=v2)

# 8 Data Download

Your data can be downloaded through the already mentioned “Download” button on the EDM2IIIF Results page when the status changes to “**done**” This automatically induces the download of a zip file with separate zip files for the IIIF manifests, the enriched EDMs and log.json file as shown below.

![](https://europeana.atlassian.net/wiki/download/attachments/2517368849/AD_4nXf3dhfyeRnYfUD5m_bpTbBHIdbII2tbKTJE9_F4A5ShOrf5-IFNXfmlQ8hGmKKAE2uCEZgs9-VMEbBFcsf_GRleHRbtYK75uGDXJAIh1lBqh9OrHypgkv3KrEL0zjdNTbQ41zN5sG6EgQgWa-0OBpcerDtD%3Fkey=yDJ2wl4wJcrsr0iw5AUDmg?version=1&modificationDate=1718708924188&cacheVersion=1&api=v2)

After downloading your created manifests, there is one last step to make them accessible: You have to make sure that you unzip the manifests in the correct folder on your server. In our case we would have to store the IIIF manifests in the folder "manifests" on the server "my.IPADDRESS". The storage place **must** match the path in the service base URL for manifests that you had entered in the upload form.

# 9 Manifest Creation

For each EDM record, a corresponding IIIF manifest is created and saved as an xml file. For example, if the user provides ten valid EDM records and enters the correct IIIF service base URL for those records, ten manifest xml files are created. The name of each manifest xml file is derived from the name of the corresponding tif image on the image server and looks like this: “manifest\_ID.json”

The name of the image itself (which replaces ‘ID’) is derived from the element edm:isShownBy, which points to the image on the website of the data provider.

All data required to create the manifest is extracted from the EDM metadata of the record and stored in the appropriate manifest fields. For more information about IIIF manifest fields, see [here](https://iiif.io/api/presentation/3.0/).

In general, the data required to create a manifest is:

- Accessible IIIF images - the image or object in general that is determined from the *isShownBy* EDM field is actually the object the manifest is created for. Therefore, it is important to first verify that this object is retrievable using the user-specified URL of the IIIF base service. If it is not, an error occurs and the manifest is not created.
- Descriptive metadata e.g. title, description, metadata, rights etc.
- Additional images (if available i.e. *edm:hasView* fields)

A **valid EDM metadata record** **with** ***edm:isShownBy*** **field** **is required** to create the manifest with the EDM2IIIF Manifest Creation tool. However, the object is better represented if its manifest contains more information about it - the richer the EDM record the better.

The following IIIF manifest fields are created with the EDM2IIIF Manifest Creation tool:

|                         |                                                                                                                |
|:------------------------|:---------------------------------------------------------------------------------------------------------------|
| **IIIF Manifest field** | **EDM field**                                                                                                  |
| @context                | [ <br/> "<http://www.w3.org/ns/anno.jsonld>", <br/> "<http://iiif.io/api/presentation/3/context.json>" <br/> ] |
| id                      | Manifest path for image                                                                                        |
| type                    | „Manifest“                                                                                                     |
| label                   | dc:title or dc:description if dc:title not present                                                             |
| summary                 | dc:description, but only if dc:title exists                                                                    |
| metadata                | all descriptive elements from edm:ProvidedCHO class like dc:identifier, dc:relation, dc:type etc.              |
| thumbnail               | edm:objects from ore:Aggregation                                                                               |
| homepage                | edm:isShownAt from ore:Aggregation                                                                             |
| requiredStatement       | dc:rights from edm:WebResource of corresponding edm:isShownBy                                                  |
| rights                  | edm:rights from ore:Aggregation                                                                                |
| provider                | edm:dataProvider from ore:Aggregation                                                                          |
| seeAlso                 | dc:source from edm:ProvidedCHO                                                                                 |
| service                 | svcs:has\_service from edm:WebResource                                                                         |
| start                   | edm:isShownBy if at least one edm:hasView exists                                                               |
| items                   | edm:isShownBy and all corresponding edm:hasView                                                                |

# 10 EDM enrichment

EDM enrichment in our case is the process of updating the EDM metadata records by providing appropriate descriptions of IIIF resources. Such updating involves the following steps:

1. Set IIIF resource in EDM’s *isShownBy field* and corresponding *WebResource* class. Do the same with appropriate IIIF resources (if existing) for every *hasView*  that is present.
2. Create a *Service* class whose identifier should be the base URL of the IIIF resource. Then flag all corresponding *WebResources* as IIIF-compliant by adding a has\_service field that holds Service’s identifier value.
3. Indicate the level of IIIF protocol in an *implements* field of the *Service* class.
4. Provide access to a IIIF manifest in an *isReferencedBy* field of *WebResource*

**Goal**: You can use the delivered IIIF-enriched EDM metadata records for your further processing as required. In particular, they also serve as templates for describing IIIF resources in exactly your EDM metadata records.

# 11 Troubleshooting

“*name* does not exist”:

After a week the EDM Manifest Creation tool deletes a submitted dataset. It is highly possible that the dataset has been removed because of this. Or it is possible that a dataset with this name does not exist at all.

How error is produced: Writing project name in *Name* input field -> Choosing *Track/download harvested dataset*  as Harvest Protocol -> *Submit* button

![](https://europeana.atlassian.net/wiki/download/attachments/2517368849/AD_4nXcq2p33A7dP-ESmF2XdkrrC-BLHn6XAVIhBVXVqgP-JWLip-bK_NIE34W-q1X8BzPdDtqdFuN4WGmA7s7gyxo45aI6uw48COtLWoz-bOHNaKRvdOstAPlbu-SBuI7D3V0canOStWddtaaOTyg85o8ogZjBJ%3Fkey=yDJ2wl4wJcrsr0iw5AUDmg?version=1&modificationDate=1718708924197&cacheVersion=1&api=v2)

*“OAI-PMH upload failed”:*

This window shows if the OAI-PMH link was not correct or one of the two URL input fields could not be processed correctly.

![](https://europeana.atlassian.net/wiki/download/attachments/2517368849/AD_4nXfu3rXytZtZkA6Wytd6xw3UThsuDou4iGumBG_0tYjPTSBQnqujA9iAMUfrKeJtchRUA-DUiZKr8R7jw_8C6hxHfs2JPqcajYjUnjuzFPXlRloiptnAjVwJyt0gobYfyq0xF6GVp7pJFwN7ssLfiGRLtl3S%3Fkey=yDJ2wl4wJcrsr0iw5AUDmg?version=1&modificationDate=1718708924205&cacheVersion=1&api=v2)

# Samples

## **Original EDM (from OAI provider)**

<rdf:RDF xmlns:rdf="<http://www.w3.org/1999/02/22-rdf-syntax-ns#>" xmlns:edm="<http://www.europeana.eu/schemas/edm/>" xmlns:dc="<http://purl.org/dc/elements/1.1/> " xmlns:dcterms="<http://purl.org/dc/terms/> " xmlns:wgs84\_pos="<http://www.w3.org/2003/01/geo/wgs84_pos#>" xmlns:skos="<http://www.w3.org/2004/02/skos/core#>" xmlns:ore="<http://www.openarchives.org/ore/terms/>">

  <edm:ProvidedCHO xmlns:dwc="<http://rs.tdwg.org/dwc/terms/> " xmlns:meta="<http://rs.tdwg.org/dwc/text/>" xmlns:gbif="<http://rs.gbif.org/terms/1.0/> " rdf:about="ZOBODATXLANDOOEXAUSTRIAX6894095">

      <dc:identifier>BIOZOOELM - ZOBODAT - 6894095</dc:identifier>

      <dc:title>Colletes maroccanus Warncke, 1978</dc:title>

      <dc:relation><http://www.biodiversitylibrary.org/name/Colletes_maroccanus_Warncke%2C_1978> </dc:relation>

      <dc:type>Specimen</dc:type>

      <dcterms:spatial rdf:resource="geo:30.75,-6.8"/>

      <edm:hasMet rdf:resource="geo:30.75,-6.8"/>

      <edm:hasType rdf:resource="<http://rs.tdwg.org/dwc/terms/Specimen>"/>

      <edm:type>IMAGE</edm:type>

    </edm:ProvidedCHO>

          <edm:WebResource xmlns:dwc="<http://rs.tdwg.org/dwc/terms/> " xmlns:meta="<http://rs.tdwg.org/dwc/text/>" xmlns:gbif="<http://rs.gbif.org/terms/1.0/> " rdf:about="<http://www.zobodat.at/bilder/belege/00100544.jpg>">

      <dc:format>jpg</dc:format>

      <dc:rights>CC BY-SA</dc:rights>

      <edm:rights rdf:resource="<http://creativecommons.org/licenses/by-sa/3.0/> "/>

    </edm:WebResource>

          <edm:WebResource xmlns:dwc="<http://rs.tdwg.org/dwc/terms/> " xmlns:meta="<http://rs.tdwg.org/dwc/text/>" xmlns:gbif="<http://rs.gbif.org/terms/1.0/> " rdf:about="<http://www.zobodat.at/bilder/belege/00100545.jpg>">

      <dc:format>jpg</dc:format>

      <dc:rights>CC BY-SA</dc:rights>

      <edm:rights rdf:resource="<http://creativecommons.org/licenses/by-sa/3.0/> "/>

    </edm:WebResource>

          <edm:WebResource xmlns:dwc="<http://rs.tdwg.org/dwc/terms/> " xmlns:meta="<http://rs.tdwg.org/dwc/text/>" xmlns:gbif="<http://rs.gbif.org/terms/1.0/> " rdf:about="<http://www.zobodat.at/bilder/belege/00100546.jpg>">

      <dc:format>jpg</dc:format>

      <dc:rights>CC BY-SA</dc:rights>

      <edm:rights rdf:resource="<http://creativecommons.org/licenses/by-sa/3.0/> "/>

    </edm:WebResource>

          <edm:WebResource xmlns:dwc="<http://rs.tdwg.org/dwc/terms/> " xmlns:meta="<http://rs.tdwg.org/dwc/text/>" xmlns:gbif="<http://rs.gbif.org/terms/1.0/> " rdf:about="<http://www.zobodat.at/bilder/belege/00100547.jpg>">

      <dc:format>jpg</dc:format>

      <dc:rights>CC BY-SA</dc:rights>

      <edm:rights rdf:resource="<http://creativecommons.org/licenses/by-sa/3.0/> "/>

    </edm:WebResource>

          <edm:WebResource xmlns:dwc="<http://rs.tdwg.org/dwc/terms/> " xmlns:meta="<http://rs.tdwg.org/dwc/text/>" xmlns:gbif="<http://rs.gbif.org/terms/1.0/> " rdf:about="<http://www.zobodat.at/bilder/belege/00100548.jpg>">

      <dc:format>jpg</dc:format>

      <dc:rights>CC BY-SA</dc:rights>

      <edm:rights rdf:resource="<http://creativecommons.org/licenses/by-sa/3.0/> "/>

    </edm:WebResource>

          <edm:WebResource xmlns:dwc="<http://rs.tdwg.org/dwc/terms/> " xmlns:meta="<http://rs.tdwg.org/dwc/text/>" xmlns:gbif="<http://rs.gbif.org/terms/1.0/> " rdf:about="<http://www.zobodat.at/bilder/belege/00100549.jpg>">

      <dc:format>jpg</dc:format>

      <dc:rights>CC BY-SA</dc:rights>

      <edm:rights rdf:resource="<http://creativecommons.org/licenses/by-sa/3.0/> "/>

    </edm:WebResource>

          <edm:WebResource xmlns:dwc="<http://rs.tdwg.org/dwc/terms/> " xmlns:meta="<http://rs.tdwg.org/dwc/text/>" xmlns:gbif="<http://rs.gbif.org/terms/1.0/> " rdf:about="<http://www.zobodat.at/bilder/belege/00100550.jpg>">

      <dc:format>jpg</dc:format>

      <dc:rights>CC BY-SA</dc:rights>

      <edm:rights rdf:resource="<http://creativecommons.org/licenses/by-sa/3.0/> "/>

    </edm:WebResource>

          <edm:WebResource xmlns:dwc="<http://rs.tdwg.org/dwc/terms/> " xmlns:meta="<http://rs.tdwg.org/dwc/text/>" xmlns:gbif="<http://rs.gbif.org/terms/1.0/> " rdf:about="<http://www.zobodat.at/bilder/belege/00100551.jpg>">

      <dc:format>jpg</dc:format>

      <dc:rights>CC BY-SA</dc:rights>

      <edm:rights rdf:resource="<http://creativecommons.org/licenses/by-sa/3.0/> "/>

    </edm:WebResource>

          <edm:WebResource xmlns:dwc="<http://rs.tdwg.org/dwc/terms/> " xmlns:meta="<http://rs.tdwg.org/dwc/text/>" xmlns:gbif="<http://rs.gbif.org/terms/1.0/> " rdf:about="<http://www.zobodat.at/belege_detail.php?id=6894095> ">

      <dc:format>text/html</dc:format>

      <dc:rights>CC BY-SA</dc:rights>

      <edm:rights rdf:resource="<http://creativecommons.org/licenses/by-sa/3.0/> "/>

    </edm:WebResource>

          <edm:Place xmlns:dwc="<http://rs.tdwg.org/dwc/terms/> " xmlns:meta="<http://rs.tdwg.org/dwc/text/>" xmlns:gbif="<http://rs.gbif.org/terms/1.0/> " rdf:about="geo:30.75,-6.8">

      <wgs84\_pos:lat>30.75</wgs84\_pos:lat>

      <wgs84\_pos:long>-6.8</wgs84\_pos:long>

      <skos:prefLabel>Djebel Tifernine</skos:prefLabel>

      <skos:note/>

    </edm:Place>

          <ore:Aggregation xmlns:dwc="<http://rs.tdwg.org/dwc/terms/> " xmlns:meta="<http://rs.tdwg.org/dwc/text/>" xmlns:gbif="<http://rs.gbif.org/terms/1.0/> " rdf:about="<http://web-openup.nhm.ac.uk/oai-provider/index.php?form=display&amp;oaiid=ZOBODAT%3ALANDOOE%3AAUSTRIA%2F6894095&amp;db=0>">

      <edm:aggregatedCHO rdf:resource="ZOBODATXLANDOOEXAUSTRIAX6894095"/>

      <edm:dataProvider>Biologiezentrum der Oberoesterreichischen Landesmuseen</edm:dataProvider>

      <edm:hasView rdf:resource="<http://www.zobodat.at/bilder/belege/00100545.jpg>"/>

      <edm:hasView rdf:resource="<http://www.zobodat.at/bilder/belege/00100546.jpg>"/>

      <edm:hasView rdf:resource="<http://www.zobodat.at/bilder/belege/00100547.jpg>"/>

      <edm:hasView rdf:resource="<http://www.zobodat.at/bilder/belege/00100548.jpg>"/>

      <edm:hasView rdf:resource="<http://www.zobodat.at/bilder/belege/00100549.jpg>"/>

      <edm:hasView rdf:resource="<http://www.zobodat.at/bilder/belege/00100550.jpg>"/>

      <edm:hasView rdf:resource="<http://www.zobodat.at/bilder/belege/00100551.jpg>"/>

      <edm:isShownAt rdf:resource="<http://www.zobodat.at/belege_detail.php?id=6894095> "/>

      <edm:isShownBy rdf:resource="<http://www.zobodat.at/bilder/belege/00100544.jpg>"/>

      <edm:object rdf:resource="<http://www.zobodat.at/bilder/belege/00100544.jpg>"/>

      <edm:provider>OpenUp!</edm:provider>

      <edm:rights rdf:resource="<http://creativecommons.org/licenses/by-sa/3.0/> "/>

    </ore:Aggregation>

</rdf:RDF>

## **.json Manifest**

{

  "@context": [

    "<http://www.w3.org/ns/anno.jsonld>",

    "<http://iiif.io/api/presentation/3/context.json>"

  ],

  "id": "<http://dev.ait.co.at/manifests/manifest_00100544.json>",

  "type": "Manifest",

  "label": {

    "@none": [

      "Colletes maroccanus Warncke, 1978"

    ]

  },

  "metadata": [

    {

      "label": {

        "en": [

          "identifier"

        ]

      },

      "value": {

        "@none": [

          "BIOZOOELM - ZOBODAT - 6894095"

        ]

      }

    },

    {

      "label": {

        "en": [

          "relation"

        ]

      },

      "value": {

        "@none": [

          "<http://www.biodiversitylibrary.org/name/Colletes_maroccanus_Warncke%2C_1978> "

        ]

      }

    },

    {

      "label": {

        "en": [

          "type"

        ]

      },

      "value": {

        "@none": [

          "Specimen"

        ]

      }

    },

    {

      "label": {

        "en": [

          "spatial"

        ]

      },

      "value": {

        "@none": [

          "Djebel Tifernine"

        ]

      }

    },

    {

      "label": {

        "en": [

          "hasMet"

        ]

      },

      "value": {

        "@none": [

          "Djebel Tifernine"

        ]

      }

    },

    {

      "label": {

        "en": [

          "type"

        ]

      },

      "value": {

        "@none": [

          "IMAGE"

        ]

      }

    }

  ],

  "thumbnail": [

    {

      "id": "<http://dev.ait.co.at/iiif/00100544.tif/full/max/0/default>",

      "type": "Image",

      "format": "jpg"

    }

  ],

  "homepage": [

    {

      "id": "<http://www.zobodat.at/belege_detail.php?id=6894095> ",

      "type": "Text",

      "format": "text/html"

    }

  ],

  "requiredStatement": {

    "label": {

      "en": [

        "Attribution"

      ]

    },

    "value": {

      "@none": [

        "CC BY-SA"

      ]

    }

  },

  "rights": "<http://creativecommons.org/licenses/by-sa/3.0/> ",

  "provider": [

    {

      "id": "Biologiezentrum der Oberoesterreichischen Landesmuseen",

      "type": "Agent",

      "homepage": [

        {

          "id": "<http://www.zobodat.at/belege_detail.php?id=6894095> ",

          "type": "Text",

          "format": "text/html"

        }

      ]

    }

  ],

  "service": [

    {

      "id": "<http://dev.ait.co.at/iiif/00100544.tif>",

      "type": "ImageService3",

      "profile": "<http://iiif.io/api/image/3/level2.json>"

    },

    {

      "id": "<http://dev.ait.co.at/iiif/00100544.tif>",

      "type": "ImageService3",

      "profile": "<http://iiif.io/api/image/3/level2.json>"

    },

    {

      "id": "<http://dev.ait.co.at/iiif/00100544.tif>",

      "type": "ImageService3",

      "profile": "<http://iiif.io/api/image/3/level2.json>"

    },

    {

      "id": "<http://dev.ait.co.at/iiif/00100544.tif>",

      "type": "ImageService3",

      "profile": "<http://iiif.io/api/image/3/level2.json>"

    },

    {

      "id": "<http://dev.ait.co.at/iiif/00100544.tif>",

      "type": "ImageService3",

      "profile": "<http://iiif.io/api/image/3/level2.json>"

    },

    {

      "id": "<http://dev.ait.co.at/iiif/00100544.tif>",

      "type": "ImageService3",

      "profile": "<http://iiif.io/api/image/3/level2.json>"

    },

    {

      "id": "<http://dev.ait.co.at/iiif/00100544.tif>",

      "type": "ImageService3",

      "profile": "<http://iiif.io/api/image/3/level2.json>"

    },

    {

      "id": "<http://dev.ait.co.at/iiif/00100544.tif>",

      "type": "ImageService3",

      "profile": "<http://iiif.io/api/image/3/level2.json>"

    }

  ],

  "start": {

    "id": "<http://dev.ait.co.at/iiif/00100544.tif/full/max/0/default>",

    "type": "Canvas",

    "format": "image/jpg",

    "height": 1920,

    "width": 2560,

    "requiredStatement": {

      "label": {

        "en": [

          "Attribution"

        ]

      },

      "value": {

        "@none": [

          "CC BY-SA"

        ]

      }

    },

    "rights": "<http://creativecommons.org/licenses/by-sa/3.0/> "

  },

  "items": [

    {

      "id": "<http://dev.ait.co.at/iiif/00100544.tif/full/max/0/default>",

      "type": "Canvas",

      "height": 1920,

      "width": 2560,

      "requiredStatement": {

        "label": {

          "en": [

            "Attribution"

          ]

        },

        "value": {

          "@none": [

            "CC BY-SA"

          ]

        }

      },

      "rights": "<http://creativecommons.org/licenses/by-sa/3.0/> ",

      "items": [

        {

          "id": "<http://dev.ait.co.at/iiif/00100544.tif>",

          "type": "AnnotationPage",

          "items": [

            {

              "id": "<http://dev.ait.co.at/iiif/00100544.tif>",

              "type": "Annotation",

              "motivation": "painting",

              "body": {

                "id": "<http://dev.ait.co.at/iiif/00100544.tif/full/max/0/default>",

                "type": "Image",

                "format": "image/jpg",

                "height": 1920,

                "width": 2560

              },

              "target": "<http://dev.ait.co.at/iiif/00100544.tif>"

            }

          ]

        }

      ]

    },

    {

      "id": "<http://dev.ait.co.at/iiif/00100545.tif>",

      "type": "Canvas",

      "width": 2560,

      "height": 1920,

      "rights": "<http://creativecommons.org/licenses/by-sa/3.0/> ",

      "items": [

        {

          "id": "<http://dev.ait.co.at/iiif/00100545.tif>",

          "type": "AnnotationPage",

          "items": [

            {

              "id": "<http://dev.ait.co.at/iiif/00100545.tif>",

              "type": "Annotation",

              "motivation": "painting",

              "body": {

                "id": "<http://dev.ait.co.at/iiif/00100545.tif/full/max/0/default>",

                "type": "Image",

                "format": "image/jpg",

                "height": 1920,

                "width": 2560

              },

              "target": "<http://dev.ait.co.at/iiif/00100545.tif>"

            }

          ]

        }

      ]

    },

    {

      "id": "<http://dev.ait.co.at/iiif/00100546.tif>",

      "type": "Canvas",

      "width": 2560,

      "height": 1920,

      "rights": "<http://creativecommons.org/licenses/by-sa/3.0/> ",

      "items": [

        {

          "id": "<http://dev.ait.co.at/iiif/00100546.tif>",

          "type": "AnnotationPage",

          "items": [

            {

              "id": "<http://dev.ait.co.at/iiif/00100546.tif>",

              "type": "Annotation",

              "motivation": "painting",

              "body": {

                "id": "<http://dev.ait.co.at/iiif/00100546.tif/full/max/0/default>",

                "type": "Image",

                "format": "image/jpg",

                "height": 1920,

                "width": 2560

              },

              "target": "<http://dev.ait.co.at/iiif/00100546.tif>"

            }

          ]

        }

      ]

    },

    {

      "id": "<http://dev.ait.co.at/iiif/00100547.tif>",

      "type": "Canvas",

      "width": 2560,

      "height": 1920,

      "rights": "<http://creativecommons.org/licenses/by-sa/3.0/> ",

      "items": [

        {

          "id": "<http://dev.ait.co.at/iiif/00100547.tif>",

          "type": "AnnotationPage",

          "items": [

            {

              "id": "<http://dev.ait.co.at/iiif/00100547.tif>",

              "type": "Annotation",

              "motivation": "painting",

              "body": {

                "id": "<http://dev.ait.co.at/iiif/00100547.tif/full/max/0/default>",

                "type": "Image",

                "format": "image/jpg",

                "height": 1920,

                "width": 2560

              },

              "target": "<http://dev.ait.co.at/iiif/00100547.tif>"

            }

          ]

        }

      ]

    },

    {

      "id": "<http://dev.ait.co.at/iiif/00100548.tif>",

      "type": "Canvas",

      "width": 2560,

      "height": 1920,

      "rights": "<http://creativecommons.org/licenses/by-sa/3.0/> ",

      "items": [

        {

          "id": "<http://dev.ait.co.at/iiif/00100548.tif>",

          "type": "AnnotationPage",

          "items": [

            {

              "id": "<http://dev.ait.co.at/iiif/00100548.tif>",

              "type": "Annotation",

              "motivation": "painting",

              "body": {

                "id": "<http://dev.ait.co.at/iiif/00100548.tif/full/max/0/default>",

                "type": "Image",

                "format": "image/jpg",

                "height": 1920,

                "width": 2560

              },

              "target": "<http://dev.ait.co.at/iiif/00100548.tif>"

            }

          ]

        }

      ]

    },

    {

      "id": "<http://dev.ait.co.at/iiif/00100549.tif>",

      "type": "Canvas",

      "width": 2560,

      "height": 1920,

      "rights": "<http://creativecommons.org/licenses/by-sa/3.0/> ",

      "items": [

        {

          "id": "<http://dev.ait.co.at/iiif/00100549.tif>",

          "type": "AnnotationPage",

          "items": [

            {

              "id": "<http://dev.ait.co.at/iiif/00100549.tif>",

              "type": "Annotation",

              "motivation": "painting",

              "body": {

                "id": "<http://dev.ait.co.at/iiif/00100549.tif/full/max/0/default>",

                "type": "Image",

                "format": "image/jpg",

                "height": 1920,

                "width": 2560

              },

              "target": "<http://dev.ait.co.at/iiif/00100549.tif>"

            }

          ]

        }

      ]

    },

    {

      "id": "<http://dev.ait.co.at/iiif/00100550.tif>",

      "type": "Canvas",

      "width": 2560,

      "height": 1920,

      "rights": "<http://creativecommons.org/licenses/by-sa/3.0/> ",

      "items": [

        {

          "id": "<http://dev.ait.co.at/iiif/00100550.tif>",

          "type": "AnnotationPage",

          "items": [

            {

              "id": "<http://dev.ait.co.at/iiif/00100550.tif>",

              "type": "Annotation",

              "motivation": "painting",

              "body": {

                "id": "<http://dev.ait.co.at/iiif/00100550.tif/full/max/0/default>",

                "type": "Image",

                "format": "image/jpg",

                "height": 1920,

                "width": 2560

              },

              "target": "<http://dev.ait.co.at/iiif/00100550.tif>"

            }

          ]

        }

      ]

    },

    {

      "id": "<http://dev.ait.co.at/iiif/00100551.tif>",

      "type": "Canvas",

      "width": 3264,

      "height": 2448,

      "rights": "<http://creativecommons.org/licenses/by-sa/3.0/> ",

      "items": [

        {

          "id": "<http://dev.ait.co.at/iiif/00100551.tif>",

          "type": "AnnotationPage",

          "items": [

            {

              "id": "<http://dev.ait.co.at/iiif/00100551.tif>",

              "type": "Annotation",

              "motivation": "painting",

              "body": {

                "id": "<http://dev.ait.co.at/iiif/00100551.tif/full/max/0/default>",

                "type": "Image",

                "format": "image/jpg",

                "height": 2448,

                "width": 3264

              },

              "target": "<http://dev.ait.co.at/iiif/00100551.tif>"

            }

          ]

        }

      ]

    }

  ]

}

## **Enriched EDM**

Please see [IIIF to EDM profile (definitions)](../../Europeana%20Data%20Model/EDM%20profiles/IIIF%20to%20EDM%20profile%20(definitions).md) for detailed information on how to express IIIF in EDM classes and properties.

<rdf:RDF xmlns:dc="<http://purl.org/dc/elements/1.1/> " xmlns:dcterms="<http://purl.org/dc/terms/> " xmlns:doap="<http://usefulinc.com/ns/doap#>" xmlns:edm="<http://www.europeana.eu/schemas/edm/>" xmlns:ore="<http://www.openarchives.org/ore/terms/>" xmlns:rdf="<http://www.w3.org/1999/02/22-rdf-syntax-ns#>" xmlns:skos="<http://www.w3.org/2004/02/skos/core#>" xmlns:svcs="<http://rdfs.org/sioc/services#>" xmlns:wgs84\_pos="<http://www.w3.org/2003/01/geo/wgs84_pos#>">

 <edm:ProvidedCHO rdf:about="ZOBODATXLANDOOEXAUSTRIAX6894095">

  <dc:identifier>BIOZOOELM - ZOBODAT - 6894095</dc:identifier>

  <dc:title>Colletes maroccanus Warncke, 1978</dc:title>

  <dc:relation><http://www.biodiversitylibrary.org/name/Colletes_maroccanus_Warncke%2C_1978> </dc:relation>

  <dc:type>Specimen</dc:type>

  <dcterms:spatial rdf:resource="geo:30.75,-6.8"/>

  <edm:hasMet rdf:resource="geo:30.75,-6.8"/>

  <edm:hasType rdf:resource="<http://rs.tdwg.org/dwc/terms/Specimen>"/>

  <edm:type>IMAGE</edm:type>

 </edm:ProvidedCHO>

 <edm:WebResource rdf:about="<http://dev.ait.co.at/iiif/00100544.tif/full/max/0/default>">

  <dc:format>jpg</dc:format>

  <dc:rights>CC BY-SA</dc:rights>

  <edm:rights rdf:resource="<http://creativecommons.org/licenses/by-sa/3.0/> "/>

  <dcterms:isReferencedBy rdf:resource="<http://dev.ait.co.at/manifests/manifest_00100544.json>"/>

  <svcs:has\_service rdf:resource="<http://dev.ait.co.at/iiif/00100544.tif>"/>

 </edm:WebResource>

 <edm:WebResource rdf:about="<http://dev.ait.co.at/iiif/00100545.tif/full/max/0/default>">

  <dc:format>jpg</dc:format>

  <dc:rights>CC BY-SA</dc:rights>

  <edm:rights rdf:resource="<http://creativecommons.org/licenses/by-sa/3.0/> "/>

  <dcterms:isReferencedBy rdf:resource="<http://dev.ait.co.at/manifests/manifest_00100544.json>"/>

  <svcs:has\_service rdf:resource="<http://dev.ait.co.at/iiif/00100544.tif>"/>

 </edm:WebResource>

 <edm:WebResource rdf:about="<http://dev.ait.co.at/iiif/00100546.tif/full/max/0/default>">

  <dc:format>jpg</dc:format>

  <dc:rights>CC BY-SA</dc:rights>

  <edm:rights rdf:resource="<http://creativecommons.org/licenses/by-sa/3.0/> "/>

  <dcterms:isReferencedBy rdf:resource="<http://dev.ait.co.at/manifests/manifest_00100544.json>"/>

  <svcs:has\_service rdf:resource="<http://dev.ait.co.at/iiif/00100544.tif>"/>

 </edm:WebResource>

 <edm:WebResource rdf:about="<http://dev.ait.co.at/iiif/00100547.tif/full/max/0/default>">

  <dc:format>jpg</dc:format>

  <dc:rights>CC BY-SA</dc:rights>

  <edm:rights rdf:resource="<http://creativecommons.org/licenses/by-sa/3.0/> "/>

  <dcterms:isReferencedBy rdf:resource="<http://dev.ait.co.at/manifests/manifest_00100544.json>"/>

  <svcs:has\_service rdf:resource="<http://dev.ait.co.at/iiif/00100544.tif>"/>

 </edm:WebResource>

 <edm:WebResource rdf:about="<http://dev.ait.co.at/iiif/00100548.tif/full/max/0/default>">

  <dc:format>jpg</dc:format>

  <dc:rights>CC BY-SA</dc:rights>

  <edm:rights rdf:resource="<http://creativecommons.org/licenses/by-sa/3.0/> "/>

  <dcterms:isReferencedBy rdf:resource="<http://dev.ait.co.at/manifests/manifest_00100544.json>"/>

  <svcs:has\_service rdf:resource="<http://dev.ait.co.at/iiif/00100544.tif>"/>

 </edm:WebResource>

 <edm:WebResource rdf:about="<http://dev.ait.co.at/iiif/00100549.tif/full/max/0/default>">

  <dc:format>jpg</dc:format>

  <dc:rights>CC BY-SA</dc:rights>

  <edm:rights rdf:resource="<http://creativecommons.org/licenses/by-sa/3.0/> "/>

  <dcterms:isReferencedBy rdf:resource="<http://dev.ait.co.at/manifests/manifest_00100544.json>"/>

  <svcs:has\_service rdf:resource="<http://dev.ait.co.at/iiif/00100544.tif>"/>

 </edm:WebResource>

 <edm:WebResource rdf:about="<http://dev.ait.co.at/iiif/00100550.tif/full/max/0/default>">

  <dc:format>jpg</dc:format>

  <dc:rights>CC BY-SA</dc:rights>

  <edm:rights rdf:resource="<http://creativecommons.org/licenses/by-sa/3.0/> "/>

  <dcterms:isReferencedBy rdf:resource="<http://dev.ait.co.at/manifests/manifest_00100544.json>"/>

  <svcs:has\_service rdf:resource="<http://dev.ait.co.at/iiif/00100544.tif>"/>

 </edm:WebResource>

 <edm:WebResource rdf:about="<http://dev.ait.co.at/iiif/00100551.tif/full/max/0/default>">

  <dc:format>jpg</dc:format>

  <dc:rights>CC BY-SA</dc:rights>

  <edm:rights rdf:resource="<http://creativecommons.org/licenses/by-sa/3.0/> "/>

  <dcterms:isReferencedBy rdf:resource="<http://dev.ait.co.at/manifests/manifest_00100544.json>"/>

  <svcs:has\_service rdf:resource="<http://dev.ait.co.at/iiif/00100544.tif>"/>

 </edm:WebResource>

 <edm:WebResource rdf:about="<http://www.zobodat.at/belege_detail.php?id=6894095> ">

  <dc:format>text/html</dc:format>

  <dc:rights>CC BY-SA</dc:rights>

  <edm:rights rdf:resource="<http://creativecommons.org/licenses/by-sa/3.0/> "/>

 </edm:WebResource>

 <edm:Place rdf:about="geo:30.75,-6.8">

  <wgs84\_pos:lat>30.75</wgs84\_pos:lat>

  <wgs84\_pos:long>-6.8</wgs84\_pos:long>

  <skos:prefLabel>Djebel Tifernine</skos:prefLabel>

  <skos:note/>

 </edm:Place>

 <ore:Aggregation rdf:about="<http://web-openup.nhm.ac.uk/oai-provider/index.php?form=display&amp;oaiid=ZOBODAT%3ALANDOOE%3AAUSTRIA%2F6894095&amp;db=0>">

  <edm:aggregatedCHO rdf:resource="ZOBODATXLANDOOEXAUSTRIAX6894095"/>

  <edm:dataProvider>Biologiezentrum der Oberoesterreichischen Landesmuseen</edm:dataProvider>

  <edm:hasView rdf:resource="<http://dev.ait.co.at/iiif/00100545.tif/full/max/0/default>"/>

  <edm:hasView rdf:resource="<http://dev.ait.co.at/iiif/00100546.tif/full/max/0/default>"/>

  <edm:hasView rdf:resource="<http://dev.ait.co.at/iiif/00100547.tif/full/max/0/default>"/>

  <edm:hasView rdf:resource="<http://dev.ait.co.at/iiif/00100548.tif/full/max/0/default>"/>

  <edm:hasView rdf:resource="<http://dev.ait.co.at/iiif/00100549.tif/full/max/0/default>"/>

  <edm:hasView rdf:resource="<http://dev.ait.co.at/iiif/00100550.tif/full/max/0/default>"/>

  <edm:hasView rdf:resource="<http://dev.ait.co.at/iiif/00100551.tif/full/max/0/default>"/>

  <edm:isShownAt rdf:resource="<http://www.zobodat.at/belege_detail.php?id=6894095> "/>

  <edm:isShownBy rdf:resource="<http://dev.ait.co.at/iiif/00100544.tif/full/max/0/default>"/>

  <edm:object rdf:resource="<http://dev.ait.co.at/iiif/00100544.tif/full/max/0/default>"/>

  <edm:provider>OpenUp!</edm:provider>

  <edm:rights rdf:resource="<http://creativecommons.org/licenses/by-sa/3.0/> "/>

 </ore:Aggregation>

 <svcs:Service rdf:about="<http://dev.ait.co.at/iiif/00100544.tif>">

  <dcterms:conformsTo rdf:resource="<https://iiif.io/api/image/3.0/> "/>

  <doap:implements rdf:resource="<http://iiif.io/api/image/3/level2.json>"/>

 </svcs:Service>

</rdf:RDF>
