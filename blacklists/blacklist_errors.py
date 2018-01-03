import logging
import json


def invalid_path(event, context):
    """
    Defines the error that is thrown if someone hits the naked blacklist/ endpoint
    without an {id}
    """
    response = {
        'statusCode': 404,
        'body': json.dumps({
            'items': [],
            'num_items': 0,
            'message': "Invalid endpoint. An {id} must be supplied.",
            'error_type': "invalid_endpoint"
        })
    }
    return response
