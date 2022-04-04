"""
 This file is part of nucypher.

 nucypher is free software: you can redistribute it and/or modify
 it under the terms of the GNU Affero General Public License as published by
 the Free Software Foundation, either version 3 of the License, or
 (at your option) any later version.

 nucypher is distributed in the hope that it will be useful,
 but WITHOUT ANY WARRANTY; without even the implied warranty of
 MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 GNU Affero General Public License for more details.

 You should have received a copy of the GNU Affero General Public License
 along with nucypher.  If not, see <https://www.gnu.org/licenses/>.
"""

import copy
import json

import pkgutil

import maya
import os
import requests
import time
from ansible.executor.playbook_executor import PlaybookExecutor
from ansible.inventory.manager import InventoryManager
from ansible.parsing.dataloader import DataLoader

from ansible.vars.manager import VariableManager
from base64 import b64encode
from mako.template import Template
from pathlib import Path

from nucypher_ops.ops.ansible_utils import AnsiblePlayBookResultsCollector

from nucypher_ops.constants import (
    CHAIN_NAMES, NETWORKS, DEFAULT_CONFIG_ROOT, PLAYBOOKS, TEMPLATES,
    NUCYPHER_ENVVAR_KEYSTORE_PASSWORD,
    NUCYPHER_ENVVAR_OPERATOR_ETH_PASSWORD, PAYMENT_NETWORKS, PAYMENT_NETWORK_CHOICES
)

from nucypher_ops.ops import keygen

try:
    import boto3
except ImportError:
    pass

NODE_CONFIG_STORAGE_KEY = 'configs'


class BaseCloudNodeConfigurator:

    NAMESSPACE_CREATE_ACTIONS = ['add', 'create']
    application = 'ursula'

    def __init__(self,  # TODO: Add type annotations
                 emitter,
                 seed_network=None,
                 pre_config=False,
                 network=None,
                 namespace=None,
                 action=None,
                 envvars=None,
                 cliargs=None,
                 resource_name=None,
                 eth_provider=None,
                 docker_image=None,
                 **kwargs
                 ):

        self.emitter = emitter
        self.network = network
        self.namespace = namespace
        self.action = action
        self.resource_name = resource_name
        self.kwargs = kwargs

        self.envvars = envvars or []
        if self.envvars:
            if not all([(len(v.split('=')) == 2) for v in self.envvars]):
                raise ValueError(
                    "Improperly specified environment variables: --env variables must be specified in pairs as `<name>=<value>`")
            self.envvars = [v.split('=') for v in (self.envvars)]

        cliargs = cliargs or []
        self.cliargs = []
        if cliargs:
            for arg in cliargs:
                if '=' in arg:
                    self.cliargs.append(arg.split('='))
                else:
                    # allow for --flags like '--prometheus'
                    self.cliargs.append((arg, ''))

        self.config_filename = f'{self.network}-{self.namespace}.json'

        self.created_new_nodes = False

        # the keys in this dict are used as search patterns by the anisble result collector and it will return
        # these values for each node if it happens upon them in some output
        self.output_capture = {'operator address': [], 'rest url': [
        ], 'nucypher version': [], 'nickname': []}

        if pre_config:
            self.config = pre_config
            self.namespace_network = self.config.get('namespace')
            return

        # where we save our state data so we can remember the resources we created for future use
        self.config_path = self.network_config_path / \
            self.namespace / self.config_filename
        self.config_dir = self.config_path.parent

        if self.config_path.exists():
            self.config = json.load(open(self.config_path))
            self.namespace_network = self.config['namespace']
        elif kwargs.get('read_only'):
            self.config = {
                'instances': {},
            }
            return
        else:
            self.namespace_network = f'{self.network}-{self.namespace}-{maya.now().date.isoformat()}'
            self.config = {
                "namespace": self.namespace_network,
                "keystorepassword": b64encode(os.urandom(64)).decode('utf-8'),
                "ethpassword": b64encode(os.urandom(64)).decode('utf-8'),
                'instances': {},
                'eth_provider': eth_provider,
                'docker_image': docker_image
            }
            self._write_config()

        if not self.config.get('keystoremnemonic'):
            wallet = keygen.generate()
            self.config['keystoremnemonic'] = wallet.mnemonic()
            self.alert_new_mnemonic(wallet)
            self._write_config()
        # configure provider specific attributes
        self._configure_provider_params()

        # if certain config options have been specified with this invocation,
        # save these to update host specific variables before deployment
        # to allow for individual host config differentiation
        self.host_level_overrides = {
            'eth_provider': eth_provider,
            'payment_provider': self.kwargs.get('payment_provider'),
            'docker_image': docker_image,
            'payment_network':  self.kwargs.get('payment_network'),
        }

        self.host_level_override_prompts = {
            'eth_provider': {"prompt": "--eth-provider: please provide the url of a hosted ethereum node (infura/geth) which your nodes can access", "choices": None},
            'payment_provider': {"prompt": "--payment-provider: please provide the url of a hosted level-two node (infura/bor) which your nodes can access", "choices": None},
            'payment_network':  {"prompt": f'--payment-network:  choose a payment network from: {PAYMENT_NETWORK_CHOICES}', "choices": PAYMENT_NETWORKS},
        }

        self.config['seed_network'] = seed_network if seed_network is not None else self.config.get(
            'seed_network')
        if not self.config['seed_network']:
            self.config.pop('seed_node', None)

        if self.kwargs.get('payment_network'):
            self.config['payment_network'] = self.kwargs.get('payment_network')

        # add instance key as host_nickname for use in inventory
        if self.config.get('instances'):
            for k, v in self.config['instances'].items():
                self.config['instances'][k]['host_nickname'] = k

        self._write_config()

    def _write_config(self):

        config_dir = self.config_path.parent
        config_dir.mkdir(parents=True, exist_ok=True)

        with open(self.config_path, 'w') as outfile:
            json.dump(self.config, outfile, indent=4)

    @property
    def instance_count(self):
        return len(self.config['instances'].keys())

    @property
    def network_config_path(self):
        return Path(DEFAULT_CONFIG_ROOT).joinpath(NODE_CONFIG_STORAGE_KEY, self.network)

    @property
    def _provider_deploy_attrs(self):
        return []

    def _configure_provider_params(self):
        pass

    def _do_setup_for_instance_creation(self):
        pass

    def _format_runtime_options(self, node_options):
        node_options.update({'network': self.network})
        return ' '.join([f'--{name} {value}' for name, value in node_options.items()])

    @property
    def chain_id(self):
        return NETWORKS[self.network]['policy']

    @property
    def chain_name(self):
        try:
            return CHAIN_NAMES[self.chain_id].lower()
        except KeyError:
            self.emitter.echo(
                f"could not identify public blockchain for {self.network}", color="red")

    @property
    def inventory_path(self):
        return str(Path(DEFAULT_CONFIG_ROOT).joinpath(NODE_CONFIG_STORAGE_KEY, f'{self.namespace_network}.ansible_inventory.yml'))

    def update_generate_inventory(self, node_names, generate_keymaterial=False, **kwargs):

        # filter out the nodes we will not be dealing with
        nodes = {key: value for key,
                 value in self.config['instances'].items() if key in node_names}
        if not nodes:
            raise KeyError(
                f"No hosts matched the supplied names: {node_names}.  Try `nucypher cloudworkers list-hosts` or create new hosts with `nucypher-ops nodes create`")

        defaults = {
            'envvars':
                [
                    (NUCYPHER_ENVVAR_KEYSTORE_PASSWORD,
                     self.config['keystorepassword']),
                    (NUCYPHER_ENVVAR_OPERATOR_ETH_PASSWORD,
                     self.config['ethpassword']),
                ],
            'cliargs': [
                    ]
        }

        if generate_keymaterial or kwargs.get('migrate_nucypher') or kwargs.get('init'):
            wallet = keygen.restore(self.config['keystoremnemonic'])
            keypairs = list(keygen.derive(
                wallet, quantity=self.instance_count))

        for datatype in ['envvars', 'cliargs']:

            data_key = f'runtime_{datatype}'

            input_data = [(k, v) for k, v in getattr(self, datatype)]

            # populate the specified environment variables as well as the
            # defaults that are only used in the inventory
            for key, node in nodes.items():
                node_vars = nodes[key].get(data_key, {})
                for k, v in input_data:
                    node_vars.update({k: v})
                nodes[key][data_key] = node_vars

                # we want to update the config with the specified values
                # so they will persist in future invocations
                self.config['instances'][key] = copy.deepcopy(nodes[key])

            # we don't want to save the default_envvars to the config file
            # but we do want them to be specified to the inventory template
            # but overridden on a per node basis if previously specified
            for key, node in nodes.items():
                for k, v in defaults[datatype]:
                    if not k in nodes[key][data_key]:
                        nodes[key][data_key][k] = v
                if generate_keymaterial or kwargs.get('migrate_nucypher') or kwargs.get('init'):
                    node['keymaterial'] = keypairs[node['index']][1]

        inventory_content = self._inventory_template.render(
            deployer=self,
            nodes=nodes.values(),
            extra=kwargs,
        )

        with open(self.inventory_path, 'w') as outfile:
            outfile.write(inventory_content)
            self.emitter.echo(f"wrote new inventory to: {self.inventory_path}")

        # now that everything rendered correctly, save how we got there.
        self._write_config()

        return self.inventory_path

    def create_nodes(self, node_names):
        self.give_helpful_hints(node_names)
        count = len(node_names)
        self.emitter.echo(
            f"ensuring cloud nodes exist for the following {count} node names:")
        for s in node_names:
            self.emitter.echo(f'\t{s}')
        time.sleep(3)
        self._do_setup_for_instance_creation()

        if not self.config.get('instances'):
            self.config['instances'] = {}

        for node_name in node_names:
            existing_node = self.config['instances'].get(node_name)
            if not existing_node:
                self.emitter.echo(
                    f'creating new node for {node_name}', color='yellow')
                time.sleep(3)
                node_data = self.create_new_node(node_name)
                node_data['host_nickname'] = node_name
                node_data['provider'] = self.provider_name
                node_data['index'] = len(self.config['instances'].keys())
                self.config['instances'][node_name] = node_data
                if self.config['seed_network'] and not self.config.get('seed_node'):
                    self.config['seed_node'] = node_data['publicaddress']
                self._write_config()
                self.created_new_nodes = True

        return self.config

    @property
    def _inventory_template(self):
        template_path = Path(TEMPLATES).joinpath('ursula_inventory.mako')
        return Template(filename=str(template_path))

    def configure_host_level_overrides(self, node_names):
        # first update any specified input in our node config

        input_values = {}
        for k, input_specified_value in self.host_level_overrides.items():
            for node_name in node_names:
                # if an instance already has a specified value, we only override
                # it if that value was input for this command invocation
                if input_specified_value:
                    self.config['instances'][node_name][k] = input_specified_value

                # if this node has not already been configured with this info
                elif not self.config['instances'][node_name].get(k):
                    # do we have it in our global config?
                    if self.config.get(k):
                        self.config['instances'][node_name][k] = self.config.get(
                            k)

                    # have we already prompted the user for this info?
                    elif input_values.get(k):
                        self.config['instances'][node_name][k] = input_values[k]

                    # if not, prompt the user.
                    else:
                        ux = self.host_level_override_prompts[k]
                        if ux.get('choices'):
                            input_values[k] = self.emitter.prompt(
                                ux['prompt'], type=self.emitter.Choice(ux['choices']), show_choices=False)
                        else:
                            input_values[k] = self.emitter.prompt(ux['prompt'])
                        self.config['instances'][node_name][k] = input_values[k]

                self._write_config()
        # print(json.dumps(self.config['instances'], indent=4))

    def deploy_nucypher_on_existing_nodes(self, node_names, migrate_nucypher=False, init=False, **kwargs):

        if migrate_nucypher or init:
            keep_going = self.emitter.prompt(
                "Proceeding with this operation will delete information from your nodes including wallets and keys.  Are you sure? (type 'yes')") == 'yes'
            if init:
                keep_going = self.emitter.prompt(
                    "Proceeding with this operation will delete your node's eth wallet so make sure it does not posses any significant funds... Are you sure? (type 'yes')") == 'yes'
            if not keep_going:
                return
            if migrate_nucypher:
                self.migrate(**kwargs)

        playbook = Path(PLAYBOOKS).joinpath('setup_remote_workers.yml')

        self.configure_host_level_overrides(node_names)

        if self.created_new_nodes:
            self.emitter.echo(
                "--- Giving newly created nodes some time to get ready ----")
            with self.emitter.progressbar(range(0, 30), show_eta=False, show_percent=False) as bar:
                for tick in bar:
                    time.sleep(1)
        self.emitter.echo(
            'Running ansible deployment for all running nodes.', color='green')

        if self.config.get('seed_network') is True and not self.config.get('seed_node'):
            self.config['seed_node'] = list(self.config['instances'].values())[
                0]['publicaddress']
            self._write_config()

        self.update_generate_inventory(
            node_names, generate_keymaterial=True, migrate_nucypher=migrate_nucypher, init=init)

        loader = DataLoader()
        inventory = InventoryManager(
            loader=loader, sources=self.inventory_path)
        callback = AnsiblePlayBookResultsCollector(
            sock=self.emitter, return_results=self.output_capture)
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

        for k in node_names:
            installed = self.config['instances'][k].get('installed', [])
            installed = list(set(installed + [self.application]))
            self.config['instances'][k]['installed'] = installed
        self._write_config()

        self.update_captured_instance_data(self.output_capture)
        self.give_helpful_hints(node_names, backup=True, playbook=playbook)

    def update_nucypher_on_existing_nodes(self, node_names):

        playbook = Path(PLAYBOOKS).joinpath('update_remote_workers.yml')

        self.configure_host_level_overrides(node_names)

        if self.config.get('seed_network') is True and not self.config.get('seed_node'):
            self.config['seed_node'] = list(self.config['instances'].values())[
                0]['publicaddress']
            self._write_config()

        self.update_generate_inventory(node_names)

        loader = DataLoader()
        inventory = InventoryManager(
            loader=loader, sources=self.inventory_path)
        callback = AnsiblePlayBookResultsCollector(
            sock=self.emitter, return_results=self.output_capture)
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

        self.update_captured_instance_data(self.output_capture)
        self.give_helpful_hints(node_names, backup=True, playbook=playbook)

    def get_worker_status(self, node_names):

        playbook = Path(PLAYBOOKS).joinpath('get_workers_status.yml')

        self.update_generate_inventory(node_names)

        loader = DataLoader()
        inventory = InventoryManager(
            loader=loader, sources=self.inventory_path)
        callback = AnsiblePlayBookResultsCollector(sock=self.emitter, return_results=self.output_capture, filter_output=[
                                                   "Print Ursula Status Data", "Print Last Log Line"])
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
        self.update_captured_instance_data(self.output_capture)

        self.give_helpful_hints(node_names, playbook=playbook)

    def print_worker_logs(self, node_names):

        playbook = Path(PLAYBOOKS).joinpath('get_worker_logs.yml')

        self.update_generate_inventory(node_names)

        loader = DataLoader()
        inventory = InventoryManager(
            loader=loader, sources=self.inventory_path)
        callback = AnsiblePlayBookResultsCollector(
            sock=self.emitter, return_results=self.output_capture)
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
        self.update_captured_instance_data(self.output_capture)

        self.give_helpful_hints(node_names, playbook=playbook)

    def backup_remote_data(self, node_names):

        playbook = Path(PLAYBOOKS).joinpath('backup_remote_workers.yml')
        self.update_generate_inventory(node_names)

        loader = DataLoader()
        inventory = InventoryManager(
            loader=loader, sources=self.inventory_path)
        callback = AnsiblePlayBookResultsCollector(
            sock=self.emitter, return_results=self.output_capture)
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

        self.give_helpful_hints(node_names, backup=True, playbook=playbook)

    def stop_worker_process(self, node_names):

        playbook = Path(PLAYBOOKS).joinpath('stop_remote_workers.yml')
        self.update_generate_inventory(node_names)

        loader = DataLoader()
        inventory = InventoryManager(
            loader=loader, sources=self.inventory_path)
        callback = AnsiblePlayBookResultsCollector(
            sock=self.emitter, return_results=self.output_capture)
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

        self.give_helpful_hints(node_names, playbook=playbook)

    def restore_from_backup(self, target_host, source_path):

        playbook = Path(PLAYBOOKS).joinpath('restore_ursula_from_backup.yml')

        self.update_generate_inventory([target_host], restore_path=source_path)

        loader = DataLoader()
        inventory = InventoryManager(
            loader=loader, sources=self.inventory_path)
        callback = AnsiblePlayBookResultsCollector(
            sock=self.emitter, return_results=self.output_capture)
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
        self.give_helpful_hints([target_host], backup=True, playbook=playbook)

    def get_provider_hosts(self):
        return [
            (node_name, host_data) for node_name, host_data in self.get_all_hosts()
            if host_data['provider'] == self.provider_name
        ]

    def get_namespace_names(self, namespace=None):
        if os.path.exists(self.network_config_path):
            for ns in self.network_config_path.iterdir():
                if namespace:
                    if namespace == ns.stem:
                        yield ns.stem
                else:
                    yield ns.stem

    def get_namespace_data(self, namespace=None):
        for ns in self.get_namespace_names(namespace):
            dep = CloudDeployers.get_deployer('generic')(
                self.emitter,
                namespace=ns,
                network=self.network,
                read_only=True
            )
            yield (ns, dep.get_all_hosts())
    
    def get_host_by_name(self, host_name):
        return next([host_data for node_name, host_data in self.get_all_hosts() if node_name == host_name])

    def get_all_hosts(self):
        return [(node_name, host_data) for node_name, host_data in self.config['instances'].items()]

    def destroy_resources(self, node_names):
        node_names = [s for s in node_names if s in [
            names for names, data in self.get_provider_hosts()]]
        if self.emitter.prompt( f"Destroying {self.provider_name} instances for nodes: {' '.join(node_names)}.  Continue?  (type 'yes')") == 'yes':
            
            if self._destroy_resources(node_names):
                if not self.config.get('instances'):
                    self.emitter.echo(
                        f"deleted all requested resources for {self.provider_name}.  We are clean.  No money is being spent.", color="green")

    def _destroy_resources(self, *args, **kwargs):
        raise NotImplementedError

    def update_captured_instance_data(self, results):
        instances_by_public_address = {
            d['publicaddress']: d for d in self.config['instances'].values()}
        for k, data in results.items():
            # results are keyed by 'publicaddress' in config data
            for instance_address, value in data:
                instances_by_public_address[instance_address][k] = value

        for k, v in self.config['instances'].items():
            if instances_by_public_address.get(v['publicaddress']):
                self.config['instances'][k] = instances_by_public_address.get(
                    v['publicaddress'])
        self._write_config()

    def give_helpful_hints(self, node_names, backup=False, playbook=None):

        self.emitter.echo("some relevant info:")
        self.emitter.echo(f' config file: "{self.config_path}"')
        self.emitter.echo(
            f" inventory file: {self.inventory_path}", color='yellow')
        if self.config.get('keypair_path'):
            self.emitter.echo(
                f" keypair file: {self.config['keypair_path']}", color='yellow')

        if nodes := [h for h in self.get_all_hosts() if h[0] in node_names]:
            self.emitter.echo("Host Info")
            for node_name, host_data in nodes:
                dep = CloudDeployers.get_deployer(host_data['provider'])(
                    self.emitter,
                    pre_config=self.config,
                    namespace=self.namespace,
                    network=self.network
                )
                self.emitter.echo(
                    f"\t{node_name}: {host_data['publicaddress']}")
                self.emitter.echo(
                    f"\t\t ssh: {dep.format_ssh_cmd(host_data)}", color="yellow")
                self.emitter.echo(
                    f"\t\t operator address: {host_data['operator address']}")

        if backup:
            self.emitter.echo(
                " *** Local backups containing sensitive data may have been created. ***", color="red")
            self.emitter.echo(
                f" Backup data can be found here: {self.config_dir}/remote_worker_backups/")

    def format_ssh_cmd(self, host_data):
        
        keypair = ''
        user = next(v['value'] for v in host_data['provider_deploy_attrs']
                    if v['key'] == 'default_user')

        if any([pda['key'] == 'ansible_ssh_private_key_file' for pda in host_data['provider_deploy_attrs']]):
            keypair ='-i "' + next(v['value'] for v in host_data['provider_deploy_attrs']
                                if v['key'] == 'ansible_ssh_private_key_file') + '"'

        return f"ssh {user}@{host_data['publicaddress']} {keypair}"

    def alert_new_mnemonic(self, wallet):
        self.emitter.echo(
            "A new keystore mnemonic has been generated:", color="yellow")
        self.emitter.echo(f'\t{wallet.mnemonic()}', color="red")
        self.emitter.echo(
            "This will be stored in the config file for this namespace.")
        self.emitter.echo(f'\t{self.config_path}')
        self.emitter.echo(
            "Back this up and keep it safe to enable restoration of Ursula nodes in the event of hard disk failure or other data loss.", color="red")

    def migrate_5_6(self):
        for index, instance in enumerate(self.config['instances'].keys()):
            if not self.config['instances'][instance].get('index'):
                self.config['instances'][instance]['index'] = index
            if instance.runtime_envvars.get('NUCYPHER_WORKER_ETH_PASSWORD'):
                instance.runtime_envvars['NUCYPHER_OPERATOR_ETH_PASSWORD'] = instance.runtime_envvars.get('NUCYPHER_WORKER_ETH_PASSWORD')
                del instance.runtime_envvars['NUCYPHER_WORKER_ETH_PASSWORD']

        if self.config.get('keyringpassword'):
            self.config['keystorepassword'] = self.config.get(
                'keyringpassword')

        if not self.config.get('keystoremnemonic'):
            wallet = keygen.generate()
            self.config['keystoremnemonic'] = wallet.mnemonic()
            self.alert_new_mnemonic(wallet)
        self._write_config()

    def migrate(self, current=5, target=6):
        migration = f'migrate_{current}_{target}'
        if hasattr(self, migration):
            return getattr(self, migration)()

        self.emitter.echo(
            f" *** Error:  Could'nt find migration from {current} to {target} ***", color="red")

    def remove_resources(self, hostnames):
        for host in hostnames:
            existing_instances = {k: v for k, v in self.config.get(
                'instances', {}).items() if k in hostnames}
            if existing_instances:
                for node_name, instance in existing_instances.items():
                    self.emitter.echo(
                        f"removing instance data for {node_name} in 3 seconds...", color='red')
                    time.sleep(3)
                    del self.config['instances'][node_name]
                    self._write_config()


class DigitalOceanConfigurator(BaseCloudNodeConfigurator):

    default_region = 'SFO3'
    provider_name = 'digitalocean'

    @property
    def instance_size(self):
        return self.kwargs.get('instance_type') or "s-1vcpu-2gb"

    @property
    def _provider_deploy_attrs(self):
        return [
            {'key': 'default_user', 'value': 'root'},
        ]

    def _configure_provider_params(self):
        self.token = os.environ.get('DIGITALOCEAN_ACCESS_TOKEN')
        if not self.token:
            self.emitter.echo(
                f"Please `export DIGITALOCEAN_ACCESS_TOKEN=<your access token.>` from here:  https://cloud.digitalocean.com/account/api/tokens\n", color="red")
            raise AttributeError(
                "Could not continue without DIGITALOCEAN_ACCESS_TOKEN environment variable.")
        self.region = os.environ.get('DIGITALOCEAN_REGION') or self.config.get(
            'digital-ocean-region') or self.kwargs.get('region') or self.default_region

        self.emitter.echo(
            f'using DigitalOcean region: {self.region}, to change regions `export DIGITALOCEAN_REGION: https://www.digitalocean.com/docs/platform/availability-matrix/\n', color='yellow')

        self.sshkey = os.environ.get(
            'DIGITAL_OCEAN_KEY_FINGERPRINT') or self.config.get('sshkey')
        if not self.sshkey:
            self.emitter.echo(
                "Please set the name of your Digital Ocean SSH Key (`export DIGITAL_OCEAN_KEY_FINGERPRINT=<your preferred ssh key fingerprint>` from here: https://cloud.digitalocean.com/account/security", color="red")
            self.emitter.echo(
                "it should look like `DIGITAL_OCEAN_KEY_FINGERPRINT=88:fb:53:51:09:aa:af:02:e2:99:95:2d:39:64:c1:64`\n", color="red")
            raise AttributeError(
                "Could not continue without DIGITAL_OCEAN_KEY_FINGERPRINT environment variable.")
        self.config['sshkey'] = self.sshkey
        self.config['digital-ocean-region'] = self.region

        self._write_config()

    def create_new_node(self, node_name):

        response = requests.post("https://api.digitalocean.com/v2/droplets",
                                 {
                                     "name": f'{node_name}',
                                     "region": self.region,
                                     "size": self.instance_size,
                                     "image": "ubuntu-20-04-x64",
                                     "ssh_keys": [self.sshkey]
                                 },
                                 headers={
                                     "Authorization": f'Bearer {self.token}'
                                 }
                                 )

        if response.status_code < 300:
            resp = response.json()

            new_node_id = resp['droplet']['id']
            node_data = {'InstanceId': new_node_id}

            self.emitter.echo("\twaiting for instance to come online...")

            instance_public_ip = None
            self.emitter.echo("checking for node's public IP")
            with self.emitter.progressbar(length=30, show_eta=False, show_percent=False) as bar:
                while not instance_public_ip:
                    bar.update(1)
                    time.sleep(1)

                    instance_resp = requests.get(
                        f'https://api.digitalocean.com/v2/droplets/{new_node_id}/',
                        headers={
                            "Authorization": f'Bearer {self.token}'
                        }
                    ).json().get('droplet')
                    if instance_resp['status'] == 'active':
                        if instance_resp.get('networks', {}).get('v4'):
                            instance_public_ip = next(
                                (n['ip_address'] for n in instance_resp['networks']['v4'] if n['type'] == 'public'), None)
                bar.update(30)
            node_data['publicaddress'] = instance_public_ip
            node_data['provider_deploy_attrs'] = self._provider_deploy_attrs
            node_data['installed'] = []
            return node_data

        else:
            self.emitter.echo(response.text, color='red')
            raise BaseException("Error creating resources in DigitalOcean")

    def _destroy_resources(self, node_names):

        existing_instances = {k: v for k, v in self.get_provider_hosts() if k in node_names}
        if existing_instances:
            self.emitter.echo(
                f"\nAbout to destroy the following: {', '.join(existing_instances.keys())}, including all local data about these nodes.")
            self.emitter.echo("\ntype 'y' to continue")
            if self.emitter.getchar(echo=False) == 'y':
                for node_name, instance in existing_instances.items():
                    if node_names and not node_name in node_names:
                        continue
                    self.emitter.echo(
                        f"deleting worker instance for {node_name} in 3 seconds...", color='red')
                    time.sleep(3)

                    result = requests.delete(
                        f'https://api.digitalocean.com/v2/droplets/{instance["InstanceId"]}/',
                        headers={
                            "Authorization": f'Bearer {self.token}'
                        })

                    if result.status_code == 204 or 'not_found' in result.text:
                        self.emitter.echo(
                            f"\tdestroyed instance for {node_name}")
                        del self.config['instances'][node_name]
                        self._write_config()
                    else:
                        raise Exception(
                            f"Errors occurred while deleting node: {result.text}")

        return True


class AWSNodeConfigurator(BaseCloudNodeConfigurator):

    URSULA_PORT = 9151
    PROMETHEUS_PORTS = [9101]
    PROMETHEUS_PORT = PROMETHEUS_PORTS[0]

    """
    gets a node up and running.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    provider_name = 'aws'

    # TODO: this probably needs to be region specific...
    EC2_AMI_LOOKUP = {
        'us-west-2': 'ami-09dd2e08d601bff67',  # Oregon
        'us-west-1': 'ami-021809d9177640a20',  # California
        'us-east-2': 'ami-07efac79022b86107',  # Ohio
        'us-east-1': 'ami-0dba2cb6798deb6d8',  # Virginia
        'eu-central-1': 'ami-0c960b947cbb2dd16',  # Frankfurt
        'ap-northeast-1': 'ami-09b86f9709b3c33d4',  # Tokyo
        'ap-southeast-1': 'ami-093da183b859d5a4b',  # Singapore
    }

    preferred_platform = 'ubuntu-focal'  # unused

    @property
    def _provider_deploy_attrs(self):
        return [
            {'key': 'ansible_ssh_private_key_file',
                'value': self.config['keypair_path']},
            {'key': 'default_user', 'value': 'ubuntu'}
        ]

    def _configure_provider_params(self):

        # some attributes we will configure later
        self.vpc = None
        # find aws profiles on user's local environment
        available_profiles = boto3.session.Session().available_profiles
        choice_list = '\n\t'.join(available_profiles)

        self.profile = self.config.get(
            'aws-profile') or os.getenv('AWS_PROFILE')
        if not self.profile:
            self.profile = self.emitter.prompt(
                f"please select an AWS profile from the following options: \n{choice_list}",
                type=self.emitter.Choice(available_profiles),
                show_choices=False
            )

        self.emitter.echo(f'using profile: {self.profile}')
        self.session = boto3.Session(profile_name=self.profile)

        ec2 = self.session.client('ec2')

        self.AWS_REGION = self.config.get(
            'aws-region') or os.environ.get('AWS_DEFAULT_REGION')
        if not self.AWS_REGION:
            available_regions = [r['RegionName']
                                 for r in ec2.describe_regions()['Regions']]
            region_choice_list = '\n\t'.join(available_regions)
            self.AWS_REGION = self.emitter.prompt(
                f"please select an AWS region from the following regions: {region_choice_list}\n",
                type=self.emitter.Choice(available_regions),
                show_choices=False
            )

        # re-init the session with a region specified
        self.session = boto3.Session(
            profile_name=self.profile, region_name=self.AWS_REGION)
        self.ec2Client = ec2 = self.session.client('ec2')

        self.EC2_INSTANCE_SIZE = self.kwargs.get('instance_type')

        if self.action == 'create':
            if self.EC2_INSTANCE_SIZE is None:
                instance_types = ec2.describe_instance_type_offerings(
                    # LocationType = 'region',
                    Filters=[
                        {'Values': ['t1.*', 't2.*', 't3.*',
                                    't3a.*'], 'Name': 'instance-type'},
                        # {'Values': [self.AWS_REGION], 'Name': 'location'}
                    ]
                )['InstanceTypeOfferings']

                instance_type_choices = sorted(
                    [r['InstanceType'] for r in instance_types])
                instance_type_choice_list = '\n\t'.join(instance_type_choices)
                self.EC2_INSTANCE_SIZE = self.emitter.prompt(
                    f"please select an instance type from the following choices:\n\t{instance_type_choice_list}\n",
                    type=self.emitter.Choice(instance_type_choices),
                    show_choices=False
                )

            self.emitter.echo(f"Instance type: {self.EC2_INSTANCE_SIZE}")

        self.emitter.echo(f"AWS Region: {self.AWS_REGION}")

        self.ec2Client = self.session.client('ec2')
        self.ec2Resource = self.session.resource('ec2')

        self.config['aws-profile'] = self.profile

        self.keypair = self.config.get('keypair')
        if not self.keypair:
            self.keypair, keypair_path = self._create_keypair()
            self.config['keypair_path'] = str(keypair_path)

        self.config['aws-profile'] = self.profile
        self.config['keypair'] = self.keypair
        self.config['aws-region'] = self.AWS_REGION
        self._write_config()

    @property
    def aws_tags(self):
        # to keep track of the junk we put in the cloud
        return [{"Key": "Name", "Value": self.namespace_network}]

    def _create_keypair(self):
        new_keypair_data = self.ec2Client.create_key_pair(
            KeyName=f'{self.namespace_network}')
        out_path = DEFAULT_CONFIG_ROOT / NODE_CONFIG_STORAGE_KEY / \
            f'{self.namespace_network}.awskeypair'
        out_path.parent.mkdir(parents=True, exist_ok=True)

        with open(out_path, 'w') as outfile:
            outfile.write(new_keypair_data['KeyMaterial'])
        # set local keypair permissions https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-key-pairs.html
        out_path.chmod(0o400)
        self.emitter.echo(
            f"a new aws keypair was saved to {out_path}, keep it safe.", color='yellow')
        return new_keypair_data['KeyName'], out_path

    def _delete_keypair(self):
        # only use self.namespace here to avoid accidental deletions of pre-existing keypairs
        deleted_keypair_data = self.ec2Client.delete_key_pair(
            KeyName=f'{self.namespace_network}')
        if deleted_keypair_data['HTTPStatusCode'] == 200:
            outpath = Path(DEFAULT_CONFIG_ROOT).joinpath(
                NODE_CONFIG_STORAGE_KEY, f'{self.namespace_network}.awskeypair')
            outpath.unlink()
            self.emitter.echo(
                f"keypair at {outpath}, was deleted", color='yellow')

    def _ensure_vpc(self):
        """creates an aws virtual private cloud if one doesn't exist"""

        try:
            from botocore import exceptions as botoexceptions
        except ImportError:
            self.emitter.echo(
                "You need to have boto3 installed to use this feature (pip3 install boto3)")
            return

        if not self.vpc:
            vpc_id = self.config.get('Vpc')
            if vpc_id:
                self.vpc = self.ec2Resource.Vpc(vpc_id)
            else:
                try:
                    vpcdata = self.ec2Client.create_vpc(
                        CidrBlock='172.16.0.0/16')
                except botoexceptions.NoCredentialsError:
                    raise ValueError(
                        f'Could create AWS resource with profile "{self.profile}" and keypair "{self.keypair}", please run this command with --aws-profile and --aws-keypair to specify matching aws credentials')
                self.vpc = self.ec2Resource.Vpc(vpcdata['Vpc']['VpcId'])
                self.vpc.wait_until_available()
                self.vpc.create_tags(Tags=self.aws_tags)
                self.vpc.modify_attribute(EnableDnsSupport={'Value': True})
                self.vpc.modify_attribute(EnableDnsHostnames={'Value': True})
                self.config['Vpc'] = vpc_id = self.vpc.id
                self._write_config()
        return self.vpc

    def _configure_path_to_internet(self):
        """
            create and configure all the little AWS bits we need to get an internet request
            from the internet to our node and back
        """

        if not self.config.get('InternetGateway'):
            gatewaydata = self.ec2Client.create_internet_gateway()
            self.config['InternetGateway'] = gateway_id = gatewaydata['InternetGateway']['InternetGatewayId']
            # tag it
            self._write_config()
            self.ec2Resource.InternetGateway(
                self.config['InternetGateway']).create_tags(Tags=self.aws_tags)

            self.vpc.attach_internet_gateway(
                InternetGatewayId=self.config['InternetGateway'])

        routetable_id = self.config.get('RouteTable')
        if not routetable_id:
            routetable = self.vpc.create_route_table()
            self.config['RouteTable'] = routetable_id = routetable.id
            self._write_config()
            routetable.create_tags(Tags=self.aws_tags)

        routetable = self.ec2Resource.RouteTable(routetable_id)
        routetable.create_route(
            DestinationCidrBlock='0.0.0.0/0', GatewayId=self.config['InternetGateway'])

        if not self.config.get('Subnet'):
            subnetdata = self.ec2Client.create_subnet(
                CidrBlock='172.16.1.0/24', VpcId=self.vpc.id)
            self.config['Subnet'] = subnet_id = subnetdata['Subnet']['SubnetId']
            self._write_config()
            self.ec2Resource.Subnet(subnet_id).create_tags(Tags=self.aws_tags)

        routetable.associate_with_subnet(SubnetId=self.config['Subnet'])

        if not self.config.get('SecurityGroup'):
            securitygroupdata = self.ec2Client.create_security_group(
                GroupName=f'Ursula-{self.namespace_network}', Description='ssh and Nucypher ports', VpcId=self.config['Vpc'])
            self.config['SecurityGroup'] = sg_id = securitygroupdata['GroupId']
            self._write_config()
            securitygroup = self.ec2Resource.SecurityGroup(sg_id)
            securitygroup.create_tags(Tags=self.aws_tags)

            securitygroup.authorize_ingress(
                CidrIp='0.0.0.0/0', IpProtocol='tcp', FromPort=22, ToPort=22)
            # TODO: is it always 9151?  Does that matter? Should this be configurable?
            securitygroup.authorize_ingress(
                CidrIp='0.0.0.0/0', IpProtocol='tcp', FromPort=self.URSULA_PORT, ToPort=self.URSULA_PORT)
            for port in self.PROMETHEUS_PORTS:
                securitygroup.authorize_ingress(
                    CidrIp='0.0.0.0/0', IpProtocol='tcp', FromPort=port, ToPort=port)

    def _do_setup_for_instance_creation(self):
        if not getattr(self, 'profile', None):
            self.emitter.echo(
                "Aws nodes can only be created with an aws profile. (https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-profiles.html)", color='red')
            raise AttributeError("AWS profile not configured.")

        self.emitter.echo(
            "ensuring that prerequisite cloud resources exist for instance creation.")
        self._ensure_vpc()
        self._configure_path_to_internet()
        self.emitter.echo("all prerequisite cloud resources do exist.")

    def _destroy_resources(self, node_names):
        try:
            from botocore import exceptions as botoexceptions
        except ImportError:
            self.emitter.echo(
                "You need to have boto3 installed to use this feature (pip3 install boto3)")
            return

        existing_instances = {k: v for k, v in self.config.get(
            'instances', {}).items() if k in node_names}
        vpc = self.ec2Resource.Vpc(self.config['Vpc'])
        if existing_instances:
            for node_name, instance in existing_instances.items():
                if node_names and not node_name in node_name:
                    continue
                self.emitter.echo(
                    f"deleting worker instance for {node_name} in 3 seconds...", color='red')
                time.sleep(3)
                self.ec2Resource.Instance(instance['InstanceId']).terminate()
                del self.config['instances'][node_name]
                self.emitter.echo(f"\tdestroyed instance for {node_name}")
                self._write_config()

        if not len(self.get_provider_hosts()):
            self.emitter.echo("waiting for instance termination...")
            time.sleep(10)
            for subresource in ['Subnet', 'RouteTable', 'SecurityGroup']:
                tries = 0
                while self.config.get(subresource) and tries < 10:
                    self.emitter.echo(f'deleting {subresource}')
                    try:
                        getattr(self.ec2Resource, subresource)(
                            self.config[subresource]).delete()
                        self.emitter.echo(
                            f'deleted {subresource}: {self.config[subresource]}')
                        del self.config[subresource]
                        self._write_config()
                    except botoexceptions.ClientError as e:
                        tries += 1
                        self.emitter.echo(
                            f'failed to delete {subresource}, because: {e}.. trying again in 10...', color="yellow")
                        time.sleep(10)
                if tries > 10:
                    self.emitter.echo(
                        "some resources could not be deleted because AWS is taking awhile to delete things.  Run this command again in a minute or so...", color="yellow")
                    return False

            if self.config.get('InternetGateway'):
                self.ec2Resource.InternetGateway(
                    self.config['InternetGateway']).detach_from_vpc(VpcId=self.config['Vpc'])
                self.ec2Resource.InternetGateway(
                    self.config['InternetGateway']).delete()
                self.emitter.echo(
                    f'deleted InternetGateway: {self.config["InternetGateway"]}')
                del self.config['InternetGateway']
                self._write_config()

            if self.config.get('Vpc'):
                vpc.delete()
                self.emitter.echo(f'deleted Vpc: {self.config["Vpc"]}')
                del self.config['Vpc']
                self._write_config()

            if self.config.get('keypair'):
                self.emitter.echo(
                    f'deleting keypair {self.keypair} in 5 seconds...', color='red')
                time.sleep(6)
                self.ec2Client.delete_key_pair(
                    KeyName=self.config.get('keypair'))
                del self.config['keypair']
                Path(self.config['keypair_path']).unlink()
                del self.config['keypair_path']
                self._write_config()

        return True

    def create_new_node(self, node_name):

        params = dict(
            ImageId=self.EC2_AMI_LOOKUP.get(self.AWS_REGION),
            InstanceType=self.EC2_INSTANCE_SIZE,
            KeyName=self.keypair,
            NetworkInterfaces=[
                {
                    'AssociatePublicIpAddress': True,
                    'DeleteOnTermination': True,
                    'DeviceIndex': 0,
                    'Groups': [
                        self.config['SecurityGroup']
                    ],
                    'SubnetId': self.config['Subnet'],
                },
            ],
            TagSpecifications=[
                {
                    'ResourceType': 'instance',
                    'Tags': [
                        {
                            'Key': 'Name',
                            'Value': f'{node_name}'
                        },
                    ]
                },
            ],
        )
        new_instance_data = self.ec2Client.run_instances(
            MaxCount=1,
            MinCount=1,
            **params
        )

        node_data = {
            'InstanceId': new_instance_data['Instances'][0]['InstanceId']}

        instance = self.ec2Resource.Instance(
            new_instance_data['Instances'][0]['InstanceId'])
        self.emitter.echo("\twaiting for instance to come online...")
        instance.wait_until_running()
        instance.load()
        node_data['publicaddress'] = instance.public_dns_name
        node_data['provider_deploy_attrs'] = self._provider_deploy_attrs

        return node_data


class GenericConfigurator(BaseCloudNodeConfigurator):

    provider_name = 'generic'

    def _write_config(self):
        if not self.config_path.exists() and self.action not in self.NAMESSPACE_CREATE_ACTIONS:
            raise AttributeError(
                f"Namespace/config '{self.namespace}' does not exist. Show existing namespaces: `nucypher nodes list-namespaces` or create a namespace: `nucypher nodes create`")
        super()._write_config()

    def create_nodes(self, node_names, host_address, login_name, key_path, ssh_port):
        if not self.config.get('instances'):
            self.config['instances'] = {}

        for node_name in node_names:
            node_data = self.config['instances'].get(node_name, {})
            if node_data:
                self.emitter.echo(
                    f"Host info already exists for staker {node_name}; Updating and proceeding.", color="yellow")
                time.sleep(3)

            node_data['publicaddress'] = host_address
            node_data['provider'] = self.provider_name
            node_data['index'] = len(self.config['instances'].keys())
            node_data['provider_deploy_attrs'] = [
                {'key': 'ansible_ssh_private_key_file', 'value': key_path},
                {'key': 'default_user', 'value': login_name},
                {'key': 'ansible_port', 'value': ssh_port}
            ]

            self.config['instances'][node_name] = node_data
            if self.config['seed_network'] and not self.config.get('seed_node'):
                self.config['seed_node'] = node_data['publicaddress']
            self._write_config()
            self.created_new_nodes = True

        return self.config

    def deploy_image_on_existing_nodes(self, hosts, resource):
        self.emitter.echo("this feature is a work in progress")
        pass


class CloudDeployers:

    aws = AWSNodeConfigurator
    digitalocean = DigitalOceanConfigurator
    generic = GenericConfigurator

    @staticmethod
    def get_deployer(name):
        return getattr(CloudDeployers, name)
