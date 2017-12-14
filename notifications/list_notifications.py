import boto3
from boto3.dynamodb.conditions import Key, Attr
import logging
import json
import os
import decimal

log = logging.getLogger()
log.setLevel(logging.DEBUG)

dynamodb = boto3.resource('dynamodb')

# This is a workaround for: http://bugs.python.org/issue16535
def decimal_default(obj):
    if isinstance(obj, decimal.Decimal):
        return float(obj)
    raise TypeError


def list_all_notifications(event, context):
    """Retrieve all notifications"""
    table = dynamodb.Table(os.environ['NOTIFICATIONS_TABLE'])
    result = table.scan(
        FilterExpression=Attr('enabled').eq(True)
    )
    error_type = None
    error_msg = ""
    items = [
        {
            'user_id': int(r['user_id']),
            'server': r['server'],
            'room_id': int(r['room_id']),
            'site': r['site']
        } for r in result['Items']]
    response = {
        'statusCode': 200,
        'body': json.dumps({
            'items': items,
            'numItems': len(items),
            'message': error_msg,
            'error_type': error_type
        }, default=decimal_default)
    }
    log.debug(response)
    return response
