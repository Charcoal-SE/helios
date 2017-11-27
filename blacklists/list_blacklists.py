import boto3
from boto3.dynamodb.conditions import Key, Attr
import logging
import json
import os

log = logging.getLogger()
log.setLevel(logging.DEBUG)

dynamodb = boto3.resource('dynamodb')

def list_blacklist_by_type(event, context):
    """Retrieve a blacklist by type"""
    blacklist_type = str(event['pathParameters']['id'])

    table = dynamodb.Table(os.environ['BLACKLIST_TABLE'])
    result = table.scan(
        FilterExpression=Attr('type').eq(blacklist_type)
    )

    response = {
        'statusCode': 200,
        'body': json.dumps({
            'items': [r['text_pattern'] for r in result['Items']],
            'numItems': len(result['Items'])
        })
    }
    log.debug(response)

    return response
