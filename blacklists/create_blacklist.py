import boto3
from boto3.dynamodb.conditions import Key, Attr
from botocore.exceptions import ClientError
import logging
import json
import os
import uuid
import datetime

log = logging.getLogger()
log.setLevel(logging.DEBUG)

dynamodb = boto3.resource('dynamodb')

def create_item_dict(data, event):
    """
    Creates the item dictionary that is used to add an entry and return

    data: The json.loads(event['body'])
    event: The event data
    """
    item_id, blacklist_type, text_pattern, user_add, user_profile, errors = extract_item_parameters(data, event)
    authorizer = extract_authorizer(event)
    d = datetime.datetime.utcnow()
    unixtime = int(d.timestamp())
    if errors:
        if len(errors) > 1:
            error_type = "multiple"
        else:
            error_type = errors[0]
        log.info("Errors: {}".format(errors))
        error_msg = ' | '.join(str(e) for e in zip(*errors)[1])
    else:
        error_type = None
        error_msg = None
    item = {
        'id': item_id,
        'type': blacklist_type,
        'text_pattern': text_pattern,
        'added_by_token': user_add,
        'created_at': unixtime,
        'modified_at': unixtime,
        'error_type': error_type,
        'message': error_msg,
        'smokey_token': authorizer,
    }
    return item


def extract_authorizer(event):
    """
    Get the authorizer associated with this request

    event: The event context
    """
    authorizer = event['requestContext']['authorizer']
    if 'user' not in authorizer:
        log.warn("'user' not found in authorizer: {}".format(authorizer))
        smokey_token = 'Unknown'
    else:
        log.debug("smokey_token set: {}".format(authorizer['user']))
        smokey_token = authorizer['user']

    return smokey_token


def extract_item_parameters(data, event):
    """
    Extract the parameters we'll use for adding an item

    data: Data array passed to the lambda
    event: Event array passed to the lambda
    """
    errors = []
    blacklist_type = str(event['pathParameters']['id'])
    if 'pattern' not in data:
        log.error("Pattern not in data. Passed data: {}".format(
            data
        ))
        pattern = "None passed"
        errors.append(("bad_data", "No pattern passed. Unable to create blacklist item"))
    else:
        pattern = data['pattern']
    if 'request_user' not in data:
        log.error("Request user not in data Passed data: {}".format(
            data
        ))
        request_user = "None passed"
        errors.append(("no_request_user", "No request user passed. Unable to create blacklist item"))
    else:
        request_user = data['request_user']
    if 'chat_link' not in data:
        log.error("chat link not in data. Passed data: {}".format(
            data
        ))
        user_profile = "None passed"
        errors.append(("no_chat_link", "No request user profile link passed. Unable to create blacklist item"))
    else:
        user_profile = data['chat_link']

    item_id = "{type}-{pattern}".format(type=blacklist_type, pattern=data['pattern'])
    return item_id, blacklist_type, pattern, request_user, user_profile, errors


def create_blacklist_item(event, context):
    data = json.loads(event['body'])
    authorizer = event['requestContext']['authorizer']
    error_msg = ""
    error_type = ""
    log.info("Data received: {}".format(data))

    item = create_item_dict(data, event)

    try:
        table.put_item(Item=item, Expected={'id': {'Exists': False}})
    except ClientError as e:
        if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
            log.debug("Duplicate entry attempted. {}".format(item))
            error_type = "Duplicate"
            error_msg = "Duplicate entry attempted. {}".format(item)
        else:   # Anything other than a duplicate entry, raise the exception
            log.error("Unknown error at blacklist entry. {}".format(item))
            log.error("Exception: {}".format(e.response['Error']['Code']))
            error_type = "Unknown"
            error_msg = "Unknown error. {}".format(item)

    error_msg = " | ".join((item['error_msg'], error_msg))
    if item['error_type'] and error_type:
        error_type = "multiple"
    else:
        error_type = item['error_type'] if item['error_type'] else error_type

    item.pop('error_type')
    item.pop('error_msg')

    response = {
        'statusCode': 200,
        'body': json.dumps({
            'items': [item],
            'numItems': 1,
            'message': error_msg,
            'error_type': error_type
        })
    }
    log.debug("Response: {}".format(response))
    return response
