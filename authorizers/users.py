import boto3
from boto3.dynamodb.conditions import Key, Attr
import logging
import json
import os

log = logging.getLogger()
log.setLevel(logging.DEBUG)

dynamodb = boto3.resource('dynamodb')

def generatePolicy(effect, resource):
    """
        effect: allow/deny
        resource: API end point
    """
    policy = {}
    policy['Version'] = "2012-10-17"    # DO NOT CHANGE THIS
    statement = {}
    statement['Action'] = 'execute-api:Invoke'
    statement['Effect'] = effect
    statement['Resource'] = resource
    policy['Statement'] = [
        statement
    ]
    return policy


def authorize(event, context):
    """ Check if user is authorized to use this route """
    token = event['authorizationToken']
    log.debug("Token: {}".format(token))
    principalId = token
    context = {
        'simpleAuth': True,
    }

    table = dynamodb.Table(os.environ['ACCESSTOKENS_TABLE'])
    dbresponse = table.scan(
        FilterExpression=Attr('token').eq(token) & Attr('enabled').eq(True)
    )
    if len(dbresponse['Items']) == 1:
        policy = generatePolicy('allow', event['methodArn'])
        context['user'] = dbresponse['Items'][0]['name']
    else:
        policy = generatePolicy('deny', event['methodArn'])

    response = {
        'principalId': principalId,
        'policyDocument': policy,
        'context': context
    }
    log.debug(response)
    return response


def authorize_metasmoke(event, context):
    """ Check if user is authorized to use this route and is metasmoke """
    token = event['authorizationToken']
    log.debug("Token: {}".format(token))
    principalId = token
    context = {
        'simpleAuth': True,
    }

    table = dynamodb.Table(os.environ['ACCESSTOKENS_TABLE'])
    dbresponse = table.scan(
        FilterExpression=Attr('token').eq(token) & Attr('enabled').eq(True) & Attr('metasmoke').eq(True)
    )
    if len(dbresponse['Items']) == 1:
        policy = generatePolicy('allow', event['methodArn'])
        context['user'] = dbresponse['Items'][0]['name']
    else:
        policy = generatePolicy('deny', event['methodArn'])

    response = {
        'principalId': principalId,
        'policyDocument': policy,
        'context': context
    }
    log.debug(response)
    return response
