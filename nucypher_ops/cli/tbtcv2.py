from nucypher_ops.constants import DEFAULT_NAMESPACE, DEFAULT_NETWORK
from nucypher_ops.ops.fleet_ops import CloudDeployers
import os
import click
emitter = click


@click.group('tbtcv2')
def cli():
    """deploy tbtcv2/random beacon nodes"""


@cli.command('stage')
@click.option('--image', help="The docker image to deploy", default='keepnetwork/keep-client:latest')
@click.option('--namespace', help="Namespace for these nodes.  Used to address hosts and data locally and name hosts on cloud platforms.", type=click.STRING, default=DEFAULT_NAMESPACE)
@click.option('--network', help="The network name these hosts will run on.", type=click.STRING, default=DEFAULT_NETWORK)
@click.option('--include-host', 'include_hosts', help="specify hosts to target", multiple=True, type=click.STRING)
@click.option('--env', '-e', 'envvars', help="Environment variables used during execution (ENVVAR=VALUE)", multiple=True, type=click.STRING, default=[])
@click.option('--cli', '-c', 'cliargs', help="additional cli launching arguments", multiple=True, type=click.STRING, default=[])
def stage(image, namespace, network, include_hosts, envvars, cliargs):
    deployer = CloudDeployers.get_deployer('tbtcv2')(emitter,
                                                     docker_image=image,
                                                     namespace=namespace,
                                                     network=network,
                                                     envvars=envvars,
                                                     cliargs=cliargs,
                                                     resource_name='tbtcv2')

    hostnames = deployer.config['instances'].keys()
    if include_hosts:
        hostnames = include_hosts
    for name, hostdata in [(n, d) for n, d in deployer.config['instances'].items() if n in hostnames]:
        emitter.echo(f'\t{name}: {hostdata["publicaddress"]}', color="yellow")
    os.environ['ANSIBLE_HOST_KEY_CHECKING'] = 'False'
    deployer.stage_nodes(hostnames)


@cli.command('run')
@click.option('--image', help="The docker image to deploy", default='keepnetwork/keep-client:latest')
@click.option('--namespace', help="Namespace for these nodes.  Used to address hosts and data locally and name hosts on cloud platforms.", type=click.STRING, default=DEFAULT_NAMESPACE)
@click.option('--network', help="The network name these hosts will run on.", type=click.STRING, default=DEFAULT_NETWORK)
@click.option('--include-host', 'include_hosts', help="specify hosts to target", multiple=True, type=click.STRING)
@click.option('--env', '-e', 'envvars', help="Environment variables used during execution (ENVVAR=VALUE)", multiple=True, type=click.STRING, default=[])
@click.option('--cli', '-c', 'cliargs', help="additional cli launching arguments", multiple=True, type=click.STRING, default=[])
def run(image, namespace, network, include_hosts, envvars, cliargs):
    deployer = CloudDeployers.get_deployer('tbtcv2')(emitter,
                                                     docker_image=image,
                                                     namespace=namespace,
                                                     network=network,
                                                     envvars=envvars,
                                                     cliargs=cliargs,
                                                     resource_name='tbtcv2')

    hostnames = deployer.config['instances'].keys()
    if include_hosts:
        hostnames = include_hosts
    for name, hostdata in [(n, d) for n, d in deployer.config['instances'].items() if n in hostnames]:
        emitter.echo(f'\t{name}: {hostdata["publicaddress"]}', color="yellow")
    os.environ['ANSIBLE_HOST_KEY_CHECKING'] = 'False'
    deployer.run_nodes(hostnames)


@cli.command('operator-address')
@click.option('--image', help="The docker image to deploy", default='keepnetwork/keep-client:latest')
@click.option('--namespace', help="Namespace for these nodes.  Used to address hosts and data locally and name hosts on cloud platforms.", type=click.STRING, default=DEFAULT_NAMESPACE)
@click.option('--network', help="The network name these hosts will run on.", type=click.STRING, default=DEFAULT_NETWORK)
@click.option('--include-host', 'include_hosts', help="specify hosts to target", multiple=True, type=click.STRING)
@click.option('--env', '-e', 'envvars', help="Environment variables used during execution (ENVVAR=VALUE)", multiple=True, type=click.STRING, default=[])
@click.option('--cli', '-c', 'cliargs', help="additional cli launching arguments", multiple=True, type=click.STRING, default=[])
def operator_address(image, namespace, network, include_hosts, envvars, cliargs):
    deployer = CloudDeployers.get_deployer('tbtcv2')(emitter,
                                                     docker_image=image,
                                                     namespace=namespace,
                                                     network=network,
                                                     envvars=envvars,
                                                     cliargs=cliargs,
                                                     resource_name='tbtcv2')

    hostnames = deployer.config['instances'].keys()
    if include_hosts:
        hostnames = include_hosts
    for name, hostdata in [(n, d) for n, d in deployer.config['instances'].items() if n in hostnames]:
        emitter.echo(f'\t{name}: {hostdata["publicaddress"]}', color="yellow")
    os.environ['ANSIBLE_HOST_KEY_CHECKING'] = 'False'
    deployer.get_operator_address(hostnames)



@cli.command('stop')
@click.option('--namespace', help="Namespace for these nodes.  Used to address hosts and data locally and name hosts on cloud platforms.", type=click.STRING, default=DEFAULT_NAMESPACE)
@click.option('--network', help="The network name these hosts will run on.", type=click.STRING, default=DEFAULT_NETWORK)
@click.option('--include-host', 'include_hosts', help="specify hosts to target", multiple=True, type=click.STRING)
def stop(namespace, network, include_hosts):
    deployer = CloudDeployers.get_deployer('tbtcv2')(emitter,
                                                     namespace=namespace,
                                                     network=network,
                                                     resource_name='tbtcv2')
    hostnames = deployer.config['instances'].keys()
    if include_hosts:
        hostnames = include_hosts
    for name, hostdata in [(n, d) for n, d in deployer.config['instances'].items() if n in hostnames]:
        emitter.echo(f'\t{name}: {hostdata["publicaddress"]}', color="yellow")
    os.environ['ANSIBLE_HOST_KEY_CHECKING'] = 'False'
    deployer.stop_nodes(hostnames)


@cli.command('fund')
@click.option('--amount', help="The amount to fund each node.  Default is .003", type=click.FLOAT, default=.003)
@click.option('--namespace',
              help="Namespace for these operations.  Used to address hosts and data locally and name hosts on cloud platforms.",
              type=click.STRING, default=DEFAULT_NAMESPACE)
@click.option('--network', help="The Nucypher network name these hosts will run on.", type=click.STRING,
              default=DEFAULT_NETWORK)
@click.option('--include-host', 'include_hosts', help="Perform this operation on only the named hosts", multiple=True,
              type=click.STRING)
def fund(amount, namespace, network, include_hosts):
    """
    fund remote nodes automatically using a locally managed burner wallet
    """

    deployer = CloudDeployers.get_deployer('tbtcv2')(emitter, namespace=namespace, network=network)

    if deployer.has_wallet:
        if password := os.getenv('NUCYPHER_OPS_LOCAL_ETH_PASSWORD'):
            emitter.echo("found local eth password in environment variable")
        else:
            password = click.prompt('Please enter the wallet password you saved for this account', hide_input=True)
    else:
        emitter.echo("Creating a new wallet to fund your nodes.")
        if password := os.getenv('NUCYPHER_OPS_LOCAL_ETH_PASSWORD'):
            emitter.echo("found local eth password in environment variable")
        else:
            password = click.prompt('please enter a password for this new eth wallet', hide_input=True)
            passwordagain = click.prompt('please enter the same password again', hide_input=True)
            if not password == passwordagain:
                raise AttributeError("passwords dont' match please try again.")

    wallet = deployer.get_or_create_local_wallet(password)
    emitter.echo(f"using local wallet: {wallet.address}")
    balance = deployer.get_wallet_balance(wallet.address, eth=True)
    emitter.echo(f"balance: {deployer.get_wallet_balance(wallet.address)}")

    hostnames = deployer.config['instances'].keys()
    if include_hosts:
        hostnames = include_hosts

    emitter.echo(f"funding {len(hostnames)} nodes with {amount} ETH each.")
    if balance < amount * len(hostnames):
        emitter.echo(
            f"balance on local wallet ({balance} ETH) is not enough to fund {len(hostnames)} with {amount} ETH.  Add more funds to local wallet ({wallet.address})")
        return

    deployer.fund_nodes(wallet, hostnames, amount)


@cli.command('defund')
@click.option('--amount', help="The amount to defund.  Default is the entire balance of the node's wallet.",
              type=click.FLOAT, default=None)
@click.option('--to-address', help="To which ETH address are you sending the proceeds?", required=True)
@click.option('--namespace',
              help="Namespace for these operations.  Used to address hosts and data locally and name hosts on cloud platforms.",
              type=click.STRING, default=DEFAULT_NAMESPACE)
@click.option('--network', help="The Nucypher network name these hosts will run on.", type=click.STRING,
              default=DEFAULT_NETWORK)
@click.option('--include-host', 'include_hosts', help="Peform this operation on only the named hosts", multiple=True,
              type=click.STRING)
def defund(amount, to_address, namespace, network, include_hosts):
    deployer = CloudDeployers.get_deployer('generic')(emitter, namespace=namespace, network=network)

    hostnames = deployer.config['instances'].keys()
    if include_hosts:
        hostnames = include_hosts

    deployer.defund_nodes(hostnames, to=to_address, amount=amount)