import os
from pathlib import Path

import click
from ansible.executor.playbook_executor import PlaybookExecutor
from ansible.inventory.manager import InventoryManager
from ansible.parsing.dataloader import DataLoader
from ansible.vars.manager import VariableManager

from nucypher_ops.constants import DEFAULT_NAMESPACE, DEFAULT_NETWORK, PLAYBOOKS
from nucypher_ops.ops.ansible_utils import AnsiblePlayBookResultsCollector
from nucypher_ops.ops.fleet_ops import CloudDeployers

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
def update(nucypher_image, namespace, network, include_hosts, envvars, cliargs):
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
@click.option('--fast', help="Only call blockchain and http methods, skip ssh into each node", default=None, is_flag=True)
@click.option('--namespace', help="Namespace for these operations.  Used to address hosts and data locally and name hosts on cloud platforms.", type=click.STRING, default=DEFAULT_NAMESPACE)
@click.option('--network', help="The Nucypher network name these hosts will run on.", type=click.STRING, default=DEFAULT_NETWORK)
@click.option('--include-host', 'include_hosts', help="Peform this operation on only the named hosts", multiple=True, type=click.STRING)
def status(fast, namespace, network, include_hosts):
    """Displays ursula status and updates worker data in stakeholder config"""

    deployer = CloudDeployers.get_deployer('generic')(
        emitter, namespace=namespace, network=network)

    hostnames = deployer.config['instances'].keys()
    if include_hosts:
        hostnames = include_hosts

    deployer.get_worker_status(hostnames, fast=fast)

@cli.command('fund')
@click.option('--amount', help="The amount to fund each node.  Default is .003", type=click.FLOAT, default=.003)
@click.option('--namespace', help="Namespace for these operations.  Used to address hosts and data locally and name hosts on cloud platforms.", type=click.STRING, default=DEFAULT_NAMESPACE)
@click.option('--network', help="The Nucypher network name these hosts will run on.", type=click.STRING, default=DEFAULT_NETWORK)
@click.option('--include-host', 'include_hosts', help="Peform this operation on only the named hosts", multiple=True, type=click.STRING)
def fund(amount, namespace, network, include_hosts):
    """
    fund remote nodes autmoatically using a locally managed burner wallet
    """
    
    deployer = CloudDeployers.get_deployer('generic')(emitter, namespace=namespace, network=network)

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
        emitter.echo(f"balance on local wallet ({balance} ETH) is not enough to fund {len(hostnames)} with {amount} ETH.  Add more funds to local wallet ({wallet.address})")
        return

    deployer.fund_nodes(wallet, hostnames, amount)
    
@cli.command('defund')
@click.option('--amount', help="The amount to defund.  Default is the entire balance of the node's wallet.", type=click.FLOAT, default=None)
@click.option('--to-address', help="To which ETH address are you sending the proceeds?", required=True)
@click.option('--namespace', help="Namespace for these operations.  Used to address hosts and data locally and name hosts on cloud platforms.", type=click.STRING, default=DEFAULT_NAMESPACE)
@click.option('--network', help="The Nucypher network name these hosts will run on.", type=click.STRING, default=DEFAULT_NETWORK)
@click.option('--include-host', 'include_hosts', help="Peform this operation on only the named hosts", multiple=True, type=click.STRING)
def defund(amount, to_address, namespace, network, include_hosts):

    deployer = CloudDeployers.get_deployer('generic')(emitter, namespace=namespace, network=network)

    hostnames = deployer.config['instances'].keys()
    if include_hosts:
        hostnames = include_hosts

    deployer.defund_nodes(hostnames, to=to_address, amount=amount)


@cli.command('show-backupdir')
@click.option('--verbose', '-v', help="include node nick names", is_flag=True)
@click.option('--namespace', help="Namespace for these operations.  Used to address hosts and data locally and name hosts on cloud platforms.", type=click.STRING, default=DEFAULT_NAMESPACE)
@click.option('--network', help="The Nucypher network name these hosts will run on.", type=click.STRING, default=DEFAULT_NETWORK)
def backupdir(verbose, namespace, network):
    deployer = CloudDeployers.get_deployer('generic')(emitter, namespace=namespace, network=network)
    hostnames = deployer.config['instances'].keys()
    for hostname in hostnames:   
        prefix = f'{hostname}:' if verbose else ''
        emitter.echo(f'{prefix} {deployer.get_backup_path_by_nickname(hostname)}')


@cli.command('restore')
@click.option('--namespace', help="Namespace for these operations.  Used to address hosts and data locally and name hosts on cloud platforms.", type=click.STRING, default=DEFAULT_NAMESPACE)
@click.option('--network', help="The Nucypher network name these hosts will run on.", type=click.STRING, default=DEFAULT_NETWORK)
@click.option('--target-host', 'target_host', help="The nickname of the host where we are putting the restored state. (try `nucypher-ops nodes list` )", multiple=False, type=click.STRING)
@click.option('--source-path', 'source_path', help="The absolute path on disk to the backup data you are restoring", type=click.STRING, required=False)
@click.option('--source-nickname', 'source_nickname', help="The nickname of the node whose data you are moving to the new machine", type=click.STRING, required=False)
def restore(namespace, network, target_host, source_path, source_nickname):
    """Restores a backup of a worker to an existing host"""
    if not source_path and not source_nickname:
        emitter.echo("You must either specify the path to a backup on disk (ie. `/Users/Alice/Library/Application Support/nucypher-ops/configs/), or the name of an existing ursula config (ie. `mainnet-nucypher-1`")

    deployer = CloudDeployers.get_deployer('generic')(emitter, namespace=namespace, network=network)

    deployer.restore_from_backup(target_host, source_path)


@cli.command('backup')
@click.option('--namespace', help="Namespace for these operations.  Used to address hosts and data locally and name hosts on cloud platforms.", type=click.STRING, default=DEFAULT_NAMESPACE)
@click.option('--network', help="The Nucypher network name these hosts are running on.", type=click.STRING, default=DEFAULT_NETWORK)
@click.option('--include-host', help="The nickname of the host to backup", multiple=False, type=click.STRING, required=False)
def backup(namespace, network, include_host):
    """Restores a backup of a worker to an existing host"""
    deployer = CloudDeployers.get_deployer('generic')(emitter, namespace=namespace, network=network)
    if include_host:
        hostnames = [include_host]
    else:
        hostnames = deployer.config['instances'].keys()

    deployer.backup_remote_data(node_names=hostnames)


@cli.command('recover-node-config')
@click.option('--include-host', 'include_hosts', help="specify hosts to recover", multiple=True, required=True, type=click.STRING)
@click.option('--provider', help="The cloud provider host(s) are running on", multiple=False,required=True, type=click.Choice(['aws', 'digitalocean']))
@click.option('--namespace', help="Namespace for these operations", type=click.STRING, default=DEFAULT_NAMESPACE)
@click.option('--login-name', help="The name username of a user with root privileges we can ssh as on the host.", default="root")
@click.option('--key-path', 'ssh_key_path', help="The path to a keypair we will need to ssh into this host (default: ~/.ssh/id_rsa)", default="~/.ssh/id_rsa")
@click.option('--ssh-port', help="The port this host's ssh daemon is listening on (default: 22)", default=22)
def recover_node_config(include_hosts, namespace, provider, login_name, ssh_key_path, ssh_port):
    playbook = Path(PLAYBOOKS).joinpath('gather_ursula_ops_data.yml')

    instance_capture = {
        'InstanceId': [],
        'publicaddress': [],
        'installed': [],
        'host_nickname': [],
        'eth_provider': [],
        'payment_provider': [],
        'payment_network': [],
        'docker_image': [],
        'operator address': [],
        'nickname': [],
        'rest url': [],

        # non-instance dictionary data
        '_ssh-fingerprint': [],
        '_instance-region': [],
        '_domain': [],
        '_keystore-password': [],
        '_operator-password': []
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

    # process data capture
    # 1. remove namespace metadata i.e. keys with underscores
    # 2. add deploy attributes
    namespace_metadata = {}
    metadata_keys = []
    for k in list(instance_capture.keys()):
        if k.startswith("_"):
            metadata_keys.append(k)
            data = instance_capture.pop(k)  # pop off non-instance specific data
            for instance_address, value in data:
                instance = namespace_metadata.get(instance_address, {})
                instance[k] = value
                namespace_metadata[instance_address] = instance

                # add deploy attrs to instance data
                attributes = instance_capture.get("provider_deploy_attrs", list())
                entry = (
                    instance_address,
                    [
                        {'key': 'ansible_ssh_private_key_file', 'value': ssh_key_path},
                        {'key': 'default_user', 'value': login_name},
                        {'key': 'ansible_port', 'value': ssh_port}
                    ]
                )
                attributes.append(entry)
                instance_capture["provider_deploy_attrs"] = attributes

    # verify namespace metadata is the same for all nodes
    ip_addresses = list(namespace_metadata.keys())
    comparator_address = ip_addresses[0]
    comparator_address_data = namespace_metadata[comparator_address]
    for instance_address, instance_data in namespace_metadata.items():
        if instance_address != comparator_address:
            for k in metadata_keys:
                if comparator_address_data[k] != instance_data[k]:
                    raise ValueError(f"Collected {k} data doesn't match "
                                     f"{comparator_address} ({comparator_address_data[k]}) vs"
                                     f"{instance_address} ({instance_data[k]}) ")

    pre_config_metadata = {
        "namespace": namespace,
        "keystorepassword": comparator_address_data['_keystore-password'],
        "ethpassword": comparator_address_data['_operator-password'],
        "keystoremnemonic": None,
        "sshkey": comparator_address_data['_ssh-fingerprint'],
    }

    if provider == 'digitalocean':
        pre_config_metadata['digital-ocean-region'] = comparator_address_data['_instance-region']

    instances_dict = {}
    for ip_address in ip_addresses:
        instances_dict[ip_address] = {
            "publicaddress": ip_address,
        }
    pre_config_metadata["instances"] = instances_dict

    deployer = CloudDeployers.get_deployer(provider)(
        emitter,
        recovery_mode=True,
        namespace=namespace,
        network=comparator_address_data['_domain'],
        pre_config=pre_config_metadata
    )

    deployer.recover_instance_config(instance_data=instance_capture)
