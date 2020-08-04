
from datetime import datetime
import json
import os
from loguru import logger
import requests

logger.remove()
logger.add(log_filename,
           level="INFO",
           format="{time: YYYY-MM-DD at HH:mm:ss} | {level:<8} | {name: ^15} "
           "|{function: ^15} | {line: >3} | {message}",
           colorize=True,
           backtrace=False,
           mode='w')

topic_arn = os.environ.get('sns_topic_arn')
EVENTS_C = boto3.client('events')
HOOK_URL = os.environ['FAIL_NOTIFICATION_DEST']

def lambda_handler(event, context):
    
    event_time = datetime.strptime(event['time'], "%Y-%m-%dT%H:%M:%SZ") 
    rules = EVENTS_C.list_rules()['Rules']
    fall_back_rules = [r for r in rules if 'fall' in r['Name']]
    spring_forward_rules = [r for r in rules if 'spring' in r['Name']]
     
    if event_time.strftime('%Y-%m-%d') in ['2020-11-01', '2021-11-07', '2022-11-06', '2023-11-05', '2024-11-03']:
        #TODO: change event rule cron expression
        for rule in fall_back_rules: 
            try:
                EVENTS_C.enable_rule(Name=rule['Name'])
            except Exception as e:
                message = "Failed to alter DST change to events trigger!: {e.args}"
                logger.critical(message)
                slack_message = {'text': json.dumps(message, indent=4)}
                res = requests.post(HOOK_URL, json=slack_message)
                logger.info(res)
            else:
                for rule in spring_forward_rules:
                    EVENTS_C.disable_rule(Name=rule['Name'])
    else:
        for rule in spring_forward_rules: 
            try:
                EVENTS_C.enable_rule(Name=rule['Name'])
            except Exception as e:
                message = "Failed to alter DST change to events trigger!: {e.args}"
                logger.critical(message)
                slack_message = {'text': json.dumps(message, indent=4)}
                res = requests.post(HOOK_URL, json=slack_message)
                logger.info(res)
            else:
                for rule in fall_back_rules:
                    EVENTS_C.disable_rule(Name=rule['Name'])