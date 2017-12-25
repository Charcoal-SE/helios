Originally posted [here](https://gist.github.com/AWegnerGitHub/f17e4f65c089712f888de429323cd86b)


## Table of Contents

- [What is this?](#what-is-this)
- [Proposal](#proposal)
- [Architecture](#architecture)
- [Simple timings tests](#simple-timings-tests)
- [Response payloads](#response-payloads)
- [Endpoints](#endpoints)
- [Work to do](#work-to-do)


## What is this?

This document describes the proposed architecture for a central SmokeDetector
databsae. As a proof of concept, there are a few areas that are not finished
but these are described in the [Work to do](#work-to-do) section.

This project is tentatively named *Helios*.

## Proposal

Using [Amazon Web Services](https://aws.amazon.com/) and the [Serverless Framework](https://serverless.com/),
we will move the blacklists, watchlist, notifications and potentially more items
(such as permissions) from Git managed assets to Helios. We'll also
eliminate the assets that are only managed locally, such as the notifications list.

This will allow us to maintain a single notification list that is accurate across
all instance of SmokeDetector. The Helios managed blacklist and watchlist will
remove the need for SmokeDetector and metasmoke to perform long running, error prone
Git commands. Additionally, we won't need to wait for continuous integration to
complete when adding to these lists. Instead, it will be able to perform it's
task on code changes, like it should.

## Architecture

Access to the blacklists and notifications will occur via calls to the API
that has been set up. The end point are described in the [Endpoints](#endpoints)
section.

These end points will be utilized to add, delete and list the various data
structures we need. Each instance of SmokeDetector will perform calls to the
`GET` HTTP end points at start up, promotion from standby or on demand to
refresh the local cache.

As SmokeDetector is run and receives commands to add or delete items, the local
cache will be updated and a call will be made to the API to do the same on Helios.
The local cache will be utilized by the running instance at all times, but can
be updated at any time as well.

This means that SmokeDetector will never need to call the API to match patterns
during runtime. New instances will be updated to the latest patterns on
activation.

HTTP `GET` endpoints will be open to all. This will allow users to fire up a
local copy of SmokeDetector and pull the latest version of our centrally managed
lists. Authorized instances of SmokeDetector will require an Authentication
token, as they do for metasmoke currently, to be able to add or delete from Helios.

Open endpoints will be eliminated if abuse occurs to prevent unexpected costs from
being incurred from AWS. However, this is not anticipated.

On the AWS side, we will utilize the Serverless Framework to handle deployment
of Python [Lambda](https://aws.amazon.com/lambda/) functions, while information
will be persisted in [DynamoDB](https://aws.amazon.com/dynamodb/). Deployment
of code upgrades will be accomplished with TravisCI. This behind the scenes
information doesn't directly impact SmokeDetector or metasmoke as all access
to the information will be accomplished via HTTP calls.

## Simple timings tests

Attached to this gist is a python script the will go through a simple workflow
the SmokeDetector would utilize to get/update/delete items from the blacklist.

This isn't an exact replication of what SmokeDetector would use, because it
doesn't handle the local caching of files. It's goal is to provide timing of
how long activities that interact with AWS will take.

This script will perform the following:

 - Request an authentication token
 - Validate the token is active (simulating a user access check)
 - Retrieve each of the blacklists/Watchlists
 - Add five items to a single blacklist
 - Delete the five items from the blacklist

The results of the script are also attached. In it we can see the various
timings it takes to pull the blacklist/watchlist items. You can see the longest
takes a little less than half a second and the shortest takes a tenth of a
second. All together, we pull in approximately 5,500 patterns being watched.

Next we send 5 random patterns to Helios. The average time for the full cycle of
send and receive a response back is about a third of a second, with the shortest
trip taking a quarter of a second and the longer taking over a second.

Finally, we remove the 5 patterns that we added. The response cycle time for this
activity was less than a quarter second for each item being deleted.

This cycle of adding and deleting will be extended, slightly, by adding in a
write operation to a local file. However, even with this additional operation,
the time to add to a list is reduced to seconds. The current cycle of add, commit
to Git, issue a pull request, continuous integration, pull, restart is on the
order of minutes for every item being added or deleted.

## Response payloads

All endpoints will return a JSON object with the following format:

    {
      'items': [array of items],
      'num_items': integer of the number of items in the above array,
      'message': An option message that indicate an error may of occurred
    }

## Endpoints

Endpoints listed here are for the proof of concept only and live in a
development staging area. If this proof of concept is accepted by the community
a production area will be set up and new end points will be shared.

### Create Authentication token

    POST https://fggqk618ri.execute-api.us-east-1.amazonaws.com/dev/auth/create

This proof of concept allows anyone to create an authentication token. This
end point will be restricted and current tokens invalidated if this proposal is
accepted.

Creating a token requires that a payload is passed that contains the `name` of
the user this token will be associated with. A Python example follows:

    requests.post(url, json={'name': 'Andy'})

### Test Authenticaion token

    GET https://fggqk618ri.execute-api.us-east-1.amazonaws.com/dev/test_auth

Test if a passed token is valid. This end point is simply for the proof of
concept and will not be publicly accessible when deployed. The token being
checked must be passed as part of the `Authorization` header.

    r = requests.get(url, headers={'Authorization': 'AVALIDTOKEN'})

This will return `Success!`

    r = requests.get(url, headers={'Authorization': 'ANINVALIDTOKEN'})

This will return `{"Message":"User is not authorized to access this resource with an explicit deny"}`

### Get Blacklists/Watchlists

    GET https://fggqk618ri.execute-api.us-east-1.amazonaws.com/dev/blacklists/{id}

Blacklists and watchlists are accessible to all users. It requires that you
pass a valid list type.

Valid options are: `watch-keyword`, `blacklist-website`, `blacklist-username`,
`blacklist-keyword`. Replace `{id}` in the following URL with one of those
options.

    r = requests.get(url)

This returns a list of all items in the selected blacklist:

    [
        "rhubcom\\.com",
        "erepairpowerpoint\\.com",
        "createspace\\.com",
        "992\\W?993\\W?3179",
        ...
    ]

### Create blacklist/watchlist item

    POST https://fggqk618ri.execute-api.us-east-1.amazonaws.com/dev/blacklists/{id}

Adding to the blacklist requires an `Authorization` token. It also requires that
a payload is passed with the pattern to be added in a `pattern` variable. The
`{id}` value in the URL is one of the valid blacklist options. A Python example
is below.

    params = {'pattern': 'My.Complicated\sPattern'}
    r = requests.post(url, json=params, headers={'Authorization': token})

A successful instead will return a record of the inserted item. The `created_at`
and `modified_at` are unix timestamps.

    {
        'modified_by': 'Andy',
        'modified_at': 1510606300,
        'created_at': 1510606300,
        'id': 'watch-keyword-TOTALLYATEST1.COM',
        'text_pattern': 'TOTALLYATEST1.COM',
        'type': 'watch-keyword'
    }

Duplicates are not allowed. They will not be inserted and will return a notice
of a duplicate attempt and a record of the duplicate.

### Delete blacklist/watchlist item

    DELETE https://fggqk618ri.execute-api.us-east-1.amazonaws.com/dev/blacklists/{id}

Deleting a blacklist item requires an `Authorization` token. It also requires
that a payload is passed with the pattern to be deleted in a `pattern` variable.
The `{id}` value in the URL is one of the valid blacklist options.

A Python example:

    params = {'pattern': 'My.Complicated\sPattern'}
    r = requests.delete(url, json=params, headers={'Authorization': token})

### Get all notifications

    GET https://fggqk618ri.execute-api.us-east-1.amazonaws.com/dev/notifications

Notifications are used to alert a user of a specific post type. Currently, these
are stored locally and not shared. This means that when a new instance starts,
it doesn't have any of the notifications that the previous instance had unless
a user added a notification when this was already run.

    r = requests.get(url)

This returns a response like this. Each item is a notification:

    [{
        "user_id": 66258,
        "server": "chat.stackexchange.com",
        "room_id": 11540,
        "site": "communitybuilding.stackexchange.com"
     },
     ...
    ]

### Creating a notification

    POST https://fggqk618ri.execute-api.us-east-1.amazonaws.com/dev/notifications

Creating a notification requires an `Authorization` token. It also requires a
payload that contains each of the following: `user_id`, `server`, `room_id`, `site`

The combination of these must be unique.

    params = {'user_id': 9854,
            'server': 'test_server',
            'room_id': 888,
            'site': 'example.com'}
    r = requests.post(url, json=params, headers={'Authorization': token})

### Delete a notification

     DELETE https://fggqk618ri.execute-api.us-east-1.amazonaws.com/dev/notifications

Deleting a notification requires an `Authorization` token. It also requires a
payload that contains each of the following: `user_id`, `server`, `room_id`, `site`

    params = {'user_id': 9854,
        'server': 'test_server',
        'room_id': 888,
        'site': 'example.com'}
    r = requests.delete(url, json=params, headers={'Authorization': token})

## Work to do

Since this proposal only includes a proof of concept, their is a more that
would need to be done to completely implement this. Below is a short list
of items, but not a guarantee this will include everything.

### Auth tokens between MS and Helios

SmokeDetector instances isn't the only thing that will require write capability
to the various endpoints described in this document. metasmoke will also require
this. On top of that, a discussion should occur on if current tokens should
be shared so that SmokeDetector instances only need one token to integrate with
both metasmoke and Helios or if it is ok to have two such tokens.

### SmokeDetector Changes

SmokeDetector development will be required to create and update local copies
of the lists. These lists already exist as text files or pickles. The changes
that are required include eliminating the file from git, updating the commands
to sent an HTTP request and write the response to the files. Theoretically,
no further change would be required to these files as the rest of the
application uses them today.

Additionally, writing new records will need to be changed to append to the end
of each file as appropriate and then send an HTTP request to Helios to update
other instances upon activation.

Git pull functionality will need to be changed to eliminate the need for
autopulls after adding to lists. This will now take moments instead of minutes.

Many of these changes will be easier once the [NG Chat Backport](https://github.com/Charcoal-SE/SmokeDetector/pull/1135)
has been completed.

### Request / Response models

*Common responses implemented. Not done via models though*

The proof of concept does not have unified response objects. Before deploying
to product these should be implemented so that end users - SmokeDetector and
metasmoke - can expect a common response layout. This will make development
easier because everything will follow the same layout.

### Move from a dev staging area to a production area

The proof of concept lives in a development area. A production area is needed
as well. This allows us to deploy a test branch of any AWS code prior to
impacting downstream systems.

Doing this means we should also have a configuration option in SmokeDetector to
use development or production. This will allow for easier testing.

### List approval

One advantage that GitHub provides that this system will eliminate is the
ability for more experienced users to approve a pattern. This functionality
should be retained. Options to do this include building the functionality into
metasmoke, building a command to list new patterns in SmokeDetector, adding a
new permission that users need to generate lists, or perhaps something else.

### Automated API Documentation

Documenting the API will be vital for developers of SmokeDetector, metasmoke and
other applications. This documentation can be done automatically, but requires
a bit of initial set up.
