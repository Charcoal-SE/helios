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

def create_blacklist_item(event, context):
    data = json.loads(event['body'])
    authorizer = event['requestContext']['authorizer']
    if 'pattern' not in data:
        log.error("New Blacklist Validation Failed. Passed data: {}".format(
            data
        ))
        raise Exception("Couldn't create the blacklist item.")
        return

    # modified_by is the authorized user
    if 'user' not in authorizer:
        log.warn("User not found in authorizer: {}".format(authorizer))
        modified_by = 'Unknown'
    else:
        log.debug("User set: {}".format(authorizer['user']))
        modified_by = authorizer['user']

    blacklist_type = str(event['pathParameters']['id'])
    table = dynamodb.Table(os.environ['BLACKLIST_TABLE'])
    d = datetime.datetime.utcnow()
    unixtime = int(d.timestamp())
    item = {
        'id': "{type}-{pattern}".format(
            type=blacklist_type,
            pattern=data['pattern']
        ),
        'type': blacklist_type,
        'text_pattern': data['pattern'],
        'modified_by': modified_by,
        'created_at': unixtime,
        'modified_at': unixtime,
    }
    error_msg = ""
    error_type = None
    body = item
    try:
        table.put_item(Item=item, Expected={'id': {'Exists': False}})
    except ClientError as e:
        if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
            log.debug("Duplicate entry attempted. {}".format(item))
            error_type = "Duplicate"
            error_msg = "Duplicate entry attempted. {}".format(item)
        else:   # Anything other than a duplicate entry, raise the exception
            raise

    response = {
        'statusCode': 200,
        'body': json.dumps({
            'items': [body],
            'numItems': 1,
            'message': error_msg,
            'error_type': error_type
        })
    }
    log.debug("Response: {}".format(response))
    return response
