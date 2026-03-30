---
tags:
  - '#data-publishing'
  - '#jira-guide'
  - '#data-processing'
---

[User Guides & Training](../User%20Guides%20&%20Training.md)

# JIRA guide for partners

The Europeana Data Publishing Services team (DPS) is the main point of contact for all data partners wishing to publish data in the Europeana website. Since January 2019, the Europeana DPS team adopted [scrum](https://en.wikipedia.org/wiki/Scrum_(software_development)) to manage the work of the team and since July 2019, we use [Jira](https://en.wikipedia.org/wiki/Jira_(software)) as a ticket tracking system to organise the work of the DPS team.

- [Why Jira?](#why-jira)
- [Getting access to Jira](#getting-access-to-jira)
- [The Data Partner Epic](#the-data-partner-epic)
- [The dataset as a ticket](#the-dataset-as-a-ticket)
- [Requesting an update of an existing dataset](#requesting-an-update-of-an-existing-dataset)
- [Creating a ticket for a new or missing dataset](#creating-a-ticket-for-a-new-or-missing-dataset)
- [The Jira Guide Epic](#the-jira-guide-epic)
- [Timeframe for accepting requests](#timeframe-for-accepting-requests)
- [Prioritisation of work](#prioritisation-of-work)
- [Notifications and the ticket status](#notifications-and-the-ticket-status)
- [Configuring notifications in Jira](#configuring-notifications-in-jira)
- [Importing data from Jira into Google Sheets](#importing-data-from-jira-into-google-sheets)

# Why Jira?

Working with Jira makes the work of the DPS team and the data publication tasks more transparent. It also helps to populate the backlog and prioritise the work on data publication.

Both DPS and data partners can follow the progress of individual datasets, each represented by a ticket, and exchange feedback quickly and easily.

Colleagues and partners that regularly work with Jira among our data partners have reported to us that it has become easier to monitor the progress of data processing work compared to communicating via emails or Google docs.

# Getting access to Jira

For every data partner contact person that needs to be involved in the data publication work, access to Jira is needed. For this to happen, **EF needs to be informed about who requires access, and needs an email address from the person that will be added to Jira**. This will trigger the person to receive an invite to join Jira and to create a Jira account.

![](../../attachments/7ac6be71-5cb4-4ae4-8877-8a0bca0c8b56.jpg)

We aim to have one to three main contacts per data partner. It is also possible to register an aggregator specific email address, like a generic contact email account that several people have access to. This way it also improves flexibility to e.g. have other people that only temporarily need access to Jira to work on a ticket.

![](../../attachments/eddd7c58-6955-4999-b718-32b09b7a67b3.jpg)

# The Data Partner Epic

Every data partner has a **high-level ticket** (called **epic**) that is named after the aggregator.

There is **one unique URL** for every data partner epic that unites all other tickets relevant for this data partner. The list of epic URLs is in [a separate sheet](https://docs.google.com/spreadsheets/d/1Y1cbw2ZDGJ6jg6D994C88kxOUGl1afyoJVUrOIwfR6Q/edit?usp=sharing).

The main contact person/s for the data partner alone will have access to their specific epic, so you will not be able to see and interact with the data processing work of other aggregators. This is important with regard to data protection regulations as the DPS Jira project contains some personal data which cannot be publicly exposed.

![](../../attachments/d80b7875-ff5f-4f9a-a8c8-d1c16dafcfd3.png)

# The dataset as a ticket

Every dataset that was processed and published since we work with Jira has a ticket in Jira that is linked to the data partner epic.

Its name consists of the **Europeana dataset ID** plus the **name of the data provider**. While the epic itself refers to the data partner as a whole, the dataset ticket will collect **specific information** about the dataset, such as recommendations for quality improvements and links to the set in the preview environment as well as a link to the published data in the Europeana website.

Data ingestion specialists will comment on the ticket with feedback on the specific ingestion round and tag the data partner when the work is complete or if advice is required. Email notifications will be sent to the data partner with every comment or status change. The ticket can also be checked at anytime regardless of status and the data partner can respond when necessary. This feedback exchange between data partner and EF **is replacing email communication for most of the data specific communication** on datasets.

It is also possible to upload attachments to Jira (e.g. a sample dataset). The default maximum file size for these attachments is 10Mb.

![](../../attachments/687126ec-a0c0-4eff-a383-f6b15996b630.png)

# Requesting an update of an existing dataset

If you would like to request that the DPS team considers your dataset for processing, then you should add a **comment** to the relevant ticket requesting an update.

Please add any relevant information, such as details of additional records, quality improvements etc.

The DPS team will be notified and we can include the request in our planning.

![](../../attachments/d0f73006-3bad-44bb-b1a6-351b9375572a.png)

# Creating a ticket for a new or missing dataset

For new and missing datasets that do not yet have a Jira ticket, data partners can create one by entering all relevant details for the dataset via the [DPS service desk](https://europeana.atlassian.net/servicedesk/customer/portal/5/group/11/create/72).

This way we can establish the basic information for every dataset, create a ticket and then move it into our workflow to be linked with the appropriate data partner epic.

The link to the service desk is also in your epic, so it will be available to you when you need it.

![](../../attachments/13d67bfa-754f-4ba4-b8b9-39c1511e7fa9.png)![](../../attachments/5061cc2c-59aa-4e74-a0af-4789688c5c04.png)

# The Jira Guide Epic

In addition to the data partner epic and the dataset tickets, we have created [one central epic](https://europeana.atlassian.net/browse/AGG-480) that all data partners have access to. In this epic we provide this guide alongside general updates relevant for all of you. In this epic we will also flag periods when Metis may be down for maintenance and we cannot publish. Like with other tickets in Jira, data partners will get email notification once a new comment or update was added to the ticket.

# Timeframe for accepting requests

Europeana DPS is working in sprint cycles of **two weeks** and our sprint starts on **Tuesdays**.

The preparation for every sprint starts on the **Monday before the Tuesday**. Therefore in order for us to consider your request for data processing in the next two week period then **please ensure it has been received on the Monday before the next sprint**.

Once your ticket is pulled into the sprint the DPS team will aim to **complete the work within this two week period.** In case of any unforeseen issues that might affect this progress, the data partner will be informed in the comments of the specific ticket.

# Prioritisation of work

At the start of the sprint we have a planning meeting where our work for the next two weeks is defined. This is the last chance for us to discuss and accept recent dataset update requests for the upcoming sprint. Accepting new tickets after the sprint has started will change the scope of the sprint and so we can only consider introducing more tickets where these are deemed to be a high priority by the Product Owner (Henning Scholz) or in a quiet period where many other tickets are already complete.

As a rule, every dataset update request submitted by a data partner will be added to the bottom of the backlog.

Europeana DPS is working on such requests on a **first come first serve basis**, however we will give datasets a higher priority where important deadlines are involved, if there is a high demand (e.g. from users) or if the data is of demonstrably high quality.

# Notifications and the ticket status

As soon as a dataset is prioritised and planned into the upcoming sprint data partners will receive **notifications**.

> [!TIP]
> Notifications indicate changes in the status of a ticket:
>
> - The default status of every ticket is **‘to do’**.
> - As soon as Europeana DPS is working on it, the status will be changed to **‘in progress’**. During this stage comments may be added with more detailed information on the status of the work.
> - If the DPS team has completed work on the ticket (here defined as processing the dataset and giving feedback to the data partner) then the status of the ticket will be updated following three different scenarios:
>
>   - The dataset is considered ready for publication by the DPS team and a preview link is sent to the data partner, together with feedback. The status of the ticket will be changed to ‘**ready to publish**’ and the data partner will be notified.
>   - The dataset has encountered issues during processing that prevent the dataset from being published. In cases where the issues are to be investigated (and fixed) by EF, the ticket status will be changed to ‘**issues on EF side**’ and the data partner will be informed about the actions that will be taken.
>   - The dataset has encountered issues during processing that prevent the dataset from being published. In cases where the issues are to be investigated (and fixed) by the aggregator or data provider, the ticket status will be changed to ‘**issues on agg side**’ and the data partner will be notified to trigger a further investigation.
> - If a dataset is published (and only then), the ticket will be closed and the status will be changed to‘**done**’.

If you wish to reopen a closed ticket then you simply have to comment on it stating your request.

![](../../attachments/4b24d0b7-4a4a-4769-9c90-fe8d459332a9.png)

# Configuring notifications in Jira

Should you wish to configure notifications in Jira then please read below

> [!TIP]
> 1. click on your icon (lower left corner of the page)
> 2. click on ‘personal settings’ and customise as needed.
> 3. By default the notifications are set to ‘notify me’ for your own changes, i.e. even when you add a comment to a ticket you get an email about it. If you don’t want this, change to ‘do not notify me’.

![](../../attachments/b7bd8a31-bab2-4628-9834-d503d36aef63.png)

# Importing data from Jira into Google Sheets

With the Jira Cloud for Sheets add-on we now have the option to import data from Jira into a spreadsheet using JQL (Jira Query Language). This means we can generate various different reports, for example:

1. Overview of all tickets linked to the data partner epic
2. Overview of all tickets that were updated within a specific time frame (e.g. last sprint, last month etc.)
3. Overview of all tickets that were completed (marked as “Done”) within a specific time frame

JQL allows users to select filters for importing data - this means that spreadsheets will only contain columns specified in the filter. DPS team supports the following filters:

1. *Aggregator name*: data partner’s name
2. *Key*: unique identifier of the ticket
3. *Assignee*: name of the DPS team member responsible for the ticket
4. *Sprint*: name of the sprint(s) in which ticket was worked on
5. *Updated*: date when ticket was last updated
6. *Data provider*: name of the institution that provided data to the aggregator
7. *Summary:* title of the ticket. For datasets this is the Europeana dataset ID and the name of the data provider
8. *Status*: allows you to track progress of the ticket. The four possible values are:

To Do, In Progress, In Acceptance, Done

1. *Fix version*: all datasets that have value "Data publications - name of the DPS team member" were processed up to the preview and are waiting to be published
2. *Description*: here you can find additional information about the set (e.g. link to the set in the preview environment as well as a link to the published dataset, recommendations for quality improvements etc.)
3. *Flagged*: if there are any internal blockers preventing DPS team from processing data, the dataset will be marked with a flag and value "Impediment" will appear in the spreadsheet
4. *Data Submission Details*:  OAI endpoint, setSpec, metadata format, number of records, dataset ID etc.

If you would like to know more about the imports generated with Jira Cloud for Sheets, please contact the DPS team.
