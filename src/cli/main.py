# hello.py
import click 

from src.cli.nodes import cli as nodes
from src.cli.ursula import cli as ursula
from src.cli.ethereum import cli as ethereum

@click.group()
def index():
    pass

index.add_command(nodes)
index.add_command(ursula)
index.add_command(ethereum)