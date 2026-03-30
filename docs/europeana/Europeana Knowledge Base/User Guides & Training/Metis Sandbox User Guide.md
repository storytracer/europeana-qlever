---
tags:
  - '#user-guide'
  - '#metis-sandbox'
---

[User Guides & Training](../User%20Guides%20&%20Training.md)

# Metis Sandbox User Guide

*Metis Sandbox Version 11 - February 2026*

- [1 Purpose of the Metis Sandbox](#key-1-purpose-of-the-metis-sandbox)
- [2 Where to find the sandbox](#key-2-where-to-find-the-sandbox)
- [3 How to prepare your dataset](#key-3-how-to-prepare-your-dataset)
- [4 General interface elements](#key-4-general-interface-elements)
  - [4.1 Page header elements](#key-4-1-page-header-elements)
  - [4.2 Buttons](#key-4-2-buttons)
  - [4.3 Input fields](#key-4-3-input-fields)
  - [4.4 Page Indicators](#key-4-4-page-indicators)
  - [4.5 Links](#key-4-5-links)
  - [4.6 Drop-down menus](#key-4-6-drop-down-menus)
- [5 The Basics: arriving at the Metis Sandbox](#key-5-the-basics-arriving-at-the-metis-sandbox)
  - [5.1 The Welcome screen](#key-5-1-the-welcome-screen)
  - [5.2 The page header and side panel](#key-5-2-the-page-header-and-side-panel)
  - [5.3 Creating a user account and logging in](#key-5-3-creating-a-user-account-and-logging-in)
  - [5.4 The Home screen](#key-5-4-the-home-screen)
- [6 Upload a new dataset](#key-6-upload-a-new-dataset)
  - [6.1 The Upload Form](#key-6-1-the-upload-form)
  - [6.2 The Harvest Protocol](#key-6-2-the-harvest-protocol)
    - [6.2.1 Zip File](#key-6-2-1-zip-file)
    - [6.2.2 OAI-PMH](#key-6-2-2-oai-pmh)
    - [6.2.3 HTTP(S) upload](#key-6-2-3-http-s-upload)
  - [6.3 XSL Transformation to EDM (Optional)](#key-6-3-xsl-transformation-to-edm-optional)
  - [6.4 The step size](#key-6-4-the-step-size)
  - [6.5 The Generated Dataset ID](#key-6-5-the-generated-dataset-id)
- [7 Dataset processing](#key-7-dataset-processing)
  - [7.1 The Data Processing View](#key-7-1-the-data-processing-view)
  - [7.2 Dataset details and rerunning a dataset](#key-7-2-dataset-details-and-rerunning-a-dataset)
  - [7.3 The Metis workflow](#key-7-3-the-metis-workflow)
  - [7.4 The Data Processing Errors Window](#key-7-4-the-data-processing-errors-window)
  - [7.5 View the published records](#key-7-5-view-the-published-records)
  - [7.6 Tier Statistics](#key-7-6-tier-statistics)
  - [7.7 Filtering Tier Statistics](#key-7-7-filtering-tier-statistics)
  - [7.8 Sorting Filtered Tier Statistics](#key-7-8-sorting-filtered-tier-statistics)
- [8 The tier calculation report](#key-8-the-tier-calculation-report)
  - [8.1 Record Provider Ids and Europeana Ids](#key-8-1-record-provider-ids-and-europeana-ids)
  - [8.2 The Record Report](#key-8-2-the-record-report)
  - [8.3 Content Tier Media Information](#key-8-3-content-tier-media-information)
  - [8.4 Metadata Tier Information](#key-8-4-metadata-tier-information)
- [9 Problem patterns](#key-9-problem-patterns)
  - [9.1 Dataset / Overview](#key-9-1-dataset-overview)
  - [9.2 Record](#key-9-2-record)
- [10 Tier Zero Records](#key-10-tier-zero-records)
- [11 Detecting contentious terms - the DE-BIAS project](#key-11-detecting-contentious-terms-the-de-bias-project)
  - [11.1 Running the DE-BIAS analysis](#key-11-1-running-the-de-bias-analysis)
  - [11.2 The DE-BIAS report](#key-11-2-the-de-bias-report)
- [12 Troubleshooting](#key-12-troubleshooting)

---

# 1 Purpose of the Metis Sandbox

The Metis Sandbox is a test environment for your data. It consists of a set of integrated tools with which you can:

1. simulate ingesting and running the Metis workflow on your data,
2. see what your records would look like on the actual [Europeana.eu](http://Europeana.eu) portal,
3. get insight into the quality of your records.

> [!WARNING]
> **Scheduled and unscheduled clean up**  
> The Metis Sandbox is a testing environment for data, it does not aim to retain data indefinitely. This means that the Metis Sandbox **gets cleaned up** regularly. All data uploaded more than **one month** ago may be removed.
>
> Additionally, during system maintenance or the release of a new Metis Sandbox version data may be removed at any time. Where possible, these events will be announced beforehand.
>
> Datasets that are deleted from the Metis Sandbox will need to be uploaded again if you wish to access the tests and reports.

---

# 2 Where to find the sandbox

The Sandbox can be accessed through <https://metis-sandbox.europeana.eu/> .

---

# 3 How to prepare your dataset

It is advised to make sure that your dataset can be used with the Metis Sandbox. The criteria are overall the same as for Metis processing:

- The records in your dataset needs to meet the requirements of the Europeana Data Model (EDM) external. More information on the EDM can be found on <https://pro.europeana.eu/page/edm-documentation> . If records are found that do not conform to this schema, you will see error messages.

> [!NOTE]
> You may choose to provide an XSLT file with the dataset, which the Metis Sandbox will use to try to transform your records into the correct format before validating them against the EDM external specifications. For details on this functionality, see the section on XSL transformation to EDM below.

- A dataset must be either uploaded as a zip file or it can be sent via HTTP (i.e. zip file download) or OAI protocols. For more details see the chapter on uploading a new dataset below.

> [!WARNING]
> Note that, contrary to Metis, the Sandbox is not equipped to process datasets exceeding 1,000 records. You can still upload datasets that are larger than that, in which case you will see a warning message indicating that only 1,000 records will be processed. See the section on step size to learn how to influence the record sampling method that the Sandbox uses in this case.

Finally, a dataset should contain one record at minimum. If your dataset is empty, you will see an error message.

---

# 4 General interface elements

There are several different methods to interact with the sandbox. Below is a list of the general interface elements and their uses.

## 4.1 Page header elements

The page header contains two navigational elements on the left, both of which are visible at all times.

![](../../attachments/4789a183-ca04-4e0d-96c0-6c9b67a537e7.png)

The ‘hamburger icon’ (the three horizontal lines) on the left opens the side panel with external links and the theme selection.

Furthermore, clicking on the Europeana logo brings you back to the welcome screen at any time (where you can get a list of your recently uploaded datasets if you are logged in – see the section on the welcome screen below).

In the header you will also find the login or the logout button - exactly one of these is visible at any time.

Clicking on the login button brings you to the login screen.

![image-20250909-075332.png](../../attachments/9139f43f-d59a-47d1-ba0f-2770dae8e31a.png)

Clicking on the logout button ends your session immediately.

![image-20250909-075556.png](../../attachments/32525b57-d9fe-49fe-8666-06ffe752e33d.png)

---

## 4.2 Buttons

Buttons are used to upload a dataset.

![](../../attachments/5a53d42d-eb7b-4b29-9fc4-24ed74249d8d.png)

---

## 4.3 Input fields

Input fields are the white boxes where information can or must be entered by you. The description with the input field states what information should or can be entered. Input fields that are required to have a value can be recognised by an asterisk\*.

![](../../attachments/cb9c93ef-f872-44a6-b508-d9bde83b31e8.png)

Invalid or missing entries will result in an error message to be displayed below or next to the input field.

![](../../attachments/6daeae9a-ba4d-4b3e-b690-35e3df2d2085.png)

## 4.4 Page Indicators

Page indicators are shown at the top of the page. They behave as tab headers: clicking on an orb will navigate to the corresponding page. The number of page indicators can vary depending on your use of the Sandbox.

The active page is shaded orange with a yellow border (in the image below, the “Upload Dataset” is the active page). This is also indicated by the page title to the left of the orbs.

![](../../attachments/8f9c86a4-62fc-41bf-8ad7-4e168b888acd.png)

There are page indicators for the following pages (going clockwise from the orange item):

- Upload Dataset
- Track Dataset
- Problem Patterns – dataset overview
- Problem Patterns – record report
- Tier calculations – record report

In addition, a page indicator can display a page’s state.  In the example below the page indicator for the Record Report shows that:

- Data has loaded
- The values in the id fields (supplied by you and always available) reflect the data being displayed, i.e. the form is “clean”

![](../../attachments/e14b5e04-eac8-4398-b92b-789e64671975.png)

A cog indicates that the page is busy. An example of this is when a new dataset is still being processed.

![](../../attachments/e1477805-c4d2-45cf-bd6f-e622e42cccbc.png)

Note that the page indicator (orb) for Problem Patterns can appear twice: once for viewing problem patterns of a dataset and once for viewing problem patterns and individual records.

---

## 4.5 Links

Links are used to navigate between pages or to open popups in the Sandbox. There are different types of links used in the Sandbox interface.

For example:

- The “**track a new dataset”** link takes you to the corresponding page.

![](../../attachments/8d1e91a3-848b-4074-9bbf-c89f338548f5.png)

- The **view detail** links open up a popup that displays the details of an error.

![](../../attachments/66140cf0-de71-4e6f-91fb-01954e39639c.png)

- Links with a **warning sign** open up a pop up with more information.

![](../../attachments/c3444c78-57d8-4a13-8d18-53c829886191.png)

- Links with a **light bulb** take you to the page with more information.

![](../../attachments/5ae4c073-5466-4cf4-aad7-515cdcb90bce.png)

- **Underlined links** switch from view of the tiers.

![](../../attachments/398c05d7-7dee-431f-8e49-39ac7315613a.png)

- External links have an icon.

![](../../attachments/cab31d03-a0a2-4a79-8a0a-820d92efdd9f.png)

- Some links, when hovered, show a small “copy” button which if clicked will copy the link (the URL) to your clipboard:

![](../../attachments/144fd764-d9f2-4ab7-9baf-ec334b8640dd.png)

- Links can be greyed when required information is missing. The image below shows that the Track and Issues links are greyed out because there is no information in the input field left of the links.

  ![](../../attachments/f0d76e65-13cd-4b1d-a67b-1508212d4ab2.png)
- Some links are greyed out and show a little padlock icon. These links are only available when the user is logged in.

  ![image-20250909-080054.png](../../attachments/52fa23b7-1561-4353-9347-375ad7bf916e.png)

---

## 4.6 Drop-down menus

Drop-down menus allow you to make a selection of a list of predetermined values.

![](../../attachments/4dde953b-68a6-44ed-88aa-08512ff0ef2d.png)

---

# 5 The Basics: arriving at the Metis Sandbox

## 5.1 The Welcome screen

The default view, the screen you land on when navigating to the tool, is the Welcome screen.

![image-20260211-082452.png](../../attachments/29415174-21f7-42e8-a566-3288621d1e07.png)

You can click ‘GET STARTED’ to navigate to the Home screen (see section below).

If you are logged in (see session on user accounts below) and if you have recently processed datasets, you will see a list of them on the Welcome screen. You can click on any of these to be taken immediately to the Dataset Processing View for that dataset, from where you can easily find all other information about this dataset.

The page indicators are already active, so you may for instance use the upload icon (the left-most one in the example above) to take a shortcut and navigate directly to the dataset upload form.

---

## 5.2 The page header and side panel

These two page elements are present and functional at any time, in any Metis Sandbox page you may find yourself in.

Most useful is the ‘hamburger icon’:

![](../../attachments/850b0b65-a5af-4bde-91fd-290ae8c52e8b.png)

This icon opens the side panel. This panel contains three external links, three internal links and a theme related option:

![image-20250127-145615.png](../../attachments/8804706e-1939-4c92-a193-232d5761c9d2.png)

The available links are:

- A link to training material, that can be used to try out some of the Metis Sandbox functionality in a more controlled setting.
- A link to the feedback page, that also contains a helpdesk functionality. You can register a bug here, ask for support or suggest a new feature/improvement.

> [!NOTE]
> You are strongly encouraged to use the feedback page in case you find a bug, if you need support or if you come up with an idea for a new feature or the improvement of an existing one. The Europeana Foundation is committed to keep improving the Metis Sandbox for its users.

- A link to the User Guide (which is the document you’re currently reading).
- An internal link to the cookies policy.
- An internal link to the privacy statement.
- An option to switch (toggle) between the two available themes.

---

## 5.3 Creating a user account and logging in

Certain functionality requires you to have a user account and be logged in. This functionality falls into two categories:

1. Functionality that lets you process data,
2. Functionality that lets you access your processing history or other account-specific information.

> [!IMPORTANT]
> The Sandbox is connected to the same Identity and Access Management (IAM) System as other Europeana applications. This means that, if you already have a Europeana account (e.g. for the Europeana website), you can use the same for the Sandbox. And vice versa.

Clicking on the login button activates the login process:

![image-20250909-075332.png](../../attachments/9139f43f-d59a-47d1-ba0f-2770dae8e31a.png)

The login screen will show:

![image-20250909-090258.png](../../attachments/9c2064aa-c6cc-4652-9fe4-f4bda8f06094.png)

If you click on the ‘Join’ button, you can create your user account. You will need to provide your full name and email address, as well as choose a username and a password.

If (or once) you have an account, you can log in by providing your email or username, and your password, followed by clicking ‘Log in’. There is also a ‘Forgot Password’ option: if you provide your email address you’ll be send a password reset link.

Once you log in, you will be brought back to the Metis Sandbox, where additional functionality is now available.

Also, the login button will have been replaced by a logout button. Clicking it ends your session immediately.

![image-20250909-075556.png](../../attachments/32525b57-d9fe-49fe-8666-06ffe752e33d.png)
> [!NOTE]
> Note that the Europeana IAM System features Single Sign-on (SSO). This means that if you log out, you will log out of all Europeana applications, including the Europeana website.

## 5.4 The Home screen

This screen allows you to start accessing the Metis Sandbox functionality. Here you can track an existing dataset, request information about a record within that dataset or create a new dataset. It looks like this:

![image (11)-20260211-100732.png](../../attachments/0aa0caf4-a7e2-4d7c-b224-9d20889a14a2.png)

**A.** Page Indicator: indicates that "Dataset Processing" is the current step.  Once other steps become available then clicking this will return you to this step.  
**B.** Dataset Id input: used to enter the id of a previously uploaded dataset.   
**C.** Record Id input: used to enter the id of a record within the specified dataset. It enables when a dataset id is entered.  
**D.** View a Recent Dataset link. This link enables when you have recently processed datasets. When clicked, it expands to show a list with your recently processed datasets. You can click a row in the list to be taken to the “Dataset Processing” functionality for that dataset.  
**E.** Create New Dataset link: enables and navigates to the “Upload a new Dataset” functionality (see below).  
**F.** Track link. This link enables when a dataset id is entered and, when clicked, takes you to the “Dataset Processing” functionality (see below) for the dataset with this dataset id.  
**G.** Issues (Overview) link. This link enables when a dataset id is entered and, when clicked, takes you to the “Problem Patterns” functionality (see below) for the dataset with this dataset id.  
**H.** Issues (Record) link. This link enables when a record id is entered and, when clicked, takes you to the “Problem Patterns” functionality (see below) for the record with this record id.  
**I.** Tier Report link. This link enables when a record id is entered and, when clicked, takes you to the “Record Report” functionality (see below) for the record with this record id.

> [!NOTE]
> Note: you need to be logged in for the ‘view a recent dataset’ and ‘create new dataset’ links (**D** and **E**) to be enabled. See the section on user accounts above.

When you type a dataset ID or a record ID, a green link will appear in the input field. If you click it, you will be taken to the dataset or record preview as it would look like on Europeana.

![](../../attachments/45322f1e-8444-4e30-94f8-298144baee2d.png)

If you are logged in and if you have recently processed datasets, you will see their ids a suggestions popup above the Dataset Id Input field as you start typing. If you click on a suggestion, it will be copied into the Dataset Id Input. When the field is empty, you can also click on the little hamburger icon (![image-20260211-083600.png](../../attachments/5978f277-d8e8-45a4-b8d7-a8be307a81c3.png)) in the field to trigger the suggestions.

![image-20260211-083955.png](../../attachments/36016ba0-ef77-49a8-beb7-fe784f99bd6b.png)

If you click on the '+' icon in this popup, you will see a clickable table with more details about each of the suggested datasets.

---

# 6 Upload a new dataset

To create a new dataset click on the “create a new dataset” link at the bottom of the home screen (D in the image above). This will take you to the “Upload Dataset” form.

> [!NOTE]
> Another way exists for uploading a new dataset: rerunning an existing one. See the section on rerunning a dataset below.

## 6.1 The Upload Form

The “Upload Dataset” view looks like this:.

![](../../attachments/f8ad7bb2-012c-4365-89ad-d881bc20d0c8.png)

**A.** Step Indicator: clicking this will take you to the “Dataset Processing” step.  
**B.** The dataset name input field.  A dataset name is valid if it contains only letters, digits and the underscore character (‘\_’).  
**C.** The dataset country drop-down.  
**D.** The dataset language drop-down.  
**E.** The harvest protocol radio button set.  
**F.** The zip file input.  This appears because “file upload” is the selected protocol.  If the selected protocol is changed to “OAI-PMH upload” or “HTTP upload” then an alternative field (or set of fields) will appear here.  
**G.** Step size field.  
**H.** An (optional) checkbox to specify that you want the Metis Sandbox Server to transform your dataset using XSLT.  If selected then a file input will appear below it allowing you to upload an XSL file.  
**I.** The “Submit” button: enables when all the (obligatory) fields have been completed.  
**J.** Step Indicator (inactive): indicates that "Upload Database" is the current step.  If you switch to another step then clicking this will return you to this step.  
  
Enter a descriptive name for your dataset in the input field below “Name”. Only letters, digits and the underscore character (‘\_’) are supported. You can select the country and language of the dataset with the dropdown menus.

The next step is to determine the “Harvest protocol”: how you will upload your dataset. This is described in detail below. The “Submit” button at the bottom left will be enabled when all information is filled in and valid.

---

## 6.2 The Harvest Protocol

There are three ways to upload your datasets to the sandbox:

1. File upload: upload an archive (e.g. a zip file)
2. OAI-PMH upload: Ingestion with OAI-PMH
3. HTTP upload: ingestion via a hosted archive (e.g. a zip file) on a server through HTTP or HTTPS

### 6.2.1 Zip File

The “File upload” protocol is selected by default. This option allows you to upload an archive file with a dataset that is stored locally. The supported archive types are `.zip`, `.tar` and `.tar.gz` archives.

![](../../attachments/ef644b39-c495-4a18-9a60-68d51ca2a66a.png)
> [!NOTE]
> Note that, even though it is not currently possible to upload multiple archive files, you can still achieve the same result by wrapping all your archives in one new zip file. The application fully supports nested archives (i.e. zip files of zip files).

### 6.2.2 OAI-PMH

To use the harvest protocol to OAI-PMH, you should enter values for the harvest URL, the metadata format, and optionally a setSpec value. For more details on these, please see the [OAI-PMH specification](https://www.openarchives.org/OAI/openarchivesprotocol.html).

![](../../attachments/b195d783-4e0c-4054-a017-1321105d013e.png)

### 6.2.3 HTTP(S) upload

You can also specify an archive that is accessible with a URL. Set the harvest protocol to “HTTP upload” to be able to enter a value for the URL.  The URL should be the (HTTP or HTTPS) download location of an archive (`.zip`, `.tar` or `.tar.gz` file) that contains the dataset records.

![](../../attachments/523d8bcb-3ea3-44e6-a270-daecd92ef12a.png)

## 6.3 XSL Transformation to EDM (Optional)

It is possible to transform the records in the dataset to the EDM format, using XSLT before any further processing. Check the option “Records are not provided in the EDM (external) format”.  An additional file input will appear for an XSL file to be specified.

![](../../attachments/fe1ba143-515f-4a5c-a43e-d5bee7213754.png)

## 6.4 The step size

This field allows you to influence the sampling behaviour.

![](../../attachments/e91ffcc5-a79d-47fb-a2a5-944c46d253a8.png)

A step size of *n* tells the Metis Sandbox to select every *n*th record for processing. This value must be a strictly positive whole number (i.e. 1, 2, 3, …). The default value is 1.

> [!IMPORTANT]
> If your dataset contains more than 1,000 records, the Metis Sandbox does not process them all. Instead it takes a sample of 1,000 records. By default (with a step size of 1), the first 1,000 records that are encountered in the dataset are selected for processing. But if your dataset is larger and made up of several batches of slightly different records, this may not yield a representative record sample of the dataset. The step size field may be used to achieve a more representative sample.

For instance, with a step size of 3, the records in position 3, 6, 9, 12, …, 3000 will be selected (or fewer, if the dataset is smaller than 3,000 records).

> [!NOTE]
> A good rule of thumb for choosing the stepsize is the following:
>
> - If your dataset contains at most 1,000 records, leave the default value of 1. All records will be processed.
> - If your dataset contains more than 1,000 records, but they are quite homogeneous, leave the default value of 1. The first 1,000 records will be processed.
> - If your dataset contains more than 1,000 records and they vary in composition and/or structure, select a step size as follows. Take the dataset size, divide by 1,000 and round down. For instance: if your dataset has 123,456 records, a good value for the step size would be 123. This way you ensure that 1,000 records are selected with maximum spreading.

---

## 6.5 The Generated Dataset ID

The “Submit” button will become enabled once you have filled all fields.  Click the **“Submit”** button to upload your dataset. You will be redirected to the “Dataset Processing” page, where you can see the data being processed in real-time.

A unique dataset id is generated for your upload and displayed at the top-right of the “Dataset Processing” page.  Remember or save this ID to be able to get back to the dataset in the future (i.e. from the home screen, see above).

---

# 7 Dataset processing

Enter a dataset ID in the Home screen or at the bottom of most other screens and click the ‘Track’ link to track (monitor) the processing of an uploaded dataset, or to see the results after it finishes processing. The “Track” button for the dataset id field is disabled when the field value is empty. This button will enabled when you type in a valid dataset id.

![](../../attachments/6c73668c-b727-4976-bc0e-5cb908c4fba0.png)

When you click this button you will reach the “Dataset Processing” page for that dataset.

> [!NOTE]
> As mentioned above, if you are logged in you can reach the Dataset Processing page for datasets you have yourself uploaded also by navigating from the Welcome screen or from the ‘view a recent dataset’ listing on the Home screen.

Invalid id’s will show a warning, and the submit buttons will be disabled again.

![](../../attachments/6188adb5-8604-4fba-a9c0-c1b2fe01ed21.png)

A record id can only be entered when a valid dataset id has been entered. The links next to the record field are greyed out when the field is empty or when an invalid value has been entered. The links will be enabled once you enter a valid record id.

![](../../attachments/8d35c29b-596f-4ba3-8050-564eb586ac79.png)

See “record provider IDs and Europeana IDs” (below) for more information about record ids and record provider ids.

## 7.1 The Data Processing View

A submitted dataset id will bring up the dataset processing view. It will also change the page’s URL to reflect the id of the dataset processing being displayed.  The dataset processing view looks like the picture below.

![image-20250127-172726.png](../../attachments/3fd5b908-fbca-40cf-bb9c-e5fa63d71edb.png)

**A.** The dataset name.  The tick after the dataset name indicates that processing is complete. Clicking will expand the dataset info panel.  
**B.** The country and language of the dataset selected when the dataset was uploaded.  
**C.** The processing date, preceded by an (optional) flag indicating that not all records in the dataset were processed.  
**D.** The processing steps performed on the dataset (they correspond to the list of items just below, element E).  
**E.** The details of the processing steps performed on the dataset.  
**F.** The (optional) warning indicating that not all records in the dataset were processed. See “step size” above for more information.  
**G.** The (not enabled) record id field.  
**H.** The dataset ID of the current dataset.  
**I.** A link to the dataset preview as it would look like on Europeana - this only appears following successful dataset publication.  
**J.** The control for running the DE-BIAS report - this only appears following successful dataset publication. See the chapter on the DE-BIAS project below.  
**K.** The tier statistics tab opener.  
**L.** The tier-zero indicator.

The tick after the dataset name indicates that processing is complete, and the generated dataset id is shown at the top-right.

The main (white) panel shows a list of processing steps, detailing how many records were processed during each, and an (optional) warning indicating that not all records in the dataset were processed.  Clicking this warning, if present, will show additional information about the import.

The dataset id will also be filled in at the bottom of the screen, enabling the the “record id” field.

To track the data processing of a different dataset just replace the value in the dataset id field with another id and click the “track” button.

## 7.2 Dataset details and rerunning a dataset

Clicking the dataset name will expand the info panel and show additional data:

![image-20250127-173413.png](../../attachments/a8098adf-6e96-4b5a-9c22-113d82353200.png)

**A.** The dataset name - clicking it again will now collapse the panel, hiding the extra info.  
**B.** The country and language are now shown with titles.  
**C.** Data about the upload is also now shown.  
**D.** The (optional) field indicating that an XSL transformation was applied to convert the record to EDM. See the section “XSL Transformation to EDM” above.

Certain datasets can be rerun. For this, a rerun button ![image-20260211-103842.png](../../attachments/11658087-710a-45cd-ab90-42af0d722e89.png) is available.

![image (12)-20260211-103626.png](../../attachments/a1c21a9c-1035-49f6-978d-28fe3c0e5a23.png)

The rerun button can be found next to the dataset ID (**A**) and in the dataset details panel (**B**).

> [!NOTE]
> You need to be logged in for the rerun option to be available. Also, you can only do this on your own datasets. The button is disabled if the dataset was created using a zip file upload or an XSTL transformation to EDM: those datasets can not be rerun.

By clicking on either of the rerun buttons you can trigger a rerun for this dataset. The Sandbox will attempt to harvest the data from the same source. This is a useful functionality if you have changed or updated the data at source. When you click the button, you will see a condensed upload form where this dataset’s settings are prefilled. Note that the Sandbox will make a suggestion for the name of the new dataset different from this dataset’s name.

![image-20260211-094527.png](../../attachments/a6bffa6e-021b-449d-9211-ad72b16a787d.png)

You can make any changes you like. Then you can start processing by clicking the ‘upload’ button ![image-20260211-094741.png](../../attachments/6c533657-0243-4a0b-a929-52f3b4b3f2e1.png). If you do, you will see a notification link that a new dataset was created:

![image-20260211-095017.png](../../attachments/f4663d87-2001-4f6d-ba9a-ab92f86c08a6.png)

Clicking on this notification link will bring you to the new dataset. Clicking on the 'X' will close the form and you stay in the current dataset.

---

## 7.3 The Metis workflow

The data goes through nine steps as part of the processing workflow.  These steps are:

1. Harvest (**H**): how many dataset records have been successfully imported
2. Transformation to EDM (**Te**): How many records have been transformed to the external EDM format (optional step)
3. Validation External (**Ve**): how many records passed EDM validation
4. Transformation (**T**): how many records have been transformed from the external EDM format to the internal EDM format
5. Validation Internal (**Vi**): how many records have passed internal validation
6. Normalisation (**N**): how many records have been normalised. Normalisation acts on individual values in the data and could include the deletion of redundant whitespace or of duplicate values
7. Enrichment (**E**): how many records have been successfully enriched
8. Media Processing (**M**): how many records have had their associated media processed
9. Publish (**Pu**): how many records have been published, i.e. uploaded to the Sandbox preview environment (which is a copy of the ‘real’ Europeana website, but does not share the same data).(see chapter 7)

The colours of each step indicate how successful this step was:

- **Green:** (success) - the step completed without errors, and all records are considered suitable for ingestion
- **Yellow:** (non-critical warning) - problems with the records have been detected, but the records could still be processed.
- **Red:** (critical warning) - more serious problems with the records have been detected, and (some of) these records could not continue their path through the pipeline. These should longer be considered for ingestion (in their current form).

---

## 7.4 The Data Processing Errors Window

Shown below is an example of a dataset that processed with many errors:

![](../../attachments/488e55c3-4d8d-4436-95c2-9e8c1cbabd68.png)

**A.** A link to the errors window  
**B.** The bold font of the number indicates that this is another link to the errors window  
**C.** No report is available for this error, so the the number does not have a bold font and there is no link to the errors window

Errors are flagged by red numbers in the panel, and if an error report is available, by the “view detail” links in the right-hand column.  The red number indicates the number of records affected (one in this case) and this number is repeated (parenthesised) in the “view detail” link.The red number also serves as a link to the error report, if available. In the screenshot above an error report is available for all processing steps apart from the last.

Clicking a link to the errors report will open a pop-up window, allowing you to see the error detail.

![](../../attachments/df523be3-5f0a-4b05-a12e-9fd4774c8269.png)

---

## 7.5 View the published records

Click on **“view published records”** (item J in the image in 7.1)  to view your final data in a copy of the Europeana website. This link is shown in the top-right of the submitted “Dataset Processing” page UI, underneath the generated dataset id.  This will show the dataset records as published on the Sandbox Preview environment.

> [!WARNING]
> **15 minute delay for data publication**
>
> Please note that it can take up to 15 minutes after the publish step finishes for the data to become available on the website. Please wait if your data is not showing yet.

It may, for example, appear like the image below.

![](../../attachments/85bddcc2-9f16-4ae1-a544-9e3b874db921.png)
> [!WARNING]
> **Tier 0 records hidden by default**   
> It is possible that not all your items are shown in this view. Records with media Tier 0 are hidden by default. You can make these records visible by clicking on “More filters”, scroll down, click the button “Show only items not meeting our publishing criteria” and click to confirm this filter.

![](../../attachments/478faca7-0643-4a24-88b6-ca408bcc887b.png)

## 7.6 Tier Statistics

Once a dataset has been processed it’s possible to view its tier statistics to help assess the dataset’s quality. The dataset processing tab will look something like this once a dataset has been processed:

![](../../attachments/9548ef82-1430-4f7d-991b-65790601a975.png)

**A.** The tier statistics tab opener

When you click the tier statistics tab opener, you will see a tab that looks like this:

![](../../attachments/7577c848-c2dc-4bc2-a6b3-f9a5b092e5e8.png)

**A.** The pie chart gives an overview of the statistics - shown by the content tier dimension (by default).

**B.** If you click the column headers, you toggle the column sort order and change the data dimension of the pie chart to that header’s default.

**C.** The second row of clickable column headers allow specific data dimensions to be set and sorted on.

**D.** The search input allows you to filter the record data by (part of the) record id.

**E.** The data grid shows the record data in a panel that you can scroll through. The fields are record id, content tier, content tier license, metadata tier (aggregate value), metadata tier (language dimension), metadata tier (enabling elements dimension) and metadata tier (contextual classes dimension). If you click on a record id, you will be taken to the tier calculation report for that record (see below).

**F.** Page navigation is enabled where necessary.

**G.** Here you can select the number of rows shown at a time in the table.

**H.** Here you can jump to a specified page by entering a (valid) page number.

**I.** The dataset floor row gives the lowest tier value present in the dataset (and the value you probably wish to look at to improve the quality of your data).

## 7.7 Filtering Tier Statistics

Clicking a pie-slice (or its corresponding legend item) will filter the data down to that value. A click on the value "3" in the pie, for example, will restrict the grid to showing only records that have a content tier value of "3".

![](../../attachments/3f35edbf-ca2b-4e7c-90d8-dd8ba72ad00f.png)

**A.** The active filter. Clicking the active pie-slice will remove the applied filter.

**B.** The active filter's legend item. Clicks on legend items are equivalent to clicks on pie-slices.

**C.** Orange column headers indicate the active filter.

**D.** A new summary row appears below the data grid indicating aggregate values for the filtered data.

**E.** The pagination updates to reflect the filtered data.

**F.** Only records with a content-tier value of "3" are visible in the grid.

## 7.8 Sorting Filtered Tier Statistics

When dataset tier statistic data is filtered by content tier you can sort it by one of the other dimensions by clicking its column header. Usually clicking a column header changes the pie chart dimension and sorts on that column, but when a filter is active the sort will be applied within the data dimension that has been filtered on.   
  
Here we see data that was filtered by content tier (value 3) and sorted by metadata tier (aggregate value).

![](../../attachments/5d469bee-6880-4f61-986d-416967f2babd.png)

**A.** Clicking this column-header will not change the dimension (it will remain “content tier”), but it will the sort (by metadata tier) within that dimension.

**B.** As before, the specific type of metadata tier sort (aggregate value) is clarified with an arrow-head indicator in the second sub-header row.

---

# 8 The tier calculation report

You can view a tier calculation report by clicking on a record ID in the tier statistics grid (see above). Alternatively, you can view the report by entering both the id of a dataset as well as the id of a record within this dataset (see below).

## 8.1 Record Provider Ids and Europeana Ids

Every processed record has both a Provider id and a Europeana id.

- A Europeana id begins with a forward slash followed by the record’s dataset id, another forward slash and then a further sequence of (non-whitespace) characters. You can find the Europeana ID of a specific record by clicking the dataset preview link and finding and inspecting the records there.
- A record’s Provider id, on the other hand, can be any sequence of (non-whitespace) characters, and is the value that can be found in the ‘rdf:about’ attribute of the ‘providedCHO’ section of your record.

You can search for a record using either of these record ids, so the “Report” button will enable itself when any sequence of non-whitespace characters has been entered into the record id field.  If, however, the UI detects that you’ve entered an id that matches the format of a valid Europeana record id, then it will show a line connecting the record id with the dataset id, as shown here:

![](../../attachments/73aa3c6c-e32a-4ce1-acd0-025a70806fae.png)

**A.** The record id begins with a slash followed by the dataset id, so the id fields are shown as connected.  
**B.** You can now open the record report by clicking the button labelled “Tier Report”.

---

## 8.2 The Record Report

The record report - or Tier Report - is divided into two main sections:

- the content tier section
- the metadata tier section

You can navigate between these sections by clicking the corresponding navigation orbs. The computed value of each tier is shown within its navigation orb at the bottom.  These computed values are single digit: numeric in the case of the content tier.

In the illustration below the computed values are “3” (for the content tier) and “A” (for the metadata tier).

![](../../attachments/7ae4bc05-0507-464e-a345-d7c485a0241b.png)

**A.** Page Indicator: the inactive "Dataset Processing" orb, indicates that this page is not active and, if clicked, will bring you to the dataset processing page.  
**B.** The Record Report summary: top-level information about this record as well as record download and viewing links.  
**C.** Tier Navigation Orbs: you can toggle between the content and the media tier report from here.  
**D.** Content Tier Information: data about the record's content tier.  
**E.** Media Navigation Orbs: you can navigate multiple media items from here.  
**F.** Processing Errors: record processing error information appears here.  
**G.** Page Indicator: indicates that "Record Report" is the current page (via its orange colour) and that the form below is “clean” (via its tick icon).

---

## 8.3 Content Tier Media Information

The media information appears under the content tier breakdown section. If there are 5 or fewer items, then a navigation orb corresponding to each item will appear.  The icon of each navigation orb illustrates the type of media item, as shown below.

![](../../attachments/5d1308c1-8d30-4a5e-9013-edb521416afb.png)

If there are more than 5 media items available in the record report then the navigation orbs will be replaced with navigation arrows, an editable field and a spinner allowing you to browse the items or jump directly to a specific one, as shown below.

![](../../attachments/a5721694-08e2-4c77-8f22-793412e1fcb5.png)

---

## 8.4 Metadata Tier Information

You can see the record report’s metadata tier information by clicking on the metadata tier navigation orb.  Metadata tier information is split into three sub-sections:

- Language dimension
- Enabling Elements Dimension
- Contextual Classes Dimension

These, like the main sections of the report, are navigable by clicking on the corresponding navigation orb.

**Active language dimension**

![](../../attachments/d64fa3fc-f892-4723-8f75-8bbcebdc5824.png)

**Active enabling elements dimension**

![](../../attachments/9d290599-1d82-4790-b7bc-31c6c7eb0fc4.png)

**Active contextual classes dimension**

![](../../attachments/2d05fc30-124e-40c2-b031-033fdeed0668.png)

---

# 9 Problem patterns

You can view problem patterns for both a dataset and for a record.  The dataset id and record id fields each have a (secondary) link labelled “Issues”.

![image (13)-20260211-163558.png](../../attachments/b4e90944-abca-4317-b3f0-c90d538a7810.png)

Clicking “Issues (Overview)”, next to the dataset id input field **(A)**, will open a problem viewer page for the whole dataset. Clicking “Issues (Record)” **(B)** will open a problem viewer page for an individual record.

## 9.1 Dataset / Overview

The problem pattern viewer for datasets shows all the problem types that occur within a given dataset.

![](../../attachments/d945fd00-a322-4090-adcf-dd8ccfd33cde.png)

A key is shown (P1, P2, P3 etc.) together with a list of records in which that problem pattern was found. The little arrows at the top-right corner may be used to navigate between the different problem patterns.

The record-references behave as (internal) links to the separate instance of the problem pattern viewer used for records (with the exception of the references for P1, as they are not displayable for individual records).

The problem pattern report can be downloaded using the “export as pdf” link.

The 8 problem patterns that are in use now are:

|         |                                              |                                                                                                                                                                                                                                               |
|:--------|:---------------------------------------------|:----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Key** | **Title**                                    | **Description**                                                                                                                                                                                                                               |
| P1      | Systematic use of the same title.            | Check across all records if there are any duplicate titles, ignoring letter (upper or lower) case.                                                                                                                                            |
| P2      | Equal title and description fields.          | Check whether there is a title - description pair for which the values are equal, ignoring letter (upper or lower) case.                                                                                                                      |
| P3      | Near-Identical title and description fields. | Determine whether there is a title - description pair for which the values are too similar (or if one contains the other). We do this ignoring the letter case.                                                                               |
| P5      | Unrecognisable title.                        | Apply heuristics to determine whether a title is not human-readable. We check whether there are at most 5 characters that are not either alphanumeric or simple spaces. We also check whether the value fully contains a dc:identifier value. |
| P6      | Non-meaningful title.                        | Check whether the record has a title of 2 characters or less as a rough heuristic of whether a title is meaningful.                                                                                                                           |
| P7      | Missing description fields.                  | Check whether the record is lacking a description (or only has empty descriptions).                                                                                                                                                           |
| P9      | Very short description.                      | Check whether the record has a description of 50 characters or less and no longer description exists in the same language.                                                                                                                    |
| P12     | Extremely long titles.                       | Check whether the record has a title of more than 70 characters.                                                                                                                                                                              |

> [!IMPORTANT]
> You can see that the numbering of the problem patterns is not consecutive. There are more problem patterns identified than in use at the moment. The number of problem patterns might change in the future.

Click on the title of a specific problem pattern to see a description.

![](../../attachments/e6dd6d45-8318-482e-be93-d91726479c74.png)

## 9.2 Record

The problem pattern viewer for records shows all the types of problem patterns that occur within a single record.

![](../../attachments/86fb95fe-21e6-40f8-88bc-bce1b5cde3ae.png)

Note that two of the page indicators in the image above show the same icon - one for each instance of the problem pattern viewer.

If you click on the “</>” button to the right of the problem pattern viewer, a panel expands that provides access to download links for the record.

![](../../attachments/2c74ff98-962c-45ad-a5da-91cb44b637ec.png)

---

# 10 Tier Zero Records

You will be warned if your dataset contains any records that have a “tier zero” rating, either for the content tier or the metadata tier in the track tab of the dataset processing page.

![](../../attachments/ad30f1c1-4f4d-402a-be58-9383c166837a.png)

One or two indicators will be shown on the right side of the screen whenever a “tier zero” record was detected. The first is for records with content tier zero (the orb with stars), the second for records with metadata tier zero (the orb with a gauge). Only one may appear, or both, as appropriate.

![](../../attachments/adb5cff0-da22-4fcc-b7c3-e91cf7e09500.png)

Click the warning indicators to see the tier-zero warning panel. This panel will show links to at most 10 sample records that were detected as having content or media tier 0.

![](../../attachments/5e3dff6c-45fe-47b7-9ded-4a1649302270.png)

These links open the Record Report (see above) for the clicked record, opening the relevant subsection of the report according to whether the tier zero warning pertained to the content-tier or the metadata-tier. The small yellow triangular warning icons will be visible until the warnings have been reviewed. Only one warning is present in the image above, because the content tier zero records have already been viewed.

---

# 11 Detecting contentious terms - the DE-BIAS project

![image-20250102-105552.png](../../attachments/c430a7ca-2879-4238-bc78-6f7ddf130101.png)

One of the results of the DE-BIAS project (2023 - 2024) is functionality to detect contentious or biased terms in your data. From the Sandbox, you may use this functionality to check your dataset for biased terms after your dataset has finished processing.

> [!IMPORTANT]
> This functionality is provided as-is. For more information see: <https://pro.europeana.eu/project/de-bias>

If the DE-BIAS detection is triggered, the values in certain fields of each successfully processed record are analyzed, provided that they have a valid language qualification (`xml:lang` attribute) and that this language is one of five supported languages (Dutch, English, French, German and Italian). Once processing is complete, you will be able to access a full listing of any contentious terms that were found in the analyzed field values.

> [!NOTE]
> You can get direct access to the detection tool here: <https://debias-tool.ails.ece.ntua.gr/>. The Sandbox processes your data with both the NER and disambiguation functionalities activated. Note that the disambiguation option is expected to be decommissioned in early 2026, after which time only the NER option will be activated.

## 11.1 Running the DE-BIAS analysis

Once a dataset has finished processing, you may choose to run DE-BIAS analysis. In order to do this, you can click the "run report" control next to the "DE-BIAS“ icon. You can find this icon in the top right corner of the data processing view (see the section “The Data Processing View” above).

![image-20250217-151341.png](../../attachments/d15449d3-72aa-453b-8c02-6d74c43bdaab.png)
> [!NOTE]
> Note: you need to be logged in for the ‘run report’ link to be enabled. See the section on user accounts above.

When you click this control, the detection analysis will begin, and a running count of the detected contentious terms will appear next to the control as this process runs.

![image-20250217-151203.png](../../attachments/5e1ebed8-4a01-4448-9cda-b18046dc5069.png)

Once it is complete, an eye icon will appear. If you click on the detection count or on the eye icon, you will open the DE-BIAS report.

![image-20250217-151327.png](../../attachments/ad5d80ee-d6a0-4827-9d53-f20ff36c702b.png)

## 11.2 The DE-BIAS report

The DE-BIAS report opens in a modal window.

![image-20250217-151950.png](../../attachments/5a44000b-13b6-4cfb-a5ce-82d1443c117c.png)

**A.** If you click on this “info” button, you will see an information panel describing the DE-BIAS functionality.  
**B.** If you click on this "download" button, the full report will download as a CSV file.  
**C.** Each item in the report consists of a block that contains the basic information about the detected term. You will find the Europeana id of the record where the term was found, the field where the term was found, the language of the term, and the term itself in its context.  
**D.** You can click on this link to see the record.  
**E.** The detected term is highlighted in its context. If you click on it you will see more information about the term and its classification as contentious or biased, such as a more detailed description of the issue, suggestions for addressing the issue, alternative terms to use and literature references.  
**F.** You can click on this button to close the DE-BIAS report.

---

# 12 Troubleshooting

**Dataset not found**

![](../../attachments/545a0662-8dca-48b0-a338-fc09d073f74a.png)

Every two weeks the sandbox is emptied. It is highly possible that the dataset has been removed because of this.
