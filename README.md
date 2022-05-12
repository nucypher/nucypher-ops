# nucypher-ops

This repo aims to streamline the process of managing and running Threshold PRE applications on remote cloud infrastructure.
It has the functionality to spin up new nodes, deploy, and run the Threshold codebase, all with minimal configuration.
## Installation
```
$ pip3 install nucypher-ops
$ nucypher-ops --help
```


## Basic Usage 
```
$ nucypher-ops nodes create # you will end up with a node running on either AWS or DigitalOcean ready for install
$ nucypher-ops ursula deploy # you will have an Ursula fully installed and ready for bonding.
```

For a more detailed guide on how to get started, follow this [tutorial](https://docs.nucypher.com/en/latest/pre_application/cloud_node_management.html) or this [community maintained guide](https://promethium.dev/t/nucypher-ops/)
