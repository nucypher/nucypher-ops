from pathlib import Path

from ansible.executor.playbook_executor import PlaybookExecutor
from ansible.inventory.manager import InventoryManager
from ansible.parsing.dataloader import DataLoader
from ansible.vars.manager import VariableManager

from nucypher_ops.cli.recover_utils import compare_and_remove_common_namespace_data, \
    add_deploy_attributes
from nucypher_ops.constants import DEFAULT_NAMESPACE, DEFAULT_NETWORK, PLAYBOOKS
from nucypher_ops.ops.ansible_utils import AnsiblePlayBookResultsCollector
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
    """Set up and configure tbtcv2 node but don't run it"""
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
    """Start tbtcv2 node."""
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
    """Determine operator address for specified hosts"""
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
    """Stop tbtcv2 node(s)"""
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
    Fund remote nodes automatically using a locally managed burner wallet
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
    """Transfer remaining ETH balance from operator address to another address"""
    deployer = CloudDeployers.get_deployer('generic')(emitter, namespace=namespace, network=network)

    hostnames = deployer.config['instances'].keys()
    if include_hosts:
        hostnames = include_hosts

    deployer.defund_nodes(hostnames, to=to_address, amount=amount)


@cli.command('recover-node-config')
@click.option('--include-host', 'include_hosts', help="specify hosts to recover", multiple=True, required=True, type=click.STRING)
@click.option('--provider', help="The cloud provider host(s) are running on", multiple=False, required=True, type=click.Choice(['digitalocean']))  # TODO: only DO allowed for now
@click.option('--namespace', help="Namespace for these operations", type=click.STRING, default=DEFAULT_NAMESPACE)
@click.option('--network', help="Network that the node is running on", type=click.STRING, default=DEFAULT_NETWORK)
@click.option('--login-name', help="The name username of a user with root privileges we can ssh as on the host.", default="root")
@click.option('--key-path', 'ssh_key_path', help="The path to a keypair we will need to ssh into this host (default: ~/.ssh/id_rsa)", default="~/.ssh/id_rsa")
@click.option('--ssh-port', help="The port this host's ssh daemon is listening on (default: 22)", default=22)
def recover_node_config(include_hosts, provider, namespace, network, login_name, ssh_key_path, ssh_port):
    """Regenerate previously lost/deleted node config(s)"""
    playbook = Path(PLAYBOOKS).joinpath('recover_tbtcv2_ops_data.yml')

    instance_capture = {
        'InstanceId': [],
        'publicaddress': [],
        'host_nickname': [],
        'eth_provider': [],
        'docker_image': [],
        'operator address': [],
        'nickname': [],
        'rest url': [],

        # non-instance dictionary data
        '_ssh-fingerprint': [],
        '_instance-region': [],
        '_operator-password': [],
    }

    inventory_host_list = '{},'.format(",".join(include_hosts))
    loader = DataLoader()
    inventory = InventoryManager(
        loader=loader, sources=inventory_host_list)
    hosts = inventory.get_hosts()
    for host in hosts:
        host.set_variable('ansible_ssh_private_key_file', ssh_key_path)
        host.set_variable('default_user', login_name)
        host.set_variable('ansible_port', ssh_port)
        host.set_variable('ansible_connection', 'ssh')
    callback = AnsiblePlayBookResultsCollector(
        sock=emitter,
        return_results=instance_capture
    )
    variable_manager = VariableManager(loader=loader, inventory=inventory)

    executor = PlaybookExecutor(
        playbooks=[playbook],
        inventory=inventory,
        variable_manager=variable_manager,
        loader=loader,
        passwords=dict(),
    )

    executor._tqm._stdout_callback = callback
    executor.run()

    #
    # Process data capture
    # 1. remove namespace metadata; keys that start with '_'
    comparator_address_data = compare_and_remove_common_namespace_data(instance_capture, include_hosts)

    # 2. add deploy attributes
    add_deploy_attributes(instance_capture, include_hosts, ssh_key_path, login_name, ssh_port)

    pre_config_metadata = {
        "namespace": f'{namespace}-{network}',
        "keystorepassword": "N/A",
        "ethpassword": comparator_address_data['_operator-password'],
        "keystoremnemonic": "N/A (recovery mode)",
        "sshkey": comparator_address_data['_ssh-fingerprint'],
    }

    # 3. Provider information
    if provider == 'digitalocean':
        pre_config_metadata['digital-ocean-region'] = comparator_address_data['_instance-region']

        # DO access token
        digital_access_token = emitter.prompt(
            f"Please enter your Digital Ocean Access Token which can be created here: https://cloud.digitalocean.com/account/api/tokens.  It looks like this: b34abcDEF17ABCDEFAbcDEf09fd72a28425ABCDEF8b198e9623ABCDEFc11591")
        if not digital_access_token:
            raise AttributeError(
                "Could not continue without Access Token")
        pre_config_metadata['digital-ocean-access-token'] = digital_access_token

    # set up pre-config instances
    node_names = []
    instances_dict = {}
    for ip_address, host_nickname in instance_capture['host_nickname']:
        instances_dict[host_nickname] = {
            "publicaddress": ip_address,
            "installed": ["tbtcv2"],
            "provider": provider,
        }

        node_names.append(host_nickname)  # store node names

    pre_config_metadata["instances"] = instances_dict

    deployer = CloudDeployers.get_deployer("tbtcv2")(
        emitter,
        recovery_mode=True,
        namespace=namespace,
        network=network,
        pre_config=pre_config_metadata,
        resource_name='tbtcv2'
    )

    # regenerate instance configuration file
    deployer.recover_instance_config(instance_data=instance_capture)

    # regenerate inventory file
    deployer.update_generate_inventory(node_names)
