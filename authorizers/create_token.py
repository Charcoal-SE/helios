import boto3
from boto3.dynamodb.conditions import Key, Attr
from botocore.exceptions import ClientError
import logging
import json
import os
import string
import random
import datetime

log = logging.getLogger()
log.setLevel(logging.DEBUG)

dynamodb = boto3.resource('dynamodb')

def generate_token(size=40, chars=string.ascii_letters + string.digits):
    """
    size = Size of string to return
    chars = Character set to choose token characters from
    """
    return ''.join(random.SystemRandom().choice(chars) for _ in range(size))


def create_token(event, context):
    data = json.loads(event['body'])

    if 'name' not in data:
        log.error("New Token Validation Failed. Passed data: {}".format(
            data
        ))
        raise Exception("Couldn't create the token item.")
        return

    table = dynamodb.Table(os.environ['ACCESSTOKENS_TABLE'])
    user = data['name']
    d = datetime.datetime.utcnow()
    unixtime = int(d.timestamp())

    item={
        'token': generate_token(),
        'name': user,
        'created_at': unixtime,
        'modified_by': user,
        'modified_at': unixtime,
        'enabled': True
    }

    table.put_item(Item=item)

    response = {
        'statusCode': 200,
        'body': json.dumps({
            'items': [item],
            'num_items': len([item])
        })
    }
    log.debug("Token: {}".format(response))
    return response
