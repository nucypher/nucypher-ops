all:
  children:
    keep:
      children:
        ${deployer.network}:
          children:
            nodes:
              vars:
                node_user: ${deployer.user}
                network_name: ${deployer.network}
                ansible_python_interpreter: /usr/bin/python3
                geth_dir: '/home/${deployer.user}/geth/.ethereum/${deployer.chain_name}/'
                geth_container_geth_datadir: "/root/.ethereum/${deployer.chain_name}"
                deployer_config_path: ${deployer.config_dir}
                ansible_connection: ssh
              hosts:
                %for node in nodes:
                ${node['publicaddress']}:
                  host_nickname: "${node['host_nickname']}"
                  %for attr in node['provider_deploy_attrs']:
                  ${attr['key']}: ${attr['value']}
                  %endfor
                  % if node.get('eth_endpoint'):
                  eth_provider: ${node['eth_endpoint']}
                  %endif
                  %if node.get('docker_image'):
                  docker_image: ${node['docker_image']}
                  %endif
                  runtime_envvars:
                  %for key, val in node['runtime_envvars'].items():
                    ${key}: "${val}"
                  %endfor
                  CLI_RUNTIME_OPTIONS: ${deployer._format_runtime_options(node['runtime_cliargs'])}
                %endfor