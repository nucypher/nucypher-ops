# hello.py
import click

from nucypher_ops.cli.nodes import cli as nodes
from nucypher_ops.cli.ursula import cli as ursula
from nucypher_ops.cli.ethereum import cli as ethereum
from nucypher_ops.cli.namespaces import cli as namespaces
from nucypher_ops.cli.porter import cli as porter


@click.group()
def index():
    pass


index.add_command(nodes)
index.add_command(ursula)
# index.add_command(ethereum)
index.add_command(namespaces)
# index.add_command(porter)
