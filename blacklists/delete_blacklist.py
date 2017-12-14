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
    if 'pattern' not in data:
        log.error("Delete Blacklist Validation Failed. Passed data: {}".format(
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

    table = dynamodb.Table(os.environ['BLACKLIST_TABLE'])
    blacklist_type = str(event['pathParameters']['id'])
    response = table.scan(
        FilterExpression=Attr('text_pattern').eq(data['pattern']) & Attr('type').eq(blacklist_type)
    )
    log.info("Deleting: {}".format(response))
    log.info("Delete requested by: {}".format(modified_by))
    uuid = response['Items'][0]['id']
    table.delete_item(
        Key={
            'id': uuid
        }
    )
    error_type = None
    response = {
        'statusCode': 200,
        'body': json.dumps({
            'items': [],
            'numItems': 0,
            'message': "Deleted {}".format(data['pattern']),
            'error_type': error_type
        })
    }
    log.debug("Response: {}".format(response))
    return response
