
# Accessing the APIs

- [Levels of access](#levels-of-access)
  - [Personal keys](#personal-keys)
  - [Project keys](#project-keys)
- [Registering for a new API key](#registering-for-a-new-api-key)
  - [Registering for a Personal key](#registering-for-a-personal-key)
  - [Registering for a Project key](#registering-for-a-project-key)
- [Accessing the Europeana APIs using your API key](#accessing-the-europeana-apis-using-your-api-key)
  - [Using an API key (read-only access)](#using-an-api-key-read-only-access)
    - [“X-Api-Key” header (preferred)](#x-api-key-header-preferred)
    - [“wskey” parameter](#wskey-parameter)
- [Accessing the Europeana APIs using tokens](#accessing-the-europeana-apis-using-tokens)
  - [Using an access bearer token](#using-an-access-bearer-token)
- [Auth Service](#auth-service)
  - [Accessing OIDC configuration](#accessing-oidc-configuration)
  - [Requesting a token](#requesting-a-token)
    - [Requesting a token with client credentials only](#requesting-a-token-with-client-credentials-only)
    - [Requesting a token with user credentials](#requesting-a-token-with-user-credentials)
    - [Requesting a token for user-level access (via authorization code flow)](#requesting-a-token-for-user-level-access-via-authorization-code-flow)
    - [Requesting a token using refresh token](#requesting-a-token-using-refresh-token)

# Levels of access

We provide API keys as the means to access the Europeana APIs. This helps us identify who is using the service, gather usage statistics to improve the APIs, and offer better customer support.

Since 28 May 2025, we have updated our API access policy to distinguish between personal and business/project use. The goal is to make it as easy as possible for anyone to try out the APIs with minimal effort—just a push of a button. At the same time, Project API keys were introduced to identify customers who rely on the Europeana APIs to support their services or meet specific operational needs.

> [!WARNING]
> To prevent misuse, we strongly recommend keeping API keys private. Do not share them with third parties or expose them in user interfaces, code, or markup, as API keys are confidential and intended for use only by the individual or client application.

> [!WARNING]
> If abuse of an API key is detected, Europeana Foundation [Fair use policy & guidelines](Fair%20use%20policy%20&%20guidelines.md).

## Personal keys

Anyone can obtain a Personal API key. If you’re simply looking to experiment with the Europeana APIs and explore the content we make available, a Personal API key is a great way to start. Its usage limits are generous enough to support most testing and discovery use cases.

> [!IMPORTANT]
> Each user account is limited to one active key

If you are a teacher and are using—or considering using—the Europeana APIs in your classroom, we recommend that you and each of your students request a Personal API key. This allows everyone to experiment with the APIs independently, without needing to share keys.

> [!WARNING]
> The rate limits for personal keys have been progressively reduced until **April 2026** to give customers with service-level requirements sufficient time to transition to project keys and request them as needed.

## Project keys

Project API keys are intended for customers who rely on the Europeana APIs to deliver a service or support a specific operational need.

Each Project API key should be associated with a specific service on your side. If you operate multiple services that use the Europeana APIs, a separate key can be granted for each one. Unlike Personal API keys, you or your organisation may hold multiple Project API keys. These keys come with significantly higher usage limits, and we can only commit to a defined level of service for customers who hold a Project API key.

Before applying for a Project API key, please consider the following:

- **Start with a Personal API key first.**  
  We strongly recommend testing the Europeana APIs using a Personal API key to evaluate whether they meet your needs. If you need assistance, please don’t hesitate to [contact our customer support team](mailto:api@europeana.eu)—we’re happy to help. Requests from accounts that do not hold, or have not used, a Personal API key will be automatically rejected.
- **Choose the appropriate account and contact email.**  
  All operational and support-related communications will be sent to the email address associated with the account requesting the Project API key. It’s important that this email provides a reliable point of contact. If you are requesting a Project API key on behalf of an organisation, consider whether the key should be linked to a personal institutional email address or to a more general, shared contact email.
- **Keep contact details up to date.**  
  Please reach out to us if the contact email needs to be updated. It is also possible to associate more than one Europeana account with the same Project API key. To do so, first create a new Europeana account associated to the new email address and include this information in your request.

> [!IMPORTANT]
> If you are working on a **research project**, such as a **PhD thesis**, and plan to use the Europeana APIs intensively, we can grant you a Project API key with a limited validity of a few months for that purpose. You can apply for this key using the same form as for regular project keys.

# Registering for a new API key

> [!WARNING]
> Since 28 May 2025, API key registration has been migrated to the account section of the Europeana website. ***You now need a*** [***Europeana account***](https://www.europeana.eu/en/create-and-use-a-europeana-account) ***to access the Europeana APIs***. In return, this update gives you easier access and better management of your API key—all in one place.

Once you’ve registered and logged in to the Europeana website, you can access the API section from the top-right menu, next to your nickname, under “*Manage API keys*”. This will take you to a page where you can register both personal and project keys, and view any keys previously granted to you.

![image-20260204-124331.png](https://europeana.atlassian.net/wiki/download/attachments/2462351393/image-20260204-124331.png?version=1&modificationDate=1770209015413&cacheVersion=1&api=v2)

## Registering for a Personal key

You can find the “*Personal API key*” section at the top of the page. After checking the box **“***I confirm that I have read and accept the API key terms of use***”**, click **“***Request a Personal API key***”.**

> [!IMPORTANT]
> Your key will appear in this section and can immediately be used.

> [!NOTE]
> You can hold only one Personal API key at a time. If you lose or forget your key, you can always return to this section to view it again.

![image-20260204-123217.png](https://europeana.atlassian.net/wiki/download/attachments/2462351393/image-20260204-123217.png?version=1&modificationDate=1770208341804&cacheVersion=1&api=v2)![image-20260206-095434.png](https://europeana.atlassian.net/wiki/download/attachments/2462351393/image-20260206-095434.png?version=1&modificationDate=1770371676057&cacheVersion=1&api=v2)

## Registering for a Project key

You can find the “*Project API keys*“ section below the “*Personal API key*“ section.

![image-20260204-141200.png](https://europeana.atlassian.net/wiki/download/attachments/2462351393/image-20260204-141200.png?version=1&modificationDate=1770214323484&cacheVersion=1&api=v2)
> [!WARNING]
> Please ensure that you meet the requirements outlined in the [Project Key](#project-key) section before requesting a Project API key; otherwise, your request may be rejected.

Complete and submit the form in the “*Project API keys*” section. This request is subject to approval by the Europeana APIs customer support team, and we aim to respond within 1–5 working days. If further details are required, we will contact you in response to your request.

> [!NOTE]
> To increase the chances of approval, please provide as much detail as possible about your project and how you intend to use—or are already using—the Europeana APIs. Including relevant reference documentation or website links will also help support our assessment.

> [!IMPORTANT]
> If your request is approved, you will receive an email confirmation. Your API key will then appear in this section and can immediately be used.

# Accessing the Europeana APIs using your API key

With minor exceptions (namely Thumbnail API, OAI-PMH, SPARQL), when accessing the Europeana APIs, you need to provide your access key (corresponding to your public key) or token (issued by the Auth Service) as part of the request.

## Using an API key (read-only access)

If you only want to access public information then supplying an access key is sufficient, however, if you need to access private information or contribute data to the APIs, then a token is mandatory. The preferred option for supplying an access key is using the “x-api-key” header but other options are also available. If you are accesing the Europeana APIs via a browser we recommend reading [How to set up your browser to access the Europeana APIs](User%20guides/How%20to%20set%20up%20your%20browser%20to%20access%20the%20Europeana%20APIs.md).

### “X-Api-Key” header (preferred)

This option makes use of the standard “X-Api-Key” header to supply the key. This option is the preferred option due to its wide adoption and because it is a safer way to share your key within a request.

**Request**

```java
GET https://api.europeana.eu/...
X-Api-Key: [WSKEY]
```

### “wskey” parameter

> [!WARNING]
> This was the preferred—and only—option until 2023, but it is now deprecated. We will provide a grace period to allow all customers to migrate to using the header-based option. This change was introduced because public keys included in URLs can be easily exposed when links are shared or bookmarked.

This option makes use of the wskey parameter instead of an header.

**Request**

```java
GET https://api.europeana.eu/...?wskey=[WSKEY]
```

# Accessing the Europeana APIs using tokens

Upon registration, you will get your individual private and public authentication key. The private key (or secret) is used for specific methods that require additional authentication while the public key must be used by all other API methods, see [Access using an API key](https://pro.europeana.eu/page/intro#access).

## Using an access bearer token

This option offers access using the access tokens that are issued by the Auth Service as bearer tokens in the Authorization header. It is the preferred and most efficient way to access the Europeana APIs, however, it is for the moment restricted to a selective number of API customers.

**Request**

```java
GET https://api.europeana.eu/...
Authorization: Bearer [JWT_TOKEN]
```

# Auth Service

The Auth Service is Europeana’s authentication and authorization service. If you are already familiared with the user accounts on the Europeana Website, you have already interacted with this service. Besides supporting the registration and management of user accounts, it can also be used as a [OpenID Connect (OIDC) Provider](https://openid.net/developers/how-connect-works/) to grant access to internal and external services such as the Europeana Website but also the Europeana APIs and, more recently, [Transcribathon.eu](http://Transcribathon.eu).

If you own a service and would like to offer access using the Europeana [Single Sign On (SSO)](https://en.wikipedia.org/wiki/Single_sign-on), get in contact with us.

Besides offering SSO access to services using Europeana accounts, Europeana’s Auth Service also manages write-level access (by users and applications) to services that are managed by Europeana such as the Europeana APIs. In particular, APIs such as the Annotation API and User Sets API require write-level access for creating, changing or deleting resources on those APIs or to get priviledged access to access restricted resources such as private Galleries in the case of the User Sets API. Access to these APIs requires the establishment of a partnership agreement to guarantee that use conditions of the service are met.

If you would like to get write-level access to these APIs, [get in contact with us](mailto:api@europeana.eu).

## Accessing OIDC configuration

The OIDC protocol is composed of a number of endpoints that support various functions from issuing an access token, manage user sessions and client registration, to accessing user information. The list of endpoints and available options can be viewed in the following URL.

```java
https://auth.europeana.eu/auth/realms/europeana/.well-known/openid-configuration
```

## Requesting a token

There are several methods to request a token depending on the level of access required or the kind of the application is requesting the token. For all these methods, the token is always requested at the following location:

```java
https://auth.europeana.eu/auth/realms/europeana/protocol/openid-connect/token
```

The following methods can be offered for access:

- client credentials only
- user credentials
- authorization code flow
- refresh token

**Response**

<details>
<summary>The response is a JSON structure composed of the following fields:</summary>

|  **Field**           |  **Datatype**    |  **Description**                                                                                                        |
|:---------------------|:-----------------|:------------------------------------------------------------------------------------------------------------------------|
| `access_token`       | `String`         | The access token. This token is used as the Bearer token in API requests.                                               |
| `expires_in`         | `Integer`        | The lifespan of the access token in seconds.                                                                            |
| `refresh_token`      |                  | The refresh token. This token can be used to obtain a new access token without the need to supply the user credentials. |
| `refresh_expires_in` | `Integer`        | The expiration time in seconds of the refresh token.                                                                    |
| `token_type`         | `String`         | The type of the token. Always with value “`Bearer`“.                                                                    |
| `scope`              | `String`         | The scopes that this token grants access to.                                                                            |
| `session_state`      | `String`         | The id of the session.                                                                                                  |

</details>

### Requesting a token with client credentials only

This method of requesting a token is used when the access can be granted at the level of the client application (identified by your key) and not at the user level. It is typically used for machine to machine applications.

**Request**

```java
POST https://auth.europeana.eu/auth/realms/europeana/protocol/openid-connect/token
Content-Type: application/x-www-form-urlencoded

client_id:[CLIENT_ID]
client_secret:[CLIENT_SECRET]
grant_type:client_credentials
```

### Requesting a token with user credentials

This method of requesting a token is used when the access can be granted at the user level and the client has access to the user credentials.

**Request**

```java
POST https://auth.europeana.eu/auth/realms/europeana/protocol/openid-connect/token
Content-Type: application/x-www-form-urlencoded

client_id:[CLIENT_ID]
client_secret:[CLIENT_SECRET]
username:[USERNAME]
password:[PASSWORD]
grant_type:password
```

### Requesting a token for user-level access (via authorization code flow)

This method of requesting a token is used when the access can be granted at the user level and the client has no (or it is not safe to) access to the user credentials. This method is typically used by web or mobile applications because the application's authentication methods are included in the exchange and must be kept secure.

**Request**

```java
POST https://auth.europeana.eu/auth/realms/europeana/protocol/openid-connect/token
Content-Type: application/x-www-form-urlencoded

grant_type:authorization_code
client_id:[CLIENT_ID]
client_secret:[CLIENT_SECRET]
code:[AUTHORIZATION_CODE]
redirect_uri:[REDIRECT_URI]
```

### Requesting a token using refresh token

This method of requesting a token is used when a refresh token has being issued as part of a previous token request.

**Request**

```java
POST https://auth.europeana.eu/auth/realms/europeana/protocol/openid-connect/token
Content-Type: application/x-www-form-urlencoded

grant_type:refresh_token
client_id:[CLIENT_ID]
client_secret:[CLIENT_SECRET]
refresh_token:[REFRESH_TOKEN]
```
