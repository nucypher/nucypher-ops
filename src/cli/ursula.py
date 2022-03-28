import os
import click
emitter = click

from src.ops.fleet_ops import CloudDeployers

from src.constants import DEFAULT_NAMESPACE, DEFAULT_NETWORK, PAYMENT_NETWORK_CHOICES


class EnumMenuPromptFromDict(click.Option):

    def __init__(self, *args, **kwargs):
        super(EnumMenuPromptFromDict, self).__init__(*args, **kwargs)
        if 'prompt' not in kwargs:
            raise TypeError(
                "'prompt' keyword required for '{}' option".format(
                    args[0][0]))

        self.choices_dict = self.prompt
        self.prompt_menu = '\n'.join('[{}] {}'.format(i + 1, name)
                                     for i, name in enumerate(self.prompt))
        self.prompt = 'Choose a payment network from,\n{}\n{}'.format(
            self.prompt_menu, self.name)

    def prompt_for_value(self, ctx):
        """Get entered value and then validate"""
        while True:
            value = super(EnumMenuPromptFromDict, self).prompt_for_value(ctx)
            try:
                choice = int(value)
                if choice > 0:
                    return list(self.choices_dict)[choice - 1]
            except (ValueError, IndexError):
                if value in self.choices_dict:
                    return value
            click.echo('Error: {} is not a valid choice'.format(value))

    def full_process_value(self, ctx, value):
        """Convert the entered value to the value from the choices dict"""
        value = super(EnumMenuPromptFromDict, self).full_process_value(
            ctx, value)
        try:
            return self.choices_dict[value]
        except (KeyError, IndexError):
            raise click.UsageError(
                "'{}' is not a valid choice".format(value), ctx)


@click.group('ursula')
def cli():
    """deploy and update ursula nodes"""

@cli.command('deploy')
@click.option('--payment-network', cls=EnumMenuPromptFromDict, prompt=PAYMENT_NETWORK_CHOICES)
@click.option('--payment-provider', help="The remote blockchain provider for the payment network.", required=True)
@click.option('--eth-provider', help="The remote blockchain provider for policies on the remote node.", required=True)
@click.option('--nucypher-image', help="The docker image containing the nucypher code to run on the remote nodes.", default=None)
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


    cliargs = list(cliargs) + [f'payment-network={payment_network}', f'payment-provider={payment_provider}']
    print (cliargs)
    deployer = CloudDeployers.get_deployer('generic')(emitter,
                                                      seed_network=seed_network,
                                                      namespace=namespace,
                                                      network=network,
                                                      envvars=envvars,
                                                      cliargs=cliargs,
                                                      resource_name='nucypher',
                                                      eth_provider=eth_provider,
                                                      docker_image=nucypher_image,
                                                    )

    hostnames = deployer.config['instances'].keys()
    if include_hosts:
        hostnames = include_hosts
    for name, hostdata in [(n, d) for n, d in deployer.config['instances'].items() if n in hostnames]:
        emitter.echo(f'\t{name}: {hostdata["publicaddress"]}', color="yellow")
    os.environ['ANSIBLE_HOST_KEY_CHECKING'] = 'False'
    deployer.deploy_nucypher_on_existing_nodes(hostnames, migrate_nucypher=migrate, init=init)


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

