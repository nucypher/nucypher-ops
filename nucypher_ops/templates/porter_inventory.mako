all:
  children:
    nucypher:
      children:
        ${deployer.network}:
          children:
            nodes:
              vars:
                network_name: ${deployer.network}
                ansible_python_interpreter: /usr/bin/python3
                ansible_connection: ssh
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
                  %if node.get('docker_image'):
                  docker_image: ${node['docker_image']}
                  %endif
                  runtime_envvars:
                  %for key, val in node['runtime_envvars'].items():
                    ${key}: "${val}"
                  %endfor
                  CLI_RUNTIME_OPTIONS: ${deployer._format_runtime_options(node['runtime_cliargs'])}
                %endfor