# Famly API Documentation

This document describes the unofficial Famly API endpoints used by this downloader tool. These endpoints were discovered through browser inspection and may change without notice.

## Authentication

All API requests require an access token passed via the `x-famly-accesstoken` header.

```http
x-famly-accesstoken: <access-token>
```

### Obtaining an Access Token

The access token can be obtained by:

1. Logging into `https://app.famly.co` via a browser
2. Extracting the token from the browser's local storage or request headers

This tool uses Playwright to automate browser login and capture the token from outgoing requests.

---

## REST API

Base URL: `https://app.famly.co/api/v2`

### List Tagged Images

Retrieves a paginated list of photos tagged with a specific child.

```http
GET /images/tagged?childId={childId}&from={offset}&to={limit}
```

#### Parameters

| Parameter | Type   | Required | Description                          |
|-----------|--------|----------|--------------------------------------|
| childId   | string | Yes      | UUID of the child                    |
| from      | int    | No       | Offset for pagination (default: 0)   |
| to        | int    | No       | Limit for pagination (default: 100)  |

#### Response

```json
{
  "images": [
    {
      "imageId": "uuid",
      "prefix": "https://img.famly.co/image/{hash}",
      "height": 3024,
      "width": 4032,
      "deviceTimestamp": "2026-01-15T14:30:45.000Z",
      "createdAt": "2026-01-15T14:35:00.000Z"
    }
  ],
  "totalAmount": 150
}
```

#### Image URL Construction

To download an image, append dimensions and path to the prefix:

```
{prefix}/{width}x{height}/path/to/image.jpg?expires=...
```

The `prefix` contains a signed URL with an expiration timestamp.

### List Conversations

Retrieves all conversations for the authenticated user.

```http
GET /conversations
```

#### Response

```json
[
  {
    "conversationId": "uuid",
    "createdAt": "2026-01-15T09:48:22+00:00",
    "lastActivityAt": "2026-01-29T16:51:56+00:00",
    "participants": [
      {
        "title": "User Name",
        "subtitle": "Role Description",
        "image": "https://img.famly.co/image/...",
        "id": "participant-id"
      }
    ],
    "lastMessage": {
      "messageId": "uuid",
      "body": "Message preview...",
      "author": {
        "title": "Author Name",
        "subtitle": "Author Role",
        "image": "https://img.famly.co/image/...",
        "me": false,
        "id": "author-id"
      },
      "images": [],
      "files": []
    },
    "unread": false,
    "archived": false
  }
]
```

### Get Conversation with Messages

Retrieves a single conversation with full message history.

```http
GET /conversations/{conversationId}
```

#### Response

Returns the same structure as list, plus a `messages` array:

```json
{
  "conversationId": "uuid",
  "participants": [...],
  "messages": [
    {
      "messageId": "uuid",
      "conversationId": "uuid",
      "createdAt": "2026-01-15T09:48:22+00:00",
      "body": "Full message text",
      "author": {
        "title": "Author Name",
        "subtitle": "Author Role",
        "image": "https://img.famly.co/image/...",
        "me": false,
        "id": "author-id"
      },
      "images": [
        {
          "prefix": "https://img.famly.co/image/...",
          "key": "archive/2026/01/15/09/images/...",
          "height": 2560,
          "width": 1920,
          "imageId": "uuid"
        }
      ],
      "files": []
    }
  ],
  "cursor": "message-id-for-pagination"
}
```

#### Message Image URLs

Message images use the same URL construction as tagged photos:

```
{prefix}/{key}
```

---

## GraphQL API

Endpoint: `https://app.famly.co/graphql`

All GraphQL requests use `POST` with a JSON body containing `query` and `variables`.

### Get Observations

Fetches observations (activity posts) for one or more children with pagination.

#### Query

```graphql
query GetObservations($childIds: [ChildId!], $first: Int!, $after: ObservationCursor) {
  childDevelopment {
    observations(childIds: $childIds, first: $first, after: $after) {
      results {
        id
        createdBy {
          name { fullName }
          profileImage { url }
        }
        remark {
          id
          date
          body
          richTextBody
        }
        children {
          id
          name
        }
        images {
          id
          width
          height
          url
          secret {
            prefix
            key
            path
            expires
          }
        }
        files {
          id
          name
          url
        }
        videos {
          ... on TranscodedVideo {
            id
            videoUrl
            thumbnailUrl
            duration
            width
            height
          }
        }
        behaviors {
          behaviorId
        }
        likes {
          count
          likedByMe
          likes {
            likedBy {
              name { fullName }
            }
            reaction
          }
        }
        comments {
          count
          results {
            id
            body
            sentBy {
              name { fullName }
              profileImage { url }
            }
            sentAt
          }
        }
      }
      next
    }
  }
}
```

#### Variables

```json
{
  "childIds": ["uuid-of-child"],
  "first": 50,
  "after": null
}
```

| Variable | Type              | Required | Description                              |
|----------|-------------------|----------|------------------------------------------|
| childIds | [ChildId!]        | No       | Array of child UUIDs (null = all)        |
| first    | Int!              | Yes      | Number of results per page (max ~50)     |
| after    | ObservationCursor | No       | Cursor for pagination (from `next`)      |

#### Response

```json
{
  "data": {
    "childDevelopment": {
      "observations": {
        "results": [
          {
            "id": "uuid",
            "createdBy": {
              "name": { "fullName": "Staff Member" },
              "profileImage": { "url": "https://img.famly.co/..." }
            },
            "remark": {
              "id": "uuid",
              "date": "2026-01-29",
              "body": "Plain text content",
              "richTextBody": "<p>HTML content</p>"
            },
            "children": [
              { "id": "uuid", "name": "Child Name" }
            ],
            "images": [
              {
                "id": "uuid",
                "width": 2245,
                "height": 1587,
                "url": "https://img.famly.co/image/.../1920x1080/...",
                "secret": {
                  "prefix": "https://img.famly.co/image/{hash}",
                  "key": "hash",
                  "path": "archive/2026/01/29/14/images/123/uuid.png",
                  "expires": "2026-01-30T19:00:00Z"
                }
              }
            ],
            "files": [
              {
                "id": "uuid",
                "name": "document.pdf",
                "url": "https://famly-de.s3.eu-central-1.amazonaws.com/archive/.../document.pdf?..."
              }
            ],
            "videos": [
              {
                "id": "uuid",
                "videoUrl": "https://famly-video-storage.s3.eu-central-1.amazonaws.com/.../video.mp4?...",
                "thumbnailUrl": "https://famly-video-storage.s3.eu-central-1.amazonaws.com/.../thumbnail.jpg?...",
                "duration": 26,
                "width": 1920,
                "height": 1080
              }
            ],
            "behaviors": [
              { "behaviorId": "uuid" }
            ],
            "likes": {
              "count": 1,
              "likedByMe": false,
              "likes": [
                {
                  "likedBy": { "name": { "fullName": "Parent Name" } },
                  "reaction": "💜"
                }
              ]
            },
            "comments": {
              "count": 1,
              "results": [
                {
                  "id": "uuid",
                  "body": "Comment text",
                  "sentBy": {
                    "name": { "fullName": "Parent Name" },
                    "profileImage": { "url": "https://img.famly.co/..." }
                  },
                  "sentAt": "2026-01-29T14:40:20Z"
                }
              ]
            }
          }
        ],
        "next": "cursor-string-for-next-page"
      }
    }
  }
}
```

#### Pagination

To fetch subsequent pages, pass the `next` value from the response as the `after` variable in the next request. When `next` is `null`, there are no more results.

---

## GraphQL Schema Types

### Observation

| Field     | Type                | Description                           |
|-----------|---------------------|---------------------------------------|
| id        | ObservationId!      | Unique identifier                     |
| createdBy | Person!             | Staff member who created it           |
| remark    | Remark              | Text content (body and richTextBody)  |
| children  | [PublicChild!]!     | Children tagged in the observation    |
| images    | [Image!]!           | Attached images                       |
| files     | [File!]!            | Attached file documents (PDFs, etc.)  |
| videos    | [Video!]!           | Attached videos (union type)          |
| behaviors | [Behavior!]!        | Developmental behaviors/milestones    |
| likes     | Likes!              | Like count and details                |
| comments  | ObservationComments!| Comment count and details             |

### Person

| Field        | Type         | Description              |
|--------------|--------------|--------------------------|
| name         | Name!        | Contains `fullName`      |
| profileImage | ProfileImage | Contains `url` (nullable)|

### Image

| Field  | Type        | Description                              |
|--------|-------------|------------------------------------------|
| id     | ImageId!    | Unique identifier                        |
| width  | Int!        | Original image width                     |
| height | Int!        | Original image height                    |
| url    | String!     | Signed URL (typically 1920x1080)         |
| secret | ImageSecret | Contains prefix, key, path, expires      |

### File

| Field | Type     | Description                                      |
|-------|----------|--------------------------------------------------|
| id    | FileId!  | Unique identifier                                |
| name  | String!  | Original filename (e.g., "report.pdf")           |
| url   | String!  | Signed S3 URL for download (expires in ~2 hours) |

### TranscodedVideo

Videos are a union type. Use fragment `... on TranscodedVideo` to access fields.

| Field        | Type     | Description                              |
|--------------|----------|------------------------------------------|
| id           | VideoId! | Unique identifier                        |
| videoUrl     | String!  | Signed S3 URL for MP4 download           |
| thumbnailUrl | String!  | Signed S3 URL for thumbnail image        |
| duration     | Int!     | Video duration in seconds                |
| width        | Int!     | Video width in pixels                    |
| height       | Int!     | Video height in pixels                   |

### Behavior

| Field      | Type        | Description                              |
|------------|-------------|------------------------------------------|
| behaviorId | BehaviorId! | Reference to developmental behavior/milestone |

### Comment

| Field   | Type           | Description                     |
|---------|----------------|---------------------------------|
| id      | CommentId!     | Unique identifier               |
| body    | String!        | Comment text                    |
| sentBy  | Person!        | Author of the comment           |
| sentAt  | ZonedDateTime! | ISO 8601 timestamp              |

### Like

| Field    | Type    | Description                          |
|----------|---------|--------------------------------------|
| likedBy  | Person! | Person who liked                     |
| reaction | String  | Emoji reaction (e.g., "💜")          |

---

## Image Downloads

### Observation Images

The `url` field in observation images provides a pre-signed URL at a fixed resolution (typically 1920x1080). To download higher resolution versions, you can construct a URL using the `secret` fields:

```
{secret.prefix}/{width}x{height}/{secret.path}?expires={secret.expires}
```

However, the signed URL may not support arbitrary dimensions. The provided `url` is typically the highest available resolution.

### Tagged Photos

For photos from the REST API, construct the download URL:

```
{prefix}/{width}x{height}/archive/...?expires=...
```

Use the original `width` and `height` from the response for full resolution.

---

## Rate Limiting

No explicit rate limits have been documented, but it's recommended to:

- Add delays between requests (e.g., 100-500ms)
- Use reasonable batch sizes (50 items per page)
- Cache the access token and reuse it within its validity period

---

## Notes

- All timestamps are in ISO 8601 format
- UUIDs are used for all identifiers
- Image URLs are signed and expire (typically within 24 hours)
- The GraphQL schema can be introspected using standard `__schema` queries
