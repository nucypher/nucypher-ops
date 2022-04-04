from nucypher_ops.constants import DEFAULT_NAMESPACE, DEFAULT_NETWORK, NETWORKS
from nucypher_ops.ops.fleet_ops import CloudDeployers
import os
import click
import json
emitter = click


@click.group('nodes')
def cli():
    """Manage the machinery"""


@cli.command('create')
@click.option('--region', help="provider specific region name (like us-east-1 or SFO3", default=None)
@click.option('--instance-type', help="provider specific instance size like `s-1vcpu-2gb` or `t3.small`", default=None)
@click.option('--cloudprovider', help="aws or digitalocean", default='aws')
@click.option('--count', help="Create this many nodes.", type=click.INT, default=1)
@click.option('--namespace', help="Namespace for these operations.  Used to address hosts and data locally and name hosts on cloud platforms.", type=click.STRING, default=DEFAULT_NAMESPACE)
@click.option('--nickname', help="A nickname by which to remember the created hosts", type=click.STRING, required=False)
@click.option('--network', help="The Nucypher network name these hosts will run on.", type=click.STRING, default=DEFAULT_NETWORK)
def create(region, instance_type, cloudprovider, count, nickname, namespace, network):
    """Creates the required number of workers to be staked later under a namespace"""

    if cloudprovider == 'aws':
        try:
            import boto3
        except ImportError:
            raise click.BadOptionUsage(
                'cloudprovider', "You must have boto3 installed to create aws nodes. run `pip install boto3` or use `--cloudprovider digitalocean`")

    deployer = CloudDeployers.get_deployer(cloudprovider)(emitter,
                                                          namespace=namespace, network=network, instance_type=instance_type, action='create', region=region)

    names = []
    i = 1
    while len(names) < count:
        name = (nickname or f'{namespace}-{network}') + f'-{i}'
        if name not in deployer.config.get('instances', {}):
            names.append(name)
        i += 1
    deployer.create_nodes(names)
    emitter.echo(
        f"done.  created {count} nodes.  list existing nodes with `nucypher-ops nodes list`")


@cli.command('add')
@click.option('--host-address', help="The IP address or Hostname of the host you are adding.", required=True)
@click.option('--login-name', help="The name username of a user with root privileges we can ssh as on the host.", required=True)
@click.option('--key-path', help="The path to a keypair we will need to ssh into this host (default: ~/.ssh/id_rsa)", default="~/.ssh/id_rsa")
@click.option('--ssh-port', help="The port this host's ssh daemon is listening on (default: 22)", default=22)
@click.option('--nickname', help="A nickname to remember this host by", type=click.STRING, required=True)
@click.option('--namespace', help="Namespace for these operations.  Used to address hosts and data locally and name hosts on cloud platforms.", type=click.STRING, default='nucypher')
@click.option('--network', help="The Nucypher network name these hosts will run on. (default mainnet)", type=click.STRING, default=DEFAULT_NETWORK)
def add(host_address, login_name, key_path, ssh_port, nickname, namespace, network):
    """Adds an existing node to the local config for future management."""

    name = nickname

    deployer = CloudDeployers.get_deployer('generic')(
        emitter, namespace=namespace, network=network, action='add')
    deployer.create_nodes([name], host_address, login_name, key_path, ssh_port)


@cli.command('copy')
@click.option('--nickname', help="A nickname to remember this host by", type=click.STRING, required=True)
@click.option('--namespace', help="Namespace for these operations.  Used to address hosts and data locally and name hosts on cloud platforms.", type=click.STRING, default='nucypher')
@click.option('--network', help="The Nucypher network name these hosts will run on. (default mainnet)", type=click.STRING, default=DEFAULT_NETWORK)
@click.option('--from', 'from_path', help="The 'path' of a node in /network/namespace/name format ie. '/mainnet/aws-us-east-nodes/aws-1'", type=click.STRING, required=True)
def copy(from_path, from_name, to_network, namespace, nickname):
    """Adds an existing node to the local config for future management."""

    try:
        network, namespace, host_name = from_path.split('/')
    except Exception as e:
        emitter.echo("please supply --from in the format of /network/namespace/node_nickname")
        return


    source = CloudDeployers.get_deployer('generic')(emitter, namespace=namespace, network=network)
    host_data = source.get_host_by_name(host_name)
    print(host_data)
    

    # deployer = CloudDeployers.get_deployer('generic')(
    #     emitter, None, None, namespace=namespace, network=network, action='add')
    # deployer.create_nodes([name], host_address, login_name, key_path, ssh_port)


@cli.command('list')
@click.option('--json', 'as_json', help="list node data", default=False, is_flag=True)
@click.option('--all', help="list all nodes under all networks and namespaces", default=False, is_flag=True)
@click.option('--network', help="The network whose hosts you want to see.", type=click.STRING, default=DEFAULT_NETWORK)
@click.option('--namespace', help="The network whose hosts you want to see.", type=click.STRING, default=DEFAULT_NAMESPACE)
def list(network, namespace, all, as_json):
    """Prints local config info about known hosts"""

    if all:
        networks = NETWORKS.keys()
        namespace = None
    else:
        networks = [network]

    deployers = [
        CloudDeployers.get_deployer('generic')(emitter, network=network, pre_config={"namespace": namespace}, read_only=True)
        for network in networks]
    
    for deployer in deployers:
        if not as_json:
            emitter.echo(f'{network}')
        for ns, hosts in deployer.get_namespace_data(namespace=namespace):
            if not as_json:
                emitter.echo(f'\t{ns}')
            for name, data in hosts:
                if not as_json:
                    emitter.echo(f'\t\t{name}')
                if as_json:
                    print (json.dumps(data, indent=4))


@cli.command('destroy')
@click.option('--cloudprovider', help="aws or digitalocean")
@click.option('--namespace', help="Namespace for these operations.  Used to address hosts and data locally and name hosts on cloud platforms.", type=click.STRING, default=DEFAULT_NAMESPACE)
@click.option('--network', help="The Nucypher network name these hosts will run on.", type=click.STRING, default=DEFAULT_NETWORK)
@click.option('--include-host', 'include_hosts', help="destroy only the named hosts", multiple=True, type=click.STRING)
def destroy(cloudprovider, namespace, network, include_hosts):
    """Cleans up all previously created resources for the given network for the same cloud provider"""

    if not cloudprovider:
        hosts = CloudDeployers.get_deployer('generic')(
            emitter, network=network, namespace=namespace).get_all_hosts()
        # check if there are hosts in this namespace
        if len(set(host['provider'] for address, host in hosts)) == 1:
            cloudprovider = hosts[0][1]['provider']
        else:
            emitter.echo("Found hosts from multiple cloudproviders.")
            emitter.echo(
                "We can only destroy hosts from one cloudprovider at a time.")
            emitter.echo(
                "Please specify which provider's hosts you'd like to destroy using --cloudprovider (digitalocean or aws)")
            return
    deployer = CloudDeployers.get_deployer(cloudprovider)(
        emitter, network=network, namespace=namespace)

    hostnames = [name for name, data in deployer.get_provider_hosts()]
    if include_hosts:
        hostnames = include_hosts
    deployer.destroy_resources(hostnames)


@cli.command('remove')
@click.option('--namespace', help="Namespace for these operations.  Used to address hosts and data locally and name hosts on cloud platforms.", type=click.STRING, default=DEFAULT_NAMESPACE)
@click.option('--network', help="The Nucypher network name these hosts will run on.", type=click.STRING, default=DEFAULT_NETWORK)
@click.option('--include-host', 'include_hosts', help="destroy only the named hosts", multiple=True, type=click.STRING)
def remove(namespace, network, include_hosts):
    """Removes managed resources for the given network/namespace"""

    deployer = CloudDeployers.get_deployer('generic')(
        emitter, network=network, namespace=namespace)

    hostnames = [name for name, data in deployer.get_all_hosts()]
    if include_hosts:
        hostnames = include_hosts
    emitter.echo(
        f"\nAbout to remove information about the following: {', '.join(hostnames)}, including all local data about these nodes.")
    emitter.echo("\ntype 'y' to continue")
    if click.getchar(echo=False) == 'y':
        deployer.remove_resources(hostnames)
