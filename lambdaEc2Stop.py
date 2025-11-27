import json
import boto3
from botocore.exceptions import ClientError

def lambda_handler(event, context):
    ec2 = boto3.client('ec2')
    
    filters = [{'Name': 'tag:AutoStop', 'Values': ['true']}]
    instances = ec2.describe_instances(Filters=filters)
    instance_ids = [instance['InstanceId'] for reservation in instances['Reservations'] for instance in reservation['Instances']]
    
    if instance_ids:
        try:
            response = ec2.stop_instances(InstanceIds=instance_ids, DryRun=False)
            print(f'Stopped instances: {response}')
        except ClientError as e:
            print(f'ClientError: {e}')
            return {
                'statusCode': 500,
                'body': json.dumps(f'ClientError: {e}')
            }
    else:
        print('No instances to stop')

    return {
        'statusCode': 200,
        'body': json.dumps('Completed modifying EC2 status as requested')
    }
