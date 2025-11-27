### 1. Create IAM Role for lambda
1. IAM Console → Roles → Create role
2. AWS service → Lambda
3. Attach các policies:
- AWSLambdaBasicExecutionRole (để ghi logs)
- Create inline policy cho EC2:
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ec2:DescribeInstances",
        "ec2:StopInstances",
        "ec2:StartInstances"
      ],
      "Resource": "*"
    }
  ]
}
4. Naming role: LambdaEC2AutoStopStartRole

### 2. Create Lambda function to stop EC2
1. Lambda Console → Create function
2. Select Author from scratch
3. Config:
Function name: EC2-AutoStop
Runtime: Python 3.11
Role: Select role step 1
4. Copy code to Lambda function

### 3: Create Lambda function to START EC2
Create new function: EC2-AutoStart

### 4: Tag EC2 Instance
EC2 console > Instances > Manage tags > add tag: 
- Key: AutoStop
- Value: true

### 5: Create eventbridge rule
Rule 1: Autostop 6PM
EventBridge Console > Rules > Create Rule
Config:
- Name: Ec2-AutoStop-Rule
- Rule type: Schedule
- Schedule pattern: Cron expression
- Cron: 0 18 * * ? *

### 6: Test:
Lambda > Deploy function > Test: create new events, json body: {} , set timeout: 30s > run test > check status EC2
