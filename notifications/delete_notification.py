import boto3
from boto3.dynamodb.conditions import Key, Attr
import logging
import json
import os
import datetime

log = logging.getLogger()
log.setLevel(logging.DEBUG)

dynamodb = boto3.resource('dynamodb')

def delete_notification_item(event, context):
    data = json.loads(event['body'])
    authorizer = event['requestContext']['authorizer']
    if not all(k in data for k in ('server','site','user_id','room_id')):
        log.error("New Notification Validation Failed. Passed data: {}".format(
            data
        ))
        raise Exception("Couldn't delete the notification item.")
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
    delete_key = "{user}-{server}-{room}-{site}".format(
        user=user_id,
        server=server,
        room=room_id,
        site=site
    )

    # We cheat and just logically delete
    d = datetime.datetime.utcnow()
    unixtime = int(d.timestamp())
    table.update_item(
        Key={
            'user_server_room_site': delete_key
        },
        UpdateExpression="SET enabled = :val1, modified_at = :val2",
        ExpressionAttributeValues={
            ':val1': False,
            ':val2': unixtime
        }
    )
    response = {
        'statusCode': 200,
        'body': json.dumps({
            'items': [],
            'numItems': 0,
            'message': "Deleted {}".format(delete_key)
        })
    }
    log.debug("Response: {}".format(response))
    return response
