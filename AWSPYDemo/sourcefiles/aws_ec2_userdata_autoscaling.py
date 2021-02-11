"""
author: Pythoholic
Lets create a launch template with EC2 userdata
Lets create a autoscaling group and attach the launch template to it
"""

import boto3
import base64
from botocore.exceptions import ClientError

with open("userdata_base64.txt", "r") as fp:
    USERDATA_B64_STR = fp.read()

class CreateInstanceEC2(object):
    def __init__(self, ec2_client):
        self.ec2_client=ec2_client

    def grep_vpc_subnet_id(self):
        vpc_id = ""
        response = self.ec2_client.describe_vpcs()
        for vpc in response["Vpcs"]:
            if vpc["Tags"][0]["Value"].__contains__("Default"):
                vpc_id = vpc["VpcId"]
                break

        response = self.ec2_client.describe_subnets(Filters=[{"Name":"vpc-id", "Values": [vpc_id]}])
        subnet_id = response["Subnets"][0]["SubnetId"]
        az = response["Subnets"][0]["AvailabilityZone"]
        return vpc_id, subnet_id, az

    def create_ec2_security_group(self):
        sg_name = "awspy_security_group"
        print("Creating the Security Group {} : STARTED ".format(sg_name))
        try:
            vpc_id, subnet_id, az = self.grep_vpc_subnet_id()
            response = self.ec2_client.create_security_group(
                GroupName=sg_name,
                Description="This SG is created using Python",
                VpcId=vpc_id
            )
            sg_id = response["GroupId"]
            sg_config = self.ec2_client.authorize_security_group_ingress(
                GroupId=sg_id,
                IpPermissions=[
                    {
                        'IpProtocol': 'tcp',
                        'FromPort': 22,
                        'ToPort':22,
                        'IpRanges':[{'CidrIp':'0.0.0.0/0'}]
                    },
                    {
                        'IpProtocol': 'tcp',
                        'FromPort': 80,
                        'ToPort': 80,
                        'IpRanges': [{'CidrIp': '0.0.0.0/0'}]
                    }
                ]
            )
            print("Creating the Security Group {} : COMPLETED - Security Group ID: {} ".format(sg_name, sg_id))
            return sg_id, sg_name
        except Exception as e:
            if str(e).__contains__("already exists"):
                response = self.ec2_client.describe_security_groups(GroupNames=[sg_name])
                sg_id = response["SecurityGroups"][0]["GroupId"]
                print("Security Group {} already exists with Security Group ID: {} ".format(sg_name, sg_id))
                return sg_id, sg_name

    def create_ec2_launch_template(self):
        print("Creating the Launch Templates : STARTED ")
        template_name = 'awspy_launch_template'
        try:
            sg_id, sg_name = self.create_ec2_security_group()
            response = self.ec2_client.create_launch_template(
                LaunchTemplateName=template_name,
                LaunchTemplateData={
                    'ImageId': 'ami-08e0ca9924195beba',
                    'InstanceType' : "t2.micro",
                    'KeyName' : "ec2-key",
                    'UserData': USERDATA_B64_STR,
                    'SecurityGroupIds': [sg_id]
                }
            )
            template_id = response['LaunchTemplate']['LaunchTemplateId']
            print("Creating the Launch Templates : COMPLETED : TemplateID:{}, TemplateName:{}".format(template_id, template_name ))
            return template_id, template_name
        except Exception as e:
            response = self.ec2_client.describe_launch_templates(
                LaunchTemplateNames=[
                    template_name,
                ]
            )
            template_id = response['LaunchTemplates'][0]['LaunchTemplateId']
            return template_id, template_name

    def create_ec2_auto_scaling_group(self):
        print ("---- Started the creation of Auto Scaling Group using Launch Templates ----")
        launch_template_id, launch_template_name = self.create_ec2_launch_template()
        vpc_id, subnet_id, az = self.grep_vpc_subnet_id()
        client = boto3.client('autoscaling')
        response = client.create_auto_scaling_group(
            AutoScalingGroupName='awspy_autoscaling_group',
            LaunchTemplate={
                'LaunchTemplateId': launch_template_id,
            },
            MinSize=1,
            MaxSize=3,
            DesiredCapacity=2,
            AvailabilityZones=[
                az,
            ]
        )

        if str(response["ResponseMetadata"]["HTTPStatusCode"]) == "200":
            print("---- Creation of Auto Scaling Group using Launch Templates : COMPLETED ----")
        else:
            print("---- Creation of Auto Scaling Group using Launch Templates : FAILED ----")
        return True


# Lets start the execution from here
try:
    ec2_client = boto3.client('ec2')
    call_obj = CreateInstanceEC2(ec2_client)
    call_obj.create_ec2_auto_scaling_group()
except ClientError as e:
    print(e)