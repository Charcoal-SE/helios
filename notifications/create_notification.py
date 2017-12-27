import boto3
from boto3.dynamodb.conditions import Key, Attr
from botocore.exceptions import ClientError
import logging
import json
import os
import datetime

log = logging.getLogger()
log.setLevel(logging.DEBUG)

dynamodb = boto3.resource('dynamodb')

def create_notification_item(event, context):
    data = json.loads(event['body'])
    authorizer = event['requestContext']['authorizer']
    if not all(k in data for k in ('server','site','user_id','room_id')):
        log.error("New Notification Validation Failed. Passed data: {}".format(
            data
        ))
        raise Exception("Couldn't create the notification item.")
        return

    # modified_by is the authorized user
    if 'user' not in authorizer:
        log.warn("User not found in authorizer: {}".format(authorizer))
        modified_by = 'Unknown'
    else:
        log.debug("User set: {}".format(authorizer['user']))
        modified_by = authorizer['user']

    table = dynamodb.Table(os.environ['NOTIFICATIONS_TABLE'])
    user_id = data['user_id']
    site = data['site']
    server = data['server']
    room_id = data['room_id']
    d = datetime.datetime.utcnow()
    unixtime = int(d.timestamp())
    item = {
        'user_server_room_site': "{user}-{server}-{room}-{site}".format(
            user=user_id,
            server=server,
            room=room_id,
            site=site
        ),
        'user_id': user_id,
        'site': site,
        'room_id': room_id,
        'server': server,
        'modified_by': modified_by,
        'created_at': unixtime,
        'modified_at': unixtime,
        'enabled': True
    }
    error_type = None
    error_msg = ""
    body = item
    try:
        table.put_item(Item=item, Expected={'user_server_room_site': {'Exists': False}})
    except ClientError as e:
        if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
            log.debug("Duplicate entry attempted. {}".format(item))
            error_type = "Duplicate"
            error_msg = error_msg = "Duplicate entry attempted. {}".format(item)
        else:   # Anything other than a duplicate entry, raise the exception
            raise

    response = {
        'statusCode': 200,
        'body': json.dumps({
            'items': [body],
            'num_items': 1
        })
    }
    log.debug("Response: {}".format(response))
    return response
