from importlib.metadata import version

import click

from nucypher_ops.cli.ethereum import cli as ethereum
from nucypher_ops.cli.namespaces import cli as namespaces
from nucypher_ops.cli.nodes import cli as nodes
from nucypher_ops.cli.porter import cli as porter
from nucypher_ops.cli.tbtcv2 import cli as tbtcv2
from nucypher_ops.cli.ursula import cli as ursula

package_version = version('nucypher_ops')


@click.group()
@click.version_option(version=package_version)
def index():
    pass


index.add_command(nodes)
index.add_command(ursula)
index.add_command(ethereum)
index.add_command(namespaces)
index.add_command(porter)
index.add_command(tbtcv2)

if __name__ == "__main__":
    index()
