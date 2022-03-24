all:
  children:
    nucypher:
      children:
        mainnet:
          children:
            nodes:
              vars:
                geth_dir: '/home/nucypher/geth/.ethereum/mainnet/'
                geth_container_geth_datadir: "/root/.ethereum/mainnet"
                nucypher_container_geth_datadir: "/root/.local/share/geth/.ethereum/mainnet"
                ansible_python_interpreter: /usr/bin/python3
                ansible_connection: ssh
                ansible_ssh_private_key_file: ~/.ssh/nc-full-nodes.pem
              hosts:
                hosts:
                %for node in nodes:
                ${node['publicaddress']}:
                    default_user: ubuntu
                    %for attr in node['provider_deploy_attrs']:
                    ${attr['key']}: ${attr['value']}
                    %endfor
                    %for key, val in node['runtime_envvars'].items():
                    ${key}: "${val}"
                    %endfor
                %endfor
