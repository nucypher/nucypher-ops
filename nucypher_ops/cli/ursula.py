from nucypher_ops.constants import DEFAULT_NAMESPACE, DEFAULT_NETWORK
from nucypher_ops.ops.fleet_ops import CloudDeployers
import os
import click
emitter = click


@click.group('ursula')
def cli():
    """deploy and update ursula nodes"""


@cli.command('deploy')
@click.option('--payment-network', help="Payment network name.  For testnets use 'mumbai'.", type=click.STRING, default='polygon')
@click.option('--payment-provider', help="The remote blockchain provider for the payment network.", default=None)
@click.option('--eth-provider', help="The remote blockchain provider for policies on the remote node.", default=None)
@click.option('--nucypher-image', help="The docker image containing the nucypher code to run on the remote nodes.", default='nucypher/nucypher:latest')
@click.option('--seed-network', help="Do you want the 1st node to be --lonely and act as a seed node for this network", default=None, is_flag=True)
@click.option('--init', help="Clear your nucypher config and start a fresh node with new keys", default=False, is_flag=True)
@click.option('--migrate', help="Migrate nucypher nodes between compatibility breaking versions", default=False, is_flag=True)
@click.option('--namespace', help="Namespace for these operations.  Used to address hosts and data locally and name hosts on cloud platforms.", type=click.STRING, default=DEFAULT_NAMESPACE)
@click.option('--network', help="The Nucypher network name these hosts will run on.", type=click.STRING, default=DEFAULT_NETWORK)
@click.option('--include-host', 'include_hosts', help="specify hosts to update", multiple=True, type=click.STRING)
@click.option('--env', '-e', 'envvars', help="environment variables (ENVVAR=VALUE)", multiple=True, type=click.STRING, default=[])
@click.option('--cli', '-c', 'cliargs', help="cli arguments for 'nucypher run': eg.'--max-gas-price 50'/'--c max-gas-price=50'", multiple=True, type=click.STRING, default=[])
def deploy(payment_network, payment_provider, eth_provider, nucypher_image, seed_network, init, migrate,
           namespace, network, include_hosts, envvars, cliargs):
    """Deploys NuCypher on managed hosts."""

    deployer = CloudDeployers.get_deployer('generic')(emitter,
                                                      seed_network=seed_network,
                                                      namespace=namespace,
                                                      network=network,
                                                      envvars=envvars,
                                                      cliargs=cliargs,
                                                      resource_name='nucypher',
                                                      eth_provider=eth_provider,
                                                      docker_image=nucypher_image,
                                                      payment_provider=payment_provider,
                                                      payment_network=payment_network
                                                      )

    hostnames = deployer.config['instances'].keys()
    if include_hosts:
        hostnames = include_hosts
    for name, hostdata in [(n, d) for n, d in deployer.config['instances'].items() if n in hostnames]:
        emitter.echo(f'\t{name}: {hostdata["publicaddress"]}', color="yellow")
    os.environ['ANSIBLE_HOST_KEY_CHECKING'] = 'False'
    deployer.deploy_nucypher_on_existing_nodes(
        hostnames, migrate_nucypher=migrate, init=init)


@cli.command('update')
@click.option('--nucypher-image', help="The docker image containing the nucypher code to run on the remote nodes.", default=None)
@click.option('--namespace', help="Namespace for these operations.  Used to address hosts and data locally and name hosts on cloud platforms.", type=click.STRING, default=DEFAULT_NAMESPACE)
@click.option('--network', help="The Nucypher network name these hosts will run on.", type=click.STRING, default=DEFAULT_NETWORK)
@click.option('--include-host', 'include_hosts', help="specify hosts to update", multiple=True, type=click.STRING)
@click.option('--env', '-e', 'envvars', help="environment variables (ENVVAR=VALUE)", multiple=True, type=click.STRING, default=[])
@click.option('--cli', '-c', 'cliargs', help="cli arguments for 'nucypher run': eg.'--max-gas-price 50'/'--c max-gas-price=50'", multiple=True, type=click.STRING, default=[])
def deploy(nucypher_image, namespace, network, include_hosts, envvars, cliargs):
    """Update images and change cli/env options on already running hosts"""

    deployer = CloudDeployers.get_deployer('generic')(emitter,
                                                      namespace=namespace,
                                                      network=network,
                                                      envvars=envvars,
                                                      cliargs=cliargs,
                                                      resource_name='nucypher',
                                                      docker_image=nucypher_image
                                                      )

    hostnames = deployer.config['instances'].keys()
    if include_hosts:
        hostnames = include_hosts
    for name, hostdata in [(n, d) for n, d in deployer.config['instances'].items() if n in hostnames]:
        emitter.echo(f'\t{name}: {hostdata["publicaddress"]}', color="yellow")
    os.environ['ANSIBLE_HOST_KEY_CHECKING'] = 'False'
    deployer.update_nucypher_on_existing_nodes(hostnames)


@cli.command('status')
@click.option('--namespace', help="Namespace for these operations.  Used to address hosts and data locally and name hosts on cloud platforms.", type=click.STRING, default=DEFAULT_NAMESPACE)
@click.option('--network', help="The Nucypher network name these hosts will run on.", type=click.STRING, default=DEFAULT_NETWORK)
@click.option('--include-host', 'include_hosts', help="Query status on only the named hosts", multiple=True, type=click.STRING)
def status(namespace, network, include_hosts):
    """Displays ursula status and updates worker data in stakeholder config"""

    deployer = CloudDeployers.get_deployer('generic')(
        emitter, namespace=namespace, network=network)

    hostnames = deployer.config['instances'].keys()
    if include_hosts:
        hostnames = include_hosts

    deployer.get_worker_status(hostnames)
