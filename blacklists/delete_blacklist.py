import boto3
from boto3.dynamodb.conditions import Key, Attr
import logging
import json
import os
import uuid
import datetime

log = logging.getLogger()
log.setLevel(logging.DEBUG)

dynamodb = boto3.resource('dynamodb')

def delete_blacklist_item(event, context):
    data = json.loads(event['body'])
    authorizer = event['requestContext']['authorizer']
    item_id, blacklist_type, text_pattern, user_add, user_profile, errors = extract_item_parameters(data, event)
    authorizer = extract_authorizer(event)

    table = dynamodb.Table(os.environ['BLACKLIST_TABLE'])
    response = table.scan(
        FilterExpression=Attr('text_pattern').eq(text_pattern) & Attr('type').eq(blacklist_type)
    )
    log.info("Deleting: {}".format(response))
    log.info("Delete requested by: {} ({})".format(user_add, user_profile))
    uuid = response['Items'][0]['id']
    table.delete_item(
        Key={
            'id': uuid
        }
    )
    log.info("Blacklist Delete Successful. Type: {} Blacklist Pattern: {}".format(blacklist_type, text_pattern))
    error_type = None
    response = {
        'statusCode': 200,
        'body': json.dumps({
            'items': [],
            'numItems': 0,
            'message': "Deleted {}".format(data['pattern']),
            'error_type': error_type,
        })
    }
    log.debug("Response: {}".format(response))
    return response


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
    Extract the parameters we'll use for delete an item

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
