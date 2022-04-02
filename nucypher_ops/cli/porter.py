from nucypher_ops.constants import DEFAULT_NAMESPACE, DEFAULT_NETWORK
from nucypher_ops.ops.fleet_ops import CloudDeployers
import os
import click
emitter = click


@click.group('porter')
def cli():
    """deploy and update geth nodes"""


@cli.command('deploy')
@click.option('--image', help="The geth image to deploy", default='nucypher/porter:latest')
@click.option('--namespace', help="Namespace for these operations.  Used to address hosts and data locally and name hosts on cloud platforms.", type=click.STRING, default=DEFAULT_NAMESPACE)
@click.option('--network', help="The Nucypher network name these hosts will run on.", type=click.STRING, default=DEFAULT_NETWORK)
@click.option('--include-host', 'include_hosts', help="specify hosts to update", multiple=True, type=click.STRING)
@click.option('--env', '-e', 'envvars', help="additional environment variables (ENVVAR=VALUE)", multiple=True, type=click.STRING, default=[])
@click.option('--cli', '-c', 'cliargs', help="additional cli arguments for geth", multiple=True, type=click.STRING, default=[])
def deploy(image, namespace, network, include_hosts, envvars, cliargs):
    """Deploys NuCypher on managed hosts."""

    deployer = CloudDeployers.get_deployer('generic')(emitter,
                                                      docker_image=image,
                                                      namespace=namespace,
                                                      network=network,
                                                      envvars=envvars,
                                                      cliargs=cliargs,
                                                      resource_name='ethereum'
                                                      )

    hostnames = deployer.config['instances'].keys()
    if include_hosts:
        hostnames = include_hosts
    for name, hostdata in [(n, d) for n, d in deployer.config['instances'].items() if n in hostnames]:
        emitter.echo(f'\t{name}: {hostdata["publicaddress"]}', color="yellow")
    os.environ['ANSIBLE_HOST_KEY_CHECKING'] = 'False'
    deployer.deploy_image_on_existing_nodes(hostnames, 'porter')
