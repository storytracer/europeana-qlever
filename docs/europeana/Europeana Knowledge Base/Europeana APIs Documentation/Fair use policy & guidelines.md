
[Europeana APIs Documentation](../Europeana%20APIs%20Documentation.md)

# Fair use policy & guidelines

The Europeana Foundation (EF) is committed to provide the same level of service to all of our users. For this reason we have established a fair use policy to be applied to all of Europeana APIs.

## Fair-use policy

- To ensure an even performance of the Europeana APIs to all Users, it is imperative that you adhere to fair and reasonable use of the Europeana APIs to seek to prevent downtime, loss of or corruption or damage to data and/or other errors or technical issues that may result from excessive use.
- Use of the API must be limited to a reasonable number of concurrent requests to an API, together with an appropriate wait period for completion of those calls before commencing further calls. Europeana may specify a limit per type of request and/or accross all Europeana APIs, to which you will be required to adhere.
- In the event that you receive an error response resulting from reaching the limit considered as reasonable for using the Europeana APIs, you must reduce the number of concurrent requests to a reasonable limit and read the documentation on how to best make use of the Europeana APIs. If optimizing and/or lowering your usage will not allow you to fulfill your use case in reasonable time, please get in contact with the Europeana API’s customer support at [api@europeana.eu](mailto:api@europeana.eu) for further assistance.
- The failture to comply with this policy may result in your access key be temporarily blocked or even revoked.

## How can I lower my usage of the Europeana APIs?

If your interest is to access metadata for a large amount of items, we recommend looking into our [Dataset download and OAI-PMH service](API%20Suite/Dataset%20download%20and%20OAI-PMH%20service.md). Considering that the latter are structured per dataset, we recommend using the [Search API Documentation](API%20Suite/Search%20API%20Documentation.md) to identify all the items that you are looking for and faceting using the “edm\_datasetName“ to identify the respective datasets. Once you have done this, you will be able to easily download or harvest the metadata in bulk and filter out the items that you need (after downloading).
