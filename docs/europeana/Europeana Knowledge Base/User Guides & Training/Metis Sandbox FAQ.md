---
tags:
  - '#metis-sandbox'
  - '#faq'
---

[User Guides & Training](../User%20Guides%20&%20Training.md)

# Metis Sandbox FAQ

# How can we help you?

The purpose of this FAQ document is to answer questions regarding the functionalities of the Metis Sandbox, to explain error messages or to address any other relevant questions. When you have a question, please read this page.   
If your question still remains unanswered, please submit a ticket via our [Customer Helpdesk](https://europeana.atlassian.net/servicedesk/customer/portal/10).   
For more information on how to start working with Metis Sandbox, please consult the [Metis Sandbox User Guide](Metis%20Sandbox%20User%20Guide.md)

<details>
<summary>1. Why do I get an error message when I try to track a dataset using dataset id?</summary>

If you are using the dataset id to retrieve a specific dataset and you get an error message, this means that this dataset was either never created or no longer exists.

> [!NOTE]
> The Metis Sandbox gets **cleaned up every night**. Datasets older than one week will be removed and are no longer accessible.  
> Datasets that are deleted from the Metis Sandbox will need to be uploaded again for testing.

</details>

<details>
<summary>2. Why is my dataset not starting to process?</summary>

If you get no errors when you create a dataset but the workflow seems to not progress, please wait. There is a limit to how many workflows can run simultaneously, which means other datasets are progressing in parallel and your set is waiting in the queue to be picked up as soon as the previous one is done.

> [!WARNING]
> **Do not create a new dataset** as this will make the queue longer and it slows down the tool.

</details>

<details>
<summary>3. Why is my dataset stuck at a specific step and not progressing further?</summary>

If you created a dataset and one of the workflow steps does not progress, please wait. There is a limit to how many workflows can run simultaneously, which means other datasets are progressing in parallel and your set is waiting in the queue to be picked up as soon as the previous one is done.

> [!WARNING]
> **Do not create a new dataset** as this will make the queue longer and it slows down the tool.

</details>

<details>
<summary>4. I used the correct OAI-PMH parameters for my dataset but the harvesting fails. Why is this happening?</summary>

If you set the harvest protocol to OAI-PMH upload, you must enter valid values for the harvest URL, metadata format, and optionally a Setspec value, which specifies set criteria for selective harvesting. If the harvest step fails for unknown reasons, please make sure you have used the **correct request parameters**.

> [!NOTE]
> Remember to always add in the form the correct metadata format (be careful about using the correct case letters) e.g. EDM, edm, Edm, rdf as used within your OAI-PMH endpoint.

</details>

<details>
<summary>5. How can I retrieve the record id?</summary>

The record id is one of the variables in the URL path of the item. In the URL this is the part after “/item/” and consists of the dataset id followed by record id. Make sure to include the first forward slash, resulting in the form of  **”/dataset\_id/record\_id”**.

![](../../attachments/2a2d8da6-b0e4-477a-bf8e-3f98010e18d0.png)

</details>

<details>
<summary>6. Can I use the Metis Sandbox to publish my dataset directly to the Europeana website?</summary>

Sandbox users **cannot publish** their data directly to the Europeana website using this tool. The Metis Sandbox is a test environment to validate the data before sending it further to the Europeana DPS team.   
If you wish to publish the content that you tested in the Sandbox, you need to follow the existing data aggregation steps.

</details>

<details>
<summary>7. Can I edit my dataset details (e.g. name, country, language) after the dataset has been created?</summary>

You can only add the dataset details once. If you wish to make any changes or re-process a set, you will need to create a new dataset in the Sandbox. This also allows you to see the differences between the older version and new version of your dataset.

</details>

<details>
<summary>8. What is the best dataset name I can use for my set?</summary>

Ideally, a dataset name for the Sandbox should have the name of the data provider, an indicator of a version and possibly the name of the person that performed the test. The upload date and time, language and country selected are not necessary to be included in the dataset name.

</details>

<details>
<summary>9. Can I upload any type of file for ingestion?</summary>

For file uploads we only accept .zip files.

</details>

<details>
<summary>10. Processing of my set is finished but I cannot view the objects in the copy of Europeana website. Am I doing something wrong?</summary>

If a set has passed the last workflow step, it takes up to 15 minutes for previews to generate in the Metis Sandbox. If the objects are not shown yet, please wait a few more minutes.

> [!NOTE]
> It is possible that not all your items are shown in this view. Records with **content tier 0 are hidden** by default. You can make these records visible by clicking on “More filters”, scroll down, click the button “Show only items not meeting our publishing criteria” and click to confirm this filter.

</details>

<details>
<summary>11. Why do I get a warning that only the first 1,000 records will be processed?</summary>

Currently, a dataset size for the Metis Sandbox **must not** exceed 1,000 records. If your dataset is larger than that, you will see a warning message indicating that only the first 1,000 records will be processed.

</details>

<details>
<summary>12. What is the minimum number of records I can test in the Sandbox?</summary>

A dataset should contain **one record** at minimum. This applies to all harvesting methods.

</details>
