try:
    import boto3
except ModuleNotFoundError:
    pass


def compare_and_remove_common_namespace_data(instance_capture: dict, include_hosts) -> dict:
    # 1. remove namespace metadata; keys that start with '_'
    namespace_metadata = {}
    metadata_keys = []
    for k in list(instance_capture.keys()):
        if k.startswith("_"):
            metadata_keys.append(k)
            data = instance_capture.pop(k)  # pop off non-instance specific data
            for instance_address, value in data:
                instance = namespace_metadata.get(instance_address, {})
                if not instance:
                    namespace_metadata[instance_address] = instance
                instance[k] = value

    # verify namespace metadata is the same for all nodes
    comparator_address = include_hosts[0]
    comparator_address_data = namespace_metadata[comparator_address]
    for instance_address, instance_data in namespace_metadata.items():
        if instance_address != comparator_address:
            for k in metadata_keys:
                if comparator_address_data[k] != instance_data[k]:
                    raise ValueError(f"Collected {k} data doesn't match "
                                     f"{comparator_address} ({comparator_address_data[k]}) vs"
                                     f"{instance_address} ({instance_data[k]}) ")

    return comparator_address_data


def add_deploy_attributes(instance_capture, include_hosts, ssh_key_path, login_name, ssh_port):
    for host in include_hosts:
        # add deploy attrs to instance data
        deploy_attrs = instance_capture.get("provider_deploy_attrs", list())
        if not deploy_attrs:
            instance_capture["provider_deploy_attrs"] = deploy_attrs
        entry = (
            host,
            [
                {'key': 'ansible_ssh_private_key_file', 'value': ssh_key_path},
                {'key': 'default_user', 'value': login_name},
                {'key': 'ansible_port', 'value': ssh_port}
            ]
        )
        deploy_attrs.append(entry)


def get_aws_instance_info(aws_profile, aws_region, ip_address) -> dict:
    # aws ec2 describe-instances --filters Name=ip-address,Values=<ip>
    aws_session = boto3.Session(profile_name=aws_profile, region_name=aws_region)
    ec2Client = aws_session.client('ec2')
    instance_info = ec2Client.describe_instances(
        Filters=[
            {'Values': [ip_address], 'Name': 'ip-address'},
        ]
    )['Reservations']['Instances'][0]

    return instance_info


def get_aws_internet_gateway_info(aws_profile, aws_region, vpc_id) -> dict:
    # aws ec2 describe-internet-gateways --filters Name=attachment.vpc-id,Values=<VPCID>
    aws_session = boto3.Session(profile_name=aws_profile, region_name=aws_region)
    ec2Client = aws_session.client('ec2')
    internet_gateway_info = ec2Client.describe_internet_gateways(
        Filters=[
            {'Values': [vpc_id], 'Name': 'attachment.vpc-id'},
        ]
    )['InternetGateways'][0]
    return internet_gateway_info


def get_aws_route_table_info(aws_profile, aws_region, subnet_id) -> dict:
    # aws ec2 describe-route-tables --filters Name=association.subnet-id,Values=<SUBNET_ID>
    aws_session = boto3.Session(profile_name=aws_profile, region_name=aws_region)
    ec2Client = aws_session.client('ec2')
    route_table_info = ec2Client.describe_route_tables(
        Filters=[
            {'Values': [subnet_id], 'Name': 'association.subnet-id'},
        ]
    )['RouteTables'][0]

    return route_table_info
