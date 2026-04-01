import json
import boto3
from botocore.exceptions import ClientError
from datetime import datetime, timezone

ssm_client = boto3.client("ssm")
ec2 = boto3.client("ec2")


def is_public_holiday():
    today = datetime.now(timezone.utc)
    today_mmdd = today.strftime("%m-%d")
    year = today.strftime("%Y")

    param = ssm_client.get_parameter(Name="public-holidays")
    holidays = json.loads(param["Parameter"]["Value"])

    if today_mmdd in holidays.get("fixed", []):
        return True
    if today_mmdd in holidays.get("yearly", {}).get(year, []):
        return True
    return False


def get_platform(instance):
    platform = instance.get("Platform", "")
    return "Windows" if platform.lower() == "windows" else "Linux"


def stop_linux_instances(instance_ids):
    if not instance_ids:
        return
    ec2.stop_instances(InstanceIds=instance_ids)
    print(f"[Linux] Stopped: {instance_ids}")


def graceful_stop_windows(instance_ids):
    if not instance_ids:
        return

    # Kiểm tra SSM agent online
    ssm_ready, not_ready = [], []
    try:
        paginator = ssm_client.get_paginator("describe_instance_information")
        managed = set()
        for page in paginator.paginate(
            Filters=[{"Key": "InstanceIds", "Values": instance_ids}]
        ):
            for info in page["InstanceInformationList"]:
                if info.get("PingStatus") == "Online":
                    managed.add(info["InstanceId"])
        ssm_ready = [i for i in instance_ids if i in managed]
        not_ready = [i for i in instance_ids if i not in managed]
    except ClientError as e:
        print(f"[Windows] Cannot query SSM: {e} — fallback all to force stop")
        not_ready = instance_ids

    # Graceful shutdown qua SSM
    if ssm_ready:
        try:
            resp = ssm_client.send_command(
                InstanceIds=ssm_ready,
                DocumentName="AWS-RunPowerShellScript",
                Parameters={"commands": ["Stop-Computer -Force"]},
                Comment="AutoStop graceful shutdown",
                TimeoutSeconds=60,
            )
            print(f"[Windows] SSM shutdown sent (CommandId={resp['Command']['CommandId']}): {ssm_ready}")
        except ClientError as e:
            print(f"[Windows] SSM failed: {e} — fallback to force stop")
            not_ready.extend(ssm_ready)

    # Fallback: SSM không available → force stop
    if not_ready:
        print(f"[Windows] Force stopping (SSM unavailable): {not_ready}")
        ec2.stop_instances(InstanceIds=not_ready, Force=True)


def lambda_handler(event, context):
    if is_public_holiday():
        print("Skipped EC2 autostop — public holiday")
        return {"statusCode": 200, "body": json.dumps("Skipped: Public Holiday")}

    # Chỉ lấy instances đang running
    filters = [
        {"Name": "tag:AutoStop", "Values": ["true"]},
        {"Name": "instance-state-name", "Values": ["running"]},
    ]
    reservations = ec2.describe_instances(Filters=filters)

    linux_ids, windows_ids = [], []
    for reservation in reservations["Reservations"]:
        for instance in reservation["Instances"]:
            if get_platform(instance) == "Windows":
                windows_ids.append(instance["InstanceId"])
            else:
                linux_ids.append(instance["InstanceId"])

    print(f"Linux to stop: {linux_ids}")
    print(f"Windows to stop: {windows_ids}")

    if not linux_ids and not windows_ids:
        print("No running instances to stop")
        return {"statusCode": 200, "body": json.dumps("No instances to stop")}

    errors = []
    try:
        stop_linux_instances(linux_ids)
    except ClientError as e:
        errors.append(f"Linux: {e}")

    try:
        graceful_stop_windows(windows_ids)
    except ClientError as e:
        errors.append(f"Windows: {e}")

    if errors:
        return {"statusCode": 500, "body": json.dumps({"errors": errors})}

    return {
        "statusCode": 200,
        "body": json.dumps({
            "stopped_linux": linux_ids,
            "shutdown_windows": windows_ids
        })
    }
