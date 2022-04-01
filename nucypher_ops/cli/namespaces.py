from nucypher_ops.constants import DEFAULT_NAMESPACE, DEFAULT_NETWORK, NETWORKS
from nucypher_ops.ops.fleet_ops import CloudDeployers
import os
import click
emitter = click


@click.group('namespaces')
def cli():
    """Organize the machinery"""

@cli.command('list')
@click.option('--all', help="list all namespaces under all networks", default=False, is_flag=True)
@click.option('--network', help="The network whose namespaces you want to see.", type=click.Choice(NETWORKS.keys()), default='mainnet')
def list_namespaces(network, all):
    """lists namespaces"""
    if all:
        networks = NETWORKS.keys()
    else:
        networks = [network]
    deployers = [
        CloudDeployers.get_deployer('generic')(emitter, network=network, pre_config={"namespace": None})
        for network in networks]
    for deployer in deployers:
        namespaces = deployer.get_namespace_names()
        if namespaces:
            emitter.echo(deployer.network)
            for ns in namespaces:
                emitter.echo(f'\t{ns}')
                