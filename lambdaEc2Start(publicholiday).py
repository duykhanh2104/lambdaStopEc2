import json
import boto3
from botocore.exceptions import ClientError
from datetime import datetime, timezone

ssm = boto3.client("ssm")

def is_public_holiday():
    today = datetime.now(timezone.utc)
    today_mmdd = today.strftime("%m-%d")
    year = today.strftime("%Y")

    param = ssm.get_parameter(
        Name="public-holidays"
    )
    holidays = json.loads(param["Parameter"]["Value"])

    if today_mmdd in holidays.get("fixed", []):
        return True

    if today_mmdd in holidays.get("yearly", {}).get(year, []):
        return True

    return False


def lambda_handler(event, context):
    # Pubic holiday specific:
    if is_public_holiday():
        print("Skipped EC2 autostart — public holiday")
        return {
            "statusCode": 200,
            "body": json.dumps("Skipped: Public Holiday")
        }

    ec2 = boto3.client('ec2')

    filters = [{'Name': 'tag:AutoStart', 'Values': ['true']}]
    instances = ec2.describe_instances(Filters=filters)

    instance_ids = [
        instance['InstanceId']
        for reservation in instances['Reservations']
        for instance in reservation['Instances']
        if instance['State']['Name'] == 'stopped'
    ]

    if instance_ids:
        try:
            response = ec2.start_instances(InstanceIds=instance_ids)
            print(f'Started instances: {instance_ids}')
        except ClientError as e:
            print(f'ClientError: {e}')
            return {
                'statusCode': 500,
                'body': json.dumps(str(e))
            }
    else:
        print('No stopped instances to start')

    return {
        'statusCode': 200,
        'body': json.dumps('Completed EC2 autostart')
    }
