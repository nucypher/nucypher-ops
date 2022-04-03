all:
  children:
    nucypher:
      children:
        ${deployer.network}:
          children:
            nodes:
              vars:
                network_name: "${deployer.network}"
                geth_options: "--${deployer.chain_name}"
                geth_dir: '/home/nucypher/geth/.ethereum/${deployer.chain_name}/'
                geth_container_geth_datadir: "/root/.ethereum/${deployer.chain_name}"
                nucypher_container_geth_datadir: "/root/.local/share/geth/.ethereum/${deployer.chain_name}"
                etherscan_domain: ${deployer.chain_name}.etherscan.io
                ansible_python_interpreter: /usr/bin/python3
                ansible_connection: ssh
                %if deployer.config.get('seed_node'):
                SEED_NODE_URI: ${deployer.config['seed_node']}
                teacher_options: ""
                %else:
                SEED_NODE_URI:
                teacher_options: ""
                %endif
                wipe_nucypher_config: ${extra.get('migrate_nucypher', False) or extra.get('init', False)}
                wipe_eth_wallet: ${extra.get('init', False)}
                deployer_config_path: ${deployer.config_dir}
                restore_path: ${extra.get('restore_path')}
                payment_network: ${deployer.config.get('payment_network', 'polygon')}
              hosts:
                %for node in nodes:
                ${node['publicaddress']}:
                  host_nickname: "${node['host_nickname']}"
                  %for attr in node['provider_deploy_attrs']:
                  ${attr['key']}: ${attr['value']}
                  %endfor
                  % if node.get('eth_provider'):
                  eth_provider: ${node['eth_provider']}
                  %endif
                  % if node.get('payment_provider'):
                  payment_provider: ${node['payment_provider']}
                  %endif
                  % if node.get('payment_network'):
                  payment_network: ${node['payment_network']}
                  %endif
                  %if node.get('docker_image'):
                  docker_image: ${node['docker_image']}
                  %endif
                  %if node.get('keymaterial'):
                  keymaterial: ${node['keymaterial']}
                  %endif
                  runtime_envvars:
                  %for key, val in node['runtime_envvars'].items():
                    ${key}: "${val}"
                  %endfor
                  nucypher_ursula_run_options: ${deployer._format_runtime_options(node['runtime_cliargs'])}
                %endfor
